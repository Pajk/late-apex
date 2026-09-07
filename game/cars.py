"""The garage.

Five original vehicles - no real marque is referenced, because car names,
badges and body shapes are all separately protected. Each one shifts the
handling enough to change which circuit suits it.

speed  top speed, as a fraction of the reference car
accel  how hard it pulls
grip   steering authority; low grip means you must brake earlier
mass   how well it shrugs off contact (higher loses less speed)
"""

CARS = [
    dict(key='wedge', name='SCARAB V8', tag='SCB',
         blurb='MID-ENGINED WEDGE - THE ALL ROUNDER',
         speed=1.00, accel=1.00, grip=1.00, mass=1.00,
         width=104, body=0.32, yield_traffic=False),
    dict(key='gt', name='MERIDIAN GT', tag='MRD',
         blurb='BIG GRAND TOURER - FAST BUT LAZY',
         speed=1.07, accel=0.94, grip=0.90, mass=1.18,
         width=110, body=0.34, yield_traffic=False),
    dict(key='coupe', name='BANTAM 16V', tag='BTM',
         blurb='LIGHT AND EAGER - LIVES IN THE CORNERS',
         speed=0.95, accel=1.14, grip=1.16, mass=0.86,
         width=96, body=0.29, yield_traffic=False),
    dict(key='ambulance', name='MEDIVAC 90', tag='MDV',
         blurb='SIRENS ON - THE FIELD GETS OUT OF YOUR WAY',
         speed=0.96, accel=0.98, grip=0.95, mass=1.25,
         width=94, body=0.33, yield_traffic=True),
    dict(key='van', name='TOURER 800', tag='TRR',
         blurb='EIGHT SEATS OF DEFIANCE - HEAVY, SLOW, PROUD',
         speed=0.94, accel=0.92, grip=0.88, mass=1.45,
         width=96, body=0.33, yield_traffic=False),
]

BY_KEY = {c['key']: c for c in CARS}
DEFAULT = CARS[0]


def get(key):
    return BY_KEY.get(key, DEFAULT)


def stat_bars(car):
    """(label, 0..1) rows for the selection screen."""
    return [
        ('SPEED', (car['speed'] - 0.88) / 0.24),
        ('ACCEL', (car['accel'] - 0.85) / 0.34),
        ('GRIP', (car['grip'] - 0.84) / 0.36),
        ('BULK', (car['mass'] - 0.80) / 0.72),
    ]
