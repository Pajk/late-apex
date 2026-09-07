"""Race rules: the things a player would call a bug if they broke.

The countdown checks are here because an early build let the throttle build
road speed on the line - the speedometer climbed to 77 km/h while the car sat
still, then launched from that speed the moment the lights went out.
"""

import random

from tests import harness


def _race(key='country', seed=1, car=None):
    from game.render import Assets, Renderer
    from game.race import Race
    from game import track as T
    from game.scores import Scores
    renderer = Renderer(Assets(harness.ROOT))
    return Race(T.load(key), renderer, harness.silent_audio(),
                Scores(T.TRACK_SPECS), random.Random(seed), car=car)


HOLD = {'left': False, 'right': False, 'accel': True, 'brake': False}
COAST = {'left': False, 'right': False, 'accel': False, 'brake': False}


def run():
    c = harness.Checks('race rules')
    from game.race import Race, MAX_SPEED, TURBO_TIME

    # -- you cannot jump the start -------------------------------------
    race = _race()
    c.check(race.state == Race.STATE_COUNTDOWN, 'race did not start on the grid')
    peak_speed = 0.0
    frames = 0
    while race.state == Race.STATE_COUNTDOWN and frames < 600:
        race.update(1 / 60.0, HOLD)          # throttle pinned the whole time
        peak_speed = max(peak_speed, race.player.speed)
        frames += 1
    c.check(peak_speed == 0.0,
            'throttle builds speed during the countdown (reached %.1f km/h)'
            % (peak_speed * 310.0 / MAX_SPEED))
    c.check(race.player.z == 0.0,
            'the car moved before the lights went out (z=%.1f)'
            % race.player.z)
    c.check(race.player.speed == 0.0,
            'the race began with a rolling start (%.1f km/h on the line)'
            % race.kmh)
    c.note('countdown held the car for %.1fs, revs reached %.2f'
           % (frames / 60.0, race.revs))

    # revving on the line is still fed back to the player
    c.check(race.revs > 0.5,
            'blipping the throttle on the line does not rev the engine')
    gear, rpm = race.gear_rpm()
    c.check(gear == 1, 'the rev counter shows gear %d on the line' % gear)

    # -- and it does pull away once racing -----------------------------
    for _ in range(60):
        race.update(1 / 60.0, HOLD)
    c.check(race.player.speed > 0 and race.player.z > 0,
            'the car does not pull away after the countdown')
    race.clear()

    # -- lap completion tops up the clock ------------------------------
    race = _race()
    race.state = Race.STATE_RACING
    race.player.speed = MAX_SPEED * 0.8
    race.player.z = race.track.length - 400
    before = race.time_left
    laps_before = race.player.lap
    for _ in range(30):
        race.update(1 / 60.0, HOLD)
    c.check(race.player.lap == laps_before + 1, 'crossing the line did not count a lap')
    c.near(race.time_left - before, race.track.lap_bonus - 2.0,
           race.track.lap_bonus + 0.5,
           'lap bonus was not added to the clock')
    c.check(race.lap_times and race.best_lap is not None,
            'no lap time was recorded')
    race.clear()

    # -- the race ends after the right number of laps ------------------
    race = _race()
    race.state = Race.STATE_RACING
    race.player.lap = race.track.laps - 1
    race.player.speed = MAX_SPEED * 0.8
    race.player.z = race.track.length - 400
    for _ in range(30):
        race.update(1 / 60.0, HOLD)
    c.check(race.state == Race.STATE_FINISHED,
            'the final lap did not finish the race')
    c.check(race.finished_at is not None, 'no finishing time was recorded')
    race.clear()

    # -- running out of time stops the race ----------------------------
    race = _race()
    race.state = Race.STATE_RACING
    race.time_left = 0.2
    for _ in range(60):
        race.update(1 / 60.0, HOLD)
    c.check(race.state == Race.STATE_TIMEUP, 'the clock reaching zero did not end the race')
    race.clear()

    # -- turbo: three per race, and no stacking ------------------------
    race = _race()
    race.state = Race.STATE_RACING
    race.player.speed = MAX_SPEED * 0.6
    c.check(race.player.turbo == 3, 'a race does not start with three turbos')

    race.use_turbo()
    c.check(race.player.turbo == 2 and race.player.turbo_left > 0,
            'the first turbo did not engage')
    race.use_turbo()
    c.check(race.player.turbo == 2,
            'turbo can be stacked - a second press during a boost spent one')

    # four attempts, each after the previous boost has run out
    uses = 1
    for _ in range(3):
        for _ in range(int(TURBO_TIME * 60) + 12):
            race.update(1 / 60.0, HOLD)
        before = race.player.turbo
        race.use_turbo()
        if race.player.turbo == before - 1:
            uses += 1
    c.check(uses == 3, 'expected exactly three turbos per race, got %d' % uses)
    c.check(race.player.turbo == 0,
            'turbo count ended at %d instead of 0' % race.player.turbo)
    c.note('turbo: %d uses granted, stacking refused' % uses)
    race.clear()

    # -- going off road actually costs you -----------------------------
    from game.race import OFF_ROAD_LIMIT
    race = _race()
    race.state = Race.STATE_RACING
    race.player.speed = MAX_SPEED
    race.player.x = 1.6                       # well onto the verge
    on_road_kmh = race.kmh
    # long enough for the off-road penalty to reach its equilibrium: the
    # penalty only applies above the limit, so speed settles just above it
    for _ in range(300):
        race.update(1 / 60.0, HOLD)
    c.check(race.player.offroad, 'the car is not registered as off road')
    c.check(race.player.speed <= OFF_ROAD_LIMIT * 1.15,
            'the verge does not slow the car (%.0f km/h off road, limit is '
            '%.0f)' % (race.kmh, OFF_ROAD_LIMIT * 310.0 / MAX_SPEED))
    c.note('off road: %.0f km/h -> %.0f km/h with the throttle pinned'
           % (on_road_kmh, race.kmh))
    race.clear()

    # -- the garage actually changes the car ---------------------------
    from game import cars as garage
    tops = {}
    for car in garage.CARS:
        r = _race(car=car)
        tops[car['key']] = r.top_speed
        c.check(abs(r.top_speed - MAX_SPEED * car['speed']) < 1e-6,
                '%s does not get its own top speed' % car['name'])
        c.check(r.car_body == car['body'],
                '%s does not get its own body width' % car['name'])
        r.clear()
    c.check(tops['gt'] > tops['wedge'] > tops['van'],
            'the cars do not differ in top speed as specified')

    # -- sirens: the ambulance makes rivals pull over -------------------
    def yielding(car_key):
        race = _race(car=garage.get(car_key))
        race.state = Race.STATE_RACING
        rival = race.cars[0]
        # park a rival just ahead, directly in the player's path
        race.player.z = rival.z - 600
        race.player.x = rival.offset = 0.0
        race.player.speed = MAX_SPEED * 0.7
        rival.speed = MAX_SPEED * 0.4
        start = rival.offset
        for _ in range(45):
            race.update(1 / 60.0, COAST)
        moved = abs(rival.offset - start)
        race.clear()
        return moved

    siren = yielding('ambulance')
    plain = yielding('wedge')
    c.check(siren > plain,
            'the ambulance siren does not clear traffic (moved %.3f vs %.3f '
            'for the plain car)' % (siren, plain))
    c.note('siren pushed the rival aside %.2f vs %.2f without it'
           % (siren, plain))

    return c.report()
