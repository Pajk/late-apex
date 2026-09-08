"""Difficulty levels.

Each level changes the road itself rather than just nudging numbers: how many
lanes it has, whether half of them carry traffic coming the other way, how
wide the tarmac is, and how much the car has to be slowed for a corner.

road        multiplies the drawn road width. The world keeps its scale, so a
            narrower road means your car takes up more of it.
oncoming    whether the left-hand lanes carry traffic at all.
centrifugal multiplies the sideways force in corners.
steer       multiplies steering authority.
animals     multiplies how many roadside animals wander onto the road, and
            animal_speed multiplies how fast they cross it - harder levels
            give you less warning as well as more of them.
time        multiplies the countdown, because slower corners mean slower laps.
"""

LEVELS = [
    dict(key='easy', name='EASY', stars=1,
         blurb='THREE LANES, EVERYONE GOING YOUR WAY',
         lanes=3, oncoming=0.0, road=1.00, centrifugal=1.00, steer=1.00,
         rivals=1.0, traffic=0.0, animals=0.6, animal_speed=0.85, time=1.00),
    dict(key='medium', name='MEDIUM', stars=2,
         blurb='FOUR LANES - THE LEFT TWO COME AT YOU',
         lanes=4, oncoming=1.0, road=1.14, centrifugal=1.00, steer=1.00,
         rivals=1.0, traffic=1.2, animals=1.0, animal_speed=1.05, time=1.10),
    dict(key='hard', name='HARD', stars=3,
         blurb='TWO LANES, HEAD ON TRAFFIC, REAL CORNERING',
         lanes=2, oncoming=1.0, road=0.74, centrifugal=1.55, steer=0.88,
         rivals=0.7, traffic=2.0, animals=1.6, animal_speed=1.3, time=1.45),
]

BY_KEY = {d['key']: d for d in LEVELS}
DEFAULT = LEVELS[0]


def get(key):
    return BY_KEY.get(key, DEFAULT)


def lane_centres(lanes):
    """Lane centres across the road, in road half-widths (-1 .. +1)."""
    return [-1.0 + (2.0 * i + 1.0) / lanes for i in range(lanes)]


def lanes_for(level):
    """(your lanes, oncoming lanes) as lists of centre offsets."""
    centres = lane_centres(level['lanes'])
    if not level['oncoming']:
        return centres, []
    mine = [c for c in centres if c > 0]
    theirs = [c for c in centres if c < 0]
    return mine or centres, theirs
