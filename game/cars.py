"""The garage.

Five original vehicles - no real marque is referenced, because car names,
badges and body shapes are all separately protected. Each one shifts the
handling enough to change which circuit suits it.

speed  top speed, as a fraction of the reference car
accel  how hard it pulls
grip   steering authority; low grip means you must brake earlier
mass   how well it shrugs off contact (higher loses less speed);
       shown as ARMOUR in the garage, where more is always better
turbos how many boosts you get in a race
engine which engine family it sounds like
"""

CARS = [
    dict(engine='v8', key='wedge', name='SCARAB V8', tag='SCB',
         blurb='MID-ENGINED WEDGE - THE ALL ROUNDER',
         speed=1.00, accel=1.00, grip=1.00, mass=1.00,
         width=104, body=0.32, yield_traffic=False),
    dict(engine='v12', key='gt', name='MERIDIAN GT', tag='MRD',
         blurb='BIG GRAND TOURER - FAST BUT LAZY',
         speed=1.07, accel=0.94, grip=0.90, mass=1.18,
         width=110, body=0.34, yield_traffic=False),
    dict(engine='four', key='coupe', name='BANTAM 16V', tag='BTM',
         blurb='LIGHT AND EAGER - LIVES IN THE CORNERS',
         speed=0.95, accel=1.14, grip=1.16, mass=0.86,
         width=96, body=0.29, yield_traffic=False),
    dict(engine='diesel', key='ambulance', name='MEDIVAC 90', tag='MDV',
         blurb='SIRENS ON - THE FIELD GETS OUT OF YOUR WAY',
         speed=0.96, accel=0.98, grip=0.95, mass=1.25,
         width=94, body=0.33, yield_traffic=True),
    dict(engine='diesel', key='van', name='TOURER 800', tag='TRR',
         blurb='EIGHT SEATS OF DEFIANCE - HEAVY, SLOW, PROUD',
         speed=0.94, accel=0.92, grip=0.88, mass=1.45,
         width=96, body=0.33, yield_traffic=False),
    dict(engine='v8', key='police', name='INTERCEPT 5', tag='INT',
         blurb='PURSUIT SPEC - FOUR BOOSTS INSTEAD OF THREE',
         speed=1.02, accel=1.06, grip=1.06, mass=1.20,
         width=110, body=0.33, yield_traffic=False, turbos=4),
    dict(engine='v10', key='f1', name='APEX GP', tag='GP1',
         blurb='SINGLE SEATER - VICIOUSLY FAST, MADE OF GLASS',
         speed=1.10, accel=1.26, grip=1.30, mass=0.50,
         width=116, body=0.30, yield_traffic=False),
    dict(engine='bike', key='bike', name='HORNET 900', tag='HNT',
         blurb='HALF THE WIDTH - GAPS OTHERS CANNOT TAKE',
         speed=1.02, accel=1.34, grip=1.22, mass=0.42,
         width=52, body=0.17, yield_traffic=False),
]

BY_KEY = {c['key']: c for c in CARS}
DEFAULT = CARS[0]


def get(key):
    return BY_KEY.get(key, DEFAULT)


def stat_bars(car):
    """(label, 0..1) rows for the selection screen."""
    return [
        ('SPEED', (car['speed'] - 0.88) / 0.26),
        ('ACCEL', (car['accel'] - 0.85) / 0.52),
        ('GRIP', (car['grip'] - 0.82) / 0.52),
        ('ARMOUR', (car['mass'] - 0.40) / 1.05),
    ]
