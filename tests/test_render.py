"""Renders every circuit and checks the frames are sane and fast enough."""

import random
import time

from tests import harness


def run():
    c = harness.Checks('render')
    import pygame
    from game.render import Assets, Renderer, WIDTH, HEIGHT
    from game.race import Race, MAX_SPEED
    from game import track as T
    from game.scores import Scores

    assets = Assets(harness.ROOT)
    renderer = Renderer(assets)
    scores = Scores(T.TRACK_SPECS)
    surface = pygame.Surface((WIDTH, HEIGHT)).convert()
    keys = {'left': False, 'right': False, 'accel': True, 'brake': False}
    frames = []

    for spec in T.TRACK_SPECS:
        track = T.load(spec['key'])
        race = Race(track, renderer, harness.silent_audio(), scores,
                    random.Random(3))
        race.state = Race.STATE_RACING
        race.player.speed = MAX_SPEED * 0.75
        race.time_left = 999
        for _ in range(240):
            race.update(1 / 60.0, keys)

        start = time.perf_counter()
        for _ in range(60):
            race.update(1 / 60.0, keys)
            race.draw(surface)
        fps = 60.0 / (time.perf_counter() - start)

        # a frame that is all one colour means the road did not draw
        colours = {surface.get_at((x, y))[:3]
                   for x in range(20, WIDTH, 37)
                   for y in range(40, HEIGHT - 40, 23)}
        c.check(len(colours) > 8,
                '%s renders an almost blank frame (%d distinct colours)'
                % (spec['name'], len(colours)))
        c.check(fps > 120,
                '%s renders too slowly for 60fps headroom (%.0f fps)'
                % (spec['name'], fps))
        c.note('%-14s %6.0f fps headless, %3d colours'
               % (spec['name'], fps, len(colours)))
        frames.append(surface.copy())
        race.clear()

    out = harness.contact_sheet(frames, 'tracks.png')
    c.note('wrote %s' % out)
    return c.report()
