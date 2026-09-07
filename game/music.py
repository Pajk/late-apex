"""The jukebox.

Race music is picked at random rather than tied to a circuit, and drawn from
a shuffled bag so every tune is heard once before any repeats.
"""

MENU = 'music_menu'

RACE = [
    ('music_city', 'NEON PURSUIT'),
    ('music_country', 'OPEN COUNTRY'),
    ('music_desert', 'DUST DEVIL'),
    ('music_winter', 'WHITEOUT'),
    ('music_summer', 'ALPINE RUSH'),
    ('music_night', 'NIGHT SHIFT'),
    ('music_sunstrip', 'SUNSTRIP'),
    ('music_overpass', 'OVERPASS'),
    ('music_redline', 'REDLINE'),
    ('music_coastal', 'COASTAL'),
    ('music_iron', 'IRON CIRCUIT'),
    ('music_lastlap', 'LAST LAP'),
]


class Jukebox:
    def __init__(self, rng):
        self.rng = rng
        self.bag = []

    def next(self):
        """(file, title). Refills and reshuffles once the bag runs dry, so you
        never hear the same tune twice in a row unless there is only one."""
        if not self.bag:
            self.bag = list(RACE)
            self.rng.shuffle(self.bag)
        return self.bag.pop()
