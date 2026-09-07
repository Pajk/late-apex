"""Old-school 3-character high score tables, saved between sessions."""

import json
import os

TABLE_SIZE = 8
NAME_LEN = 3
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-!'

_SEED_NAMES = ['ACE', 'MAX', 'REV', 'JET', 'ZAP', 'KIT', 'FOX', 'AMI']
_SEED_CARS = ['SCB', 'MRD', 'BTM', 'SCB', 'MDV', 'BTM', 'TRR', 'MRD']


def save_dir():
    """Where the table is kept. LATE_APEX_DATA_DIR overrides it, which
    lets the test suite run without touching real high scores."""
    base = os.environ.get('LATE_APEX_DATA_DIR') or os.path.expanduser(
        '~/Library/Application Support/LateApex')
    try:
        os.makedirs(base, exist_ok=True)
        return base
    except OSError:
        return os.path.expanduser('~')


def format_time(seconds):
    if seconds is None or seconds >= 5999:
        return '--:--.--'
    m = int(seconds // 60)
    s = seconds - m * 60
    return '%d:%05.2f' % (m, s)


class Scores:
    def __init__(self, tracks):
        self.path = os.path.join(save_dir(), 'scores.json')
        self.track_keys = [t['key'] for t in tracks]
        self.data = {}
        self._seed(tracks)
        self.load()

    def _seed(self, tracks):
        for spec in tracks:
            k = spec['key']
            par_race = (spec['start_time'] + spec['lap_bonus'] * 2) * 0.97
            par_lap = par_race / 3.0
            self.data[k] = {
                'race': [{'name': _SEED_NAMES[i % len(_SEED_NAMES)],
                          'time': round(par_race * (1.0 + 0.05 * i), 2),
                          'car': _SEED_CARS[i % len(_SEED_CARS)]}
                         for i in range(TABLE_SIZE)],
                'lap': [{'name': _SEED_NAMES[(i + 3) % len(_SEED_NAMES)],
                         'time': round(par_lap * (1.0 + 0.05 * i), 2),
                         'car': _SEED_CARS[(i + 2) % len(_SEED_CARS)]}
                        for i in range(TABLE_SIZE)],
            }

    def load(self):
        try:
            with open(self.path) as fh:
                raw = json.load(fh)
        except (OSError, ValueError):
            return
        for k, v in raw.items():
            if k not in self.data or not isinstance(v, dict):
                continue
            for kind in ('race', 'lap'):
                rows = v.get(kind)
                if not isinstance(rows, list):
                    continue
                clean = []
                for r in rows:
                    try:
                        name = str(r['name'])[:NAME_LEN].upper() or '---'
                        t = float(r['time'])
                    except (KeyError, TypeError, ValueError):
                        continue
                    row = {'name': name, 'time': t}
                    if r.get('car'):
                        row['car'] = str(r['car'])[:3].upper()
                    clean.append(row)
                if clean:
                    clean.sort(key=lambda r: r['time'])
                    self.data[k][kind] = clean[:TABLE_SIZE]

    def save(self):
        try:
            with open(self.path, 'w') as fh:
                json.dump(self.data, fh, indent=1)
        except OSError:
            pass

    # -- queries --------------------------------------------------------
    def table(self, track_key, kind):
        return self.data[track_key][kind]

    def best(self, track_key, kind):
        rows = self.data[track_key][kind]
        return rows[0]['time'] if rows else None

    def position(self, track_key, kind, time):
        """1-based place this time would take, or None if it misses the table."""
        rows = self.data[track_key][kind]
        for i, r in enumerate(rows):
            if time < r['time']:
                return i + 1
        return len(rows) + 1 if len(rows) < TABLE_SIZE else None

    def insert(self, track_key, kind, name, time, car=None):
        pos = self.position(track_key, kind, time)
        if pos is None:
            return None
        rows = self.data[track_key][kind]
        row = {'name': name[:NAME_LEN].upper(), 'time': time}
        if car:
            row['car'] = str(car)[:3].upper()
        rows.insert(pos - 1, row)
        del rows[TABLE_SIZE:]
        self.save()
        return pos
