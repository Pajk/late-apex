"""Drives every circuit with an autopilot at three skill levels and checks the
countdown timers still make each race winnable but not a formality."""

import random

from tests import harness

SKILLS = ((0.55, 'novice'), (0.85, 'good'), (1.0, 'expert'))


def run():
    c = harness.Checks('balance')
    from game.render import Assets, Renderer
    from game.race import Race
    from game import track as T
    from game.scores import Scores
    from game import autopilot

    renderer = Renderer(Assets(harness.ROOT))
    scores = Scores(T.TRACK_SPECS)
    results = {}

    for spec in T.TRACK_SPECS:
        for skill, label in SKILLS:
            track = T.load(spec['key'])
            race = Race(track, renderer, harness.silent_audio(), scores,
                        random.Random(9))
            elapsed = 0.0
            while race.state in (Race.STATE_COUNTDOWN,
                                 Race.STATE_RACING) and elapsed < 400:
                race.update(1 / 60.0, autopilot.drive(race, skill))
                elapsed += 1 / 60.0
            results[(spec['key'], label)] = (race.state, race.finished_at,
                                             race.best_lap)
            race.clear()

        budget = spec['start_time'] + spec['lap_bonus'] * 2
        state, finished, best = results[(spec['key'], 'good')]
        ok = c.check(state == Race.STATE_FINISHED,
                     '%s is not finishable by a competent lap (budget %ds)'
                     % (spec['name'], budget))
        if ok:
            c.near(finished / budget, 0.75, 0.99,
                   '%s clock is mistuned - a good run uses %.0f%% of the '
                   'budget' % (spec['name'], 100 * finished / budget))
            c.check(best is not None and 15 < best < 120,
                    '%s best lap is implausible (%s)' % (spec['name'], best))

        _, novice_t, _ = results[(spec['key'], 'novice')]
        _, expert_t, _ = results[(spec['key'], 'expert')]
        if novice_t and expert_t:
            c.check(expert_t <= novice_t + 0.5,
                    '%s rewards the worse driver (expert %.1fs vs novice '
                    '%.1fs)' % (spec['name'], expert_t, novice_t))

        def show(label):
            state, finished, best = results[(spec['key'], label)]
            if state == Race.STATE_FINISHED:
                return '%s %s' % (label, _fmt(finished))
            return '%s TIMEUP' % label
        c.note('%-14s budget %3ds | %s' % (
            spec['name'], budget, '  '.join(show(l) for _, l in SKILLS)))

    # every car has to be able to finish every circuit at every difficulty,
    # or the slow ones are a trap rather than a choice
    from game import cars as garage
    from game import difficulty as levels
    slowest = {}
    for level in levels.LEVELS:
      for car in garage.CARS:
        for spec in T.TRACK_SPECS:
            track = T.load(spec['key'])
            race = Race(track, renderer, harness.silent_audio(), scores,
                        random.Random(9), car=car, level=level)
            elapsed = 0.0
            while race.state in (Race.STATE_COUNTDOWN,
                                 Race.STATE_RACING) and elapsed < 400:
                race.update(1 / 60.0, autopilot.drive(race, 0.95))
                elapsed += 1 / 60.0
            budget = (spec['start_time'] + spec['lap_bonus'] * 2) \
                * level['time']
            ok = c.check(race.state == Race.STATE_FINISHED,
                         '%s cannot finish %s on %s within %ds'
                         % (car['name'], spec['name'], level['name'], budget))
            if ok:
                margin = budget - race.finished_at
                c.check(margin >= 3.0,
                        '%s has only %.1fs to spare on %s (%s) - that '
                        'combination is a trap, not a choice'
                        % (car['name'], margin, spec['name'], level['name']))
                key = (level['name'], car['name'])
                if key not in slowest or margin < slowest[key][1]:
                    slowest[key] = (spec['name'], margin)
            race.clear()
    for level in levels.LEVELS:
        row = '  '.join('%s%+5.1f' % (car['name'][:6],
                                      slowest[(level['name'], car['name'])][1])
                        for car in garage.CARS
                        if (level['name'], car['name']) in slowest)
        c.note('%-7s tightest: %s' % (level['name'], row))

    # the whole point of the clock: a sloppy run must be able to fail
    timeouts = sum(1 for (_, label), (state, _, _) in results.items()
                   if label == 'novice' and state == Race.STATE_TIMEUP)
    c.check(timeouts >= 1,
            'no circuit punishes a sloppy run - the countdown is toothless')
    return c.report()


def _fmt(t):
    if t is None:
        return '--:--'
    return '%d:%05.2f' % (int(t // 60), t - int(t // 60) * 60)