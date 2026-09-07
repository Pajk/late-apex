"""Sprite placement and track geometry invariants.

This is the test that would have caught the start gantry sitting with one leg
in the middle of the road: roadside sprites anchor at their inner edge, but a
sprite at offset exactly 0 must be centred instead.
"""

from tests import harness


def run():
    c = harness.Checks('geometry')
    from game.render import Assets, OBJECT_SCALE, sprite_anchor
    from game.track import ROAD_WIDTH, SEGMENT_LENGTH
    from game import track as T

    assets = Assets(harness.ROOT)

    def span(name, scale, offset):
        """Left/right edge in road half-widths (the road spans -1.0..+1.0).

        Deliberately calls the game's own sprite_anchor rather than repeating
        the arithmetic, so a regression in the real code fails this test.
        """
        w = assets.get(name).get_width() * scale * OBJECT_SCALE / ROAD_WIDTH
        centre = sprite_anchor(offset, w)
        return centre - w / 2, centre + w / 2, w

    # -- centred sprites stay centred ----------------------------------
    left, right, width = span('obj_gantry', 2.2, 0.0)
    c.check(abs(left + right) < 1e-9,
            'start gantry is not centred on the road (spans %.2f..%.2f)'
            % (left, right))
    c.check(left < -1.0 and right > 1.0,
            'start gantry legs are not clear of the road '
            '(spans %.2f..%.2f, road edges are -1.0/+1.0)' % (left, right))
    c.note('gantry %.2f half-widths wide, legs at %+.2f / %+.2f'
           % (width, left, right))

    # -- roadside sprites anchor at their inner edge -------------------
    for name, scale, offset in (('obj_tree_oak', 2.4, 1.5),
                                ('obj_tree_oak', 2.4, -1.5),
                                ('obj_streetlamp', 1.3, 1.16),
                                ('obj_streetlamp', 1.3, -1.16)):
        left, right, _ = span(name, scale, offset)
        inner = left if offset > 0 else right
        c.check(abs(inner - offset) < 1e-9,
                '%s at offset %+.2f should touch %+.2f, got %+.2f'
                % (name, offset, offset, inner))

    # -- nothing collidable is placed on the racing line ---------------
    for spec in T.TRACK_SPECS:
        track = T.load(spec['key'])
        intruders = []
        for seg in track.segments:
            for offset, name, scale, collides in seg.sprites:
                if not collides:
                    continue
                left, right, _ = span(name, scale, offset)
                if left < 1.0 and right > -1.0:
                    intruders.append((seg.index, name, offset))
        c.check(not intruders,
                '%s has %d collidable objects overlapping the road, e.g. %s'
                % (spec['name'], len(intruders), intruders[:3]))

    # -- the lap must actually join up ---------------------------------
    for spec in T.TRACK_SPECS:
        track = T.load(spec['key'])
        first, last = track.segments[0], track.segments[-1]
        c.check(abs(first.p1.wy) < 1e-6 and abs(last.p2.wy) < 1e-6,
                '%s does not return to y=0 at the finish line '
                '(start %.2f, end %.2f)'
                % (spec['name'], first.p1.wy, last.p2.wy))
        c.check(abs(last.curve) < 0.01,
                '%s still curves at the finish line (%.3f)'
                % (spec['name'], last.curve))
        c.check(track.length == len(track.segments) * SEGMENT_LENGTH,
                '%s length does not match its segment count' % spec['name'])

    # -- rivals must look the size they collide at ---------------------
    from game.race import PLAYER_W, RIVAL_W
    import random as _rnd
    from game.render import Renderer as _R
    from game.scores import Scores as _S
    from game.race import Race as _Race
    _renderer = _R(assets)
    _race = _Race(T.load('country'), _renderer, harness.silent_audio(),
                  _S(T.TRACK_SPECS), _rnd.Random(1))
    rival = _race.cars[0]
    sprite_w = assets.get(rival.sprite).get_width()
    drawn = sprite_w * rival.size * OBJECT_SCALE / ROAD_WIDTH
    c.near(drawn, RIVAL_W - 0.005, RIVAL_W + 0.005,
           'rivals render %.3f road half-widths wide but collide at %.3f - '
           'you would hit an invisible edge' % (drawn, RIVAL_W))
    c.near(drawn, PLAYER_W * 0.9, PLAYER_W * 1.1,
           'rivals are a different size from the player car (%.3f vs %.3f)'
           % (drawn, PLAYER_W))
    c.note('rivals draw %.3f wide, collide at %.3f, player is %.3f'
           % (drawn, RIVAL_W, PLAYER_W))
    _race.clear()

    # -- the HUD must not swallow the player's car ---------------------
    _check_car_clears_hud(c)

    # -- and the same thing end to end, through the real renderer ------
    _check_gantry_pixels(c)

    return c.report()


