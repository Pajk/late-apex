"""Walks the whole front end: title, circuit select, a race, results,
3-character name entry and the high score table."""

from tests import harness


def run():
    c = harness.Checks('ui flow')
    import pygame
    from game.app import (App, S_TITLE, S_SELECT, S_CAR, S_RACE, S_PAUSE,
                          S_RESULT, S_NAME, S_SCORES, S_HELP)
    from game.race import Race, MAX_SPEED

    app = App(harness.ROOT)
    frames = []

    def press(key):
        app.on_key(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0,
                                      unicode=''))

    def step(n=1):
        for _ in range(n):
            app.update(1 / 60.0)
            app.draw()

    def grab():
        frames.append(app.screen.copy())

    step(30)
    c.check(app.state == S_TITLE, 'did not start on the title screen')
    c.check(app.demo is not None, 'attract-mode demo is not running')
    grab()

    press(pygame.K_RETURN)
    step(40)
    c.check(app.state == S_SELECT, 'enter on title did not open circuit select')
    grab()

    before = app.sel
    press(pygame.K_DOWN)
    step(5)
    c.check(app.sel != before, 'circuit selection did not move')
    grab()

    press(pygame.K_i)
    step(40)
    c.check(app.state == S_HELP, 'I did not open the controls screen')
    grab()
    press(pygame.K_RETURN)
    step(40)

    press(pygame.K_h)
    step(40)
    c.check(app.state == S_SCORES, 'H did not open the high score table')
    grab()
    press(pygame.K_ESCAPE)
    step(40)

    press(pygame.K_RETURN)
    step(40)
    c.check(app.state == S_CAR, 'enter did not open the garage')
    grab()
    from game import cars as garage
    before_car = app.car_sel
    press(pygame.K_RIGHT)
    step(5)
    c.check(app.car_sel != before_car, 'car selection did not move')
    press(pygame.K_LEFT)
    step(5)

    press(pygame.K_RETURN)
    step(40)
    c.check(app.state == S_RACE, 'enter did not start a race')
    c.check(app.race.car is garage.CARS[app.car_sel],
            'the race did not use the chosen car')
    c.check(app.race is not None and app.demo is None,
            'demo was not torn down when the race began')
    c.check(app.race.state == Race.STATE_COUNTDOWN,
            'race did not begin with a countdown')
    grab()

    # wait out the countdown rather than assuming its length
    waited = 0
    while app.race.state == Race.STATE_COUNTDOWN and waited < 600:
        step(1)
        waited += 1
    c.check(app.race.state == Race.STATE_RACING,
            'countdown did not hand over to racing (waited %d frames)'
            % waited)
    c.note('countdown lasted %.1fs' % (waited / 60.0))
    app.race.player.speed = MAX_SPEED * 0.8
    step(300)
    c.check(app.race.player.z > 0, 'the car did not move')
    grab()

    press(pygame.K_p)
    step(3)
    c.check(app.state == S_PAUSE, 'P did not pause')
    grab()
    frozen = app.race.player.z
    step(30)
    c.check(app.race.player.z == frozen, 'the race kept running while paused')
    press(pygame.K_p)
    step(3)
    c.check(app.state == S_RACE, 'P did not resume')

    # jump to the last lap and cross the line
    race = app.race
    race.player.lap = race.track.laps - 1
    race.race_time, race.lap_time = 95.4, 31.2
    race.lap_times = [33.1, 31.0]
    race.best_lap = 31.0
    race.player.z = race.track.length - 500
    race.player.speed = MAX_SPEED * 0.7
    step(120)
    c.check(race.state == Race.STATE_FINISHED, 'crossing the line did not finish')

    step(240)
    c.check(app.state == S_RESULT, 'results screen did not appear')
    c.check(app.result is not None and app.result['qualifies'],
            'a record lap did not qualify for the table')
    grab()

    press(pygame.K_RETURN)
    step(10)
    c.check(app.state == S_NAME, 'qualifying did not open name entry')
    grab()

    # type initials directly
    for key in (pygame.K_p, pygame.K_a, pygame.K_v):
        press(key)
    step(60)
    c.check(app.state == S_SCORES, 'confirming initials did not show the table')
    grab()

    table = app.scores.table(app.result['key'], 'race')
    mine = [r for r in table if r['name'] == 'PAV']
    c.check(mine and mine[0].get('car') == app.result['car'],
            'the score did not record which car set it')
    c.check(any(row['name'] == 'PAV' for row in table),
            'the new score is missing from the table (%s)'
            % [r['name'] for r in table[:3]])
    c.check(table == sorted(table, key=lambda r: r['time']),
            'the high score table is not sorted by time')

    reloaded = type(app.scores)(__import__('game.track', fromlist=['x'])
                                .TRACK_SPECS)
    c.check(any(r['name'] == 'PAV'
                for r in reloaded.table(app.result['key'], 'race')),
            'the score did not survive a reload from disk')

    out = harness.contact_sheet(frames, 'screens.png', cols=3)
    c.note('walked %d screens, wrote %s' % (len(frames), out))
    return c.report()
