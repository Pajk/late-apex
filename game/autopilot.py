"""A driver that reads the road ahead.

Used three ways: the attract-mode demo behind the menus, the balance tests,
and the screenshot/GIF capture tool. Keeping one implementation means the
demo drives as well as the thing the tests measure.
"""

from . import difficulty as diff
from .race import MAX_SPEED, CENTRIFUGAL


def corner_limit(track, z, look_ahead):
    """The fraction of top speed the tightest corner within `look_ahead`
    can actually be held at, derived from the same physics the car uses:
    sideways push grows with speed squared, steering only linearly.
    """
    worst = 0.0
    for dz in range(200, int(look_ahead), 200):
        curve = track.segment_at(z + dz).curve
        if abs(curve) > abs(worst):
            worst = curve
    if abs(worst) <= 0.4:
        return 2.0, worst
    grip = track.theme['grip']
    authority = 2.5 * (0.55 + 0.45 * grip)
    return authority * grip / (abs(worst) * CENTRIFUGAL), worst


def drive(race, skill=0.85):
    """Return a key state dict. `skill` 0..1 sets how far ahead the driver
    looks and how close to the limit it dares to run."""
    player, track = race.player, race.track
    look = 600 + 2600 * skill
    limit, _ = corner_limit(track, player.z, look)
    limit = min(1.0, limit) * (0.72 + 0.26 * skill)
    limit /= race.level['centrifugal'] ** 0.5

    here = track.segment_at(player.z).curve
    mine, oncoming = diff.lanes_for(race.level)
    target = -here * 0.10
    if oncoming:
        # Keep to the middle of our own side. Hugging the outer lane leaves
        # no room for the car to be pushed wide in a corner.
        centre = sum(mine) / len(mine)
        target = centre + max(-0.2, min(0.2, target))
        target = max(min(mine), min(max(mine), target))
    else:
        target = max(-0.75, min(0.75, target))
    error = target - player.x
    ratio = player.speed / MAX_SPEED
    return {'left': error < -0.03, 'right': error > 0.03,
            'accel': ratio < limit, 'brake': ratio > limit * 1.06}