def _check_car_clears_hud(c):
    """The instrument panel is drawn over the world, so the car has to sit
    above it. It used to be placed against the bottom of the screen, which put
    a third of every car - wheels, bumper and plate - behind the panel."""
    import random
    from game.render import Assets, Renderer, HEIGHT
    from game.race import Race, MAX_SPEED, HUD_BOTTOM, HUD_TOP
    from game import track as T, cars as garage
    from game.scores import Scores

    renderer = Renderer(Assets(harness.ROOT))
    panel_top = HEIGHT - HUD_BOTTOM
    for car in garage.CARS:
        race = Race(T.load('country'), renderer, harness.silent_audio(),
                    Scores(T.TRACK_SPECS), random.Random(3), car=car)
        race.state = Race.STATE_RACING
        race.player.speed = MAX_SPEED * 0.8
        for _ in range(120):          # let the bounce reach its extremes
            race.update(1 / 60.0, {'left': False, 'right': False,
                                   'accel': True, 'brake': False})
        img, (_, top) = race._player_sprite(0)
        bottom = top + img.get_height()
        hidden = max(0, bottom - panel_top)
        height = img.get_height()
        # Absolute limits on purpose: deriving the tolerance from CAR_SINK
        # would let the assertion drift along with the very value it guards.
        c.check(hidden <= 10,
                '%s is %dpx behind the instrument panel (10px is the limit)'
                % (car['name'], hidden))
        c.check(hidden <= height * 0.15,
                '%s has %.0f%% of its body behind the panel'
                % (car['name'], 100.0 * hidden / height))
        c.check(top > HUD_TOP,
                '%s reaches up into the top HUD bar (y=%d)'
                % (car['name'], top))
        c.check(hidden >= 0,
                '%s floats above the panel with a visible gap' % car['name'])
        race.clear()
    c.note('all %d cars sit clear of the instrument panel'
           % len(garage.CARS))


def _check_gantry_pixels(c):
    """Render the approach to the start gantry and measure where it actually
    lands on screen, by diffing against the same frame with the gantry taken
    out. Catches the anchoring being mis-wired in the render path itself, not
    just in the arithmetic."""
    import random
    import pygame
    from game.render import Assets, Renderer, WIDTH, HEIGHT
    from game.race import Race
    from game import track as T
    from game.scores import Scores

    renderer = Renderer(Assets(harness.ROOT))
    track = T.load('country')
    race = Race(track, renderer, harness.silent_audio(),
                Scores(T.TRACK_SPECS), random.Random(1))
    race.state = Race.STATE_RACING

    gantry_seg = next(s for s in track.segments
                      if any(sp[1] == 'obj_gantry' for sp in s.sprites))
    race.player.z = (gantry_seg.index * 200) - 5000
    race.player.x = 0.0
    race.player.speed = 0.0
    race.update(1 / 60.0, {'left': 0, 'right': 0, 'accel': 0, 'brake': 0})

    surface = pygame.Surface((WIDTH, HEIGHT)).convert()
    race.draw(surface)
    with_gantry = surface.copy()
    road_centre = gantry_seg.p1.sx          # projected centre of that segment

    stashed = gantry_seg.sprites
    gantry_seg.sprites = [s for s in stashed if s[1] != 'obj_gantry']
    race.draw(surface)
    without = surface.copy()
    gantry_seg.sprites = stashed

    xs = [x for x in range(WIDTH) for y in range(28, 120)
          if with_gantry.get_at((x, y)) != without.get_at((x, y))]
    if not c.check(len(xs) > 40,
                   'the gantry did not render at all (%d pixels differed)'
                   % len(xs)):
        race.clear()
        return
    left, right = min(xs), max(xs)
    centre = (left + right) / 2.0
    c.note('gantry drawn at x %d..%d, centre %.1f, road centre %.1f'
           % (left, right, centre, road_centre))
    c.check(abs(centre - road_centre) <= 2.0,
            'the rendered gantry is off-centre by %.1f px (drawn centre %.1f, '
            'road centre %.1f)' % (abs(centre - road_centre), centre,
                                   road_centre))
    race.clear()
