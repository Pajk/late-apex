"""Synthesises every sound in the game: six looping chiptune tracks, a set of
seamless engine loops, and the UI / collision effects.

    python tools/gen_music.py
"""
import os
import wave

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'assets', 'audio')
SR = 44100

NOTES = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7,
         'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def hz(name):
    """'A4' -> 440.0 ; '-' is a rest."""
    if name in ('-', None):
        return 0.0
    octave = int(name[-1])
    semi = NOTES[name[:-1]]
    midi = (octave + 1) * 12 + semi
    return 440.0 * 2 ** ((midi - 69) / 12.0)


# --------------------------------------------------------------------------
# Oscillators
# --------------------------------------------------------------------------

def _phase(f, n, detune=0.0):
    t = np.arange(n) / SR
    return (f * (1 + detune)) * t


def pulse(f, n, duty=0.5, detune=0.0):
    if f <= 0:
        return np.zeros(n)
    p = np.mod(_phase(f, n, detune), 1.0)
    return np.where(p < duty, 1.0, -1.0)


def triangle(f, n, detune=0.0):
    if f <= 0:
        return np.zeros(n)
    p = np.mod(_phase(f, n, detune), 1.0)
    return 4 * np.abs(p - 0.5) - 1.0


def saw(f, n, detune=0.0):
    if f <= 0:
        return np.zeros(n)
    p = np.mod(_phase(f, n, detune), 1.0)
    return 2 * p - 1.0


def noise(n, rng):
    return rng.uniform(-1, 1, n)


def env(n, a=0.005, d=0.05, s=0.7, r=0.06):
    """Sample-accurate ADSR that always fits inside n samples."""
    a_n = max(1, int(a * SR))
    d_n = max(1, int(d * SR))
    r_n = max(1, int(r * SR))
    if a_n + d_n + r_n > n:
        scale = n / float(a_n + d_n + r_n)
        a_n, d_n, r_n = max(1, int(a_n * scale)), max(1, int(d_n * scale)), \
            max(1, int(r_n * scale))
    s_n = max(0, n - a_n - d_n - r_n)
    return np.concatenate([
        np.linspace(0, 1, a_n),
        np.linspace(1, s, d_n),
        np.full(s_n, s),
        np.linspace(s, 0, r_n),
    ])[:n]


def lowpass(x, k=0.35):
    """One-pole filter, vectorised via a simple recursive pass."""
    out = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += k * (x[i] - acc)
        out[i] = acc
    return out


def fast_lowpass(x, width):
    """Cheap moving-average low pass (used on long noise beds)."""
    if width < 2:
        return x
    c = np.cumsum(np.insert(x, 0, 0))
    y = (c[width:] - c[:-width]) / width
    return np.concatenate([y, np.full(len(x) - len(y), y[-1] if len(y) else 0)])


# --------------------------------------------------------------------------
# Sequencer
# --------------------------------------------------------------------------

class Song:
    def __init__(self, bpm, bars, beats_per_bar=4, seed=0):
        self.bpm = bpm
        self.step = 60.0 / bpm / 4.0                # one 16th note
        self.total = int(bars * beats_per_bar * 4 * self.step * SR) + SR // 4
        self.buf = np.zeros(self.total)
        self.rng = np.random.default_rng(seed)

    def _at(self, step_index):
        return int(step_index * self.step * SR)

    def add(self, step_index, length_steps, data, gain=1.0):
        i = self._at(step_index)
        n = len(data)
        if i >= self.total:
            return
        n = min(n, self.total - i)
        self.buf[i:i + n] += data[:n] * gain

    def tone(self, step_index, length_steps, note, wave='pulse', duty=0.5,
             gain=0.2, adsr=(0.004, 0.05, 0.65, 0.05), detune=0.0, tail=1.0):
        f = hz(note)
        if f <= 0:
            return
        n = max(1, int(length_steps * self.step * SR * tail))
        if wave == 'pulse':
            w = pulse(f, n, duty, detune)
        elif wave == 'tri':
            w = triangle(f, n, detune)
        elif wave == 'saw':
            w = saw(f, n, detune)
        else:
            w = pulse(f, n, duty, detune)
        self.add(step_index, length_steps, w * env(n, *adsr), gain)

    def kick(self, i, gain=0.55):
        n = int(0.16 * SR)
        t = np.arange(n) / SR
        f = 140 * np.exp(-t * 26) + 44
        w = np.sin(2 * np.pi * np.cumsum(f) / SR)
        e = np.exp(-t * 15)
        self.add(i, 1, w * e, gain)

    def snare(self, i, gain=0.34):
        n = int(0.17 * SR)
        t = np.arange(n) / SR
        nz = fast_lowpass(self.rng.uniform(-1, 1, n), 3)
        tone = np.sin(2 * np.pi * 195 * t) * 0.4
        e = np.exp(-t * 24)
        self.add(i, 1, (nz + tone) * e, gain)

    def hat(self, i, gain=0.13, open_=False):
        n = int((0.10 if open_ else 0.035) * SR)
        t = np.arange(n) / SR
        nz = self.rng.uniform(-1, 1, n)
        nz = nz - fast_lowpass(nz, 4)          # crude high pass
        self.add(i, 1, nz * np.exp(-t * (24 if open_ else 70)), gain)

    def finish(self, peak=0.82, fade_in=0):
        b = self.buf
        m = np.max(np.abs(b)) or 1.0
        b = b / m * peak
        # soft clip for a little warmth
        b = np.tanh(b * 1.25) / np.tanh(1.25)
        if fade_in:
            k = int(fade_in * SR)
            b[:k] *= np.linspace(0, 1, k)
        return b


def write_wav(path, mono, stereo_spread=0.0):
    if stereo_spread > 0:
        d = int(SR * 0.012 * stereo_spread)
        left = mono.copy()
        right = np.concatenate([np.zeros(d), mono[:-d]]) if d else mono.copy()
        data = np.stack([left * 0.98 + right * 0.12,
                         right * 0.98 + left * 0.12], axis=1)
    else:
        data = np.stack([mono, mono], axis=1)
    pcm = np.clip(data, -1, 1)
    pcm = (pcm * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# --------------------------------------------------------------------------
# Note helpers
# --------------------------------------------------------------------------

SCALE_STEPS = {
    'minor': [0, 2, 3, 5, 7, 8, 10],
    'major': [0, 2, 4, 5, 7, 9, 11],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'dorian': [0, 2, 3, 5, 7, 9, 10],
}
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def note_from(root, octave, semis):
    idx = NOTES[root] + semis
    o = octave + idx // 12
    return NAMES[idx % 12] + str(o)


def chord_notes(root, octave, quality):
    intervals = {'m': [0, 3, 7], 'M': [0, 4, 7], 'm7': [0, 3, 7, 10],
                 'M7': [0, 4, 7, 11], 'sus': [0, 5, 7],
                 'dim': [0, 3, 6]}[quality]
    return [note_from(root, octave, i) for i in intervals]


def build_track(name, bpm, bars, prog, melody, *, lead_wave='pulse',
                lead_duty=0.5, arp_duty=0.25, seed=1, drums='rock',
                bass_octave=2, lead_gain=0.20, pad=False, swing=0.0):
    """prog: list of (root, quality) per bar. melody: list of (note, steps)
    played from the top, '-' for rests."""
    s = Song(bpm, bars, seed=seed)
    steps_per_bar = 16

    for bar in range(bars):
        root, qual = prog[bar % len(prog)]
        base = bar * steps_per_bar
        ch = chord_notes(root, bass_octave, qual)

        # bass: driving eighths with an octave lift, classic 80s racer
        for k in range(8):
            i = base + k * 2
            n = ch[0] if k % 4 != 3 else note_from(root, bass_octave + 1, 0)
            s.tone(i, 2, n, 'pulse', 0.5, gain=0.26,
                   adsr=(0.002, 0.03, 0.55, 0.05), tail=0.95)

        # arpeggio bed
        full = chord_notes(root, bass_octave + 2, qual)
        for k in range(16):
            n = full[k % len(full)]
            if k % 8 >= 4:
                n = note_from(root, bass_octave + 3, 0) if k % 4 == 3 else n
            s.tone(base + k, 1, n, 'pulse', arp_duty, gain=0.085,
                   adsr=(0.001, 0.02, 0.4, 0.03), tail=0.9)

        if pad:
            for n in chord_notes(root, bass_octave + 1, qual):
                s.tone(base, 16, n, 'tri', gain=0.055,
                       adsr=(0.25, 0.4, 0.6, 0.5), detune=0.004)
                s.tone(base, 16, n, 'tri', gain=0.05,
                       adsr=(0.25, 0.4, 0.6, 0.5), detune=-0.004)

        # drums
        if drums == 'rock':
            pattern_k = [0, 6, 8, 14]
            pattern_s = [4, 12]
        elif drums == 'drive':
            pattern_k = [0, 4, 8, 12]
            pattern_s = [4, 12]
        else:                                       # 'light'
            pattern_k = [0, 10]
            pattern_s = [8]
        for i in pattern_k:
            s.kick(base + i)
        for i in pattern_s:
            s.snare(base + i)
        for i in range(0, 16, 2):
            s.hat(base + i, gain=0.10, open_=(i % 8 == 6))

    # melody laid across the whole loop
    pos = 0
    limit = bars * steps_per_bar
    while pos < limit:
        for note, dur in melody:
            if pos >= limit:
                break
            if note != '-':
                s.tone(pos, dur, note, lead_wave, lead_duty, gain=lead_gain,
                       adsr=(0.006, 0.08, 0.62, 0.10), tail=0.98)
                s.tone(pos, dur, note, lead_wave, lead_duty, gain=lead_gain * 0.4,
                       adsr=(0.006, 0.08, 0.62, 0.10), detune=0.006, tail=0.98)
            pos += dur

    out = s.finish(0.80)
    write_wav(os.path.join(OUT, name + '.wav'), out, stereo_spread=1.0)
    return name


# --------------------------------------------------------------------------
# The six tunes
# --------------------------------------------------------------------------

def gen_music():
    made = []

    # Title screen: moody, mid-tempo, minor
    made.append(build_track(
        'music_menu', 108, 8,
        [('A', 'm'), ('F', 'M'), ('C', 'M'), ('G', 'M'),
         ('A', 'm'), ('F', 'M'), ('D', 'm'), ('E', 'm')],
        [('A4', 4), ('C5', 2), ('E5', 6), ('D5', 4),
         ('C5', 4), ('A4', 4), ('G4', 4), ('-', 4),
         ('F4', 4), ('A4', 4), ('C5', 6), ('B4', 2),
         ('A4', 8), ('-', 8)],
        lead_wave='pulse', lead_duty=0.25, arp_duty=0.125, seed=11,
        drums='light', pad=True, lead_gain=0.20))

    # City: fast synth-pop chase
    made.append(build_track(
        'music_city', 146, 8,
        [('A', 'm'), ('A', 'm'), ('F', 'M'), ('G', 'M'),
         ('A', 'm'), ('C', 'M'), ('F', 'M'), ('E', 'm')],
        [('A4', 2), ('A4', 2), ('C5', 2), ('E5', 2), ('D5', 4), ('C5', 4),
         ('B4', 2), ('C5', 2), ('D5', 4), ('E5', 4), ('-', 4),
         ('G4', 2), ('A4', 2), ('C5', 4), ('B4', 2), ('A4', 6),
         ('E5', 4), ('D5', 4), ('C5', 4), ('A4', 4)],
        lead_wave='pulse', lead_duty=0.5, arp_duty=0.25, seed=3,
        drums='drive', lead_gain=0.21))

    # Countryside: bright and bouncy major key
    made.append(build_track(
        'music_country', 132, 8,
        [('C', 'M'), ('G', 'M'), ('A', 'm'), ('F', 'M'),
         ('C', 'M'), ('G', 'M'), ('F', 'M'), ('G', 'M')],
        [('G4', 2), ('C5', 2), ('E5', 4), ('D5', 2), ('C5', 2), ('D5', 4),
         ('E5', 2), ('G5', 2), ('E5', 4), ('C5', 4), ('-', 4),
         ('A4', 2), ('C5', 2), ('F5', 4), ('E5', 4), ('C5', 4),
         ('D5', 4), ('E5', 4), ('G5', 4), ('C5', 4)],
        lead_wave='pulse', lead_duty=0.25, arp_duty=0.5, seed=5,
        drums='rock', lead_gain=0.20))

    # Desert: spanish-flavoured phrygian
    made.append(build_track(
        'music_desert', 124, 8,
        [('E', 'm'), ('F', 'M'), ('E', 'm'), ('D', 'm'),
         ('E', 'm'), ('F', 'M'), ('G', 'M'), ('F', 'M')],
        [('E4', 4), ('F4', 2), ('G4', 2), ('A4', 4), ('G4', 4),
         ('F4', 2), ('E4', 2), ('D4', 4), ('E4', 8),
         ('B4', 4), ('A4', 2), ('G4', 2), ('F4', 4), ('E4', 4),
         ('G4', 4), ('F4', 4), ('E4', 8)],
        lead_wave='saw', lead_duty=0.5, arp_duty=0.125, seed=8,
        drums='rock', lead_gain=0.17))

    # Winter: cold, sparse, wistful
    made.append(build_track(
        'music_winter', 116, 8,
        [('D', 'm'), ('A', 'm'), ('B', 'M'), ('F', 'M'),
         ('D', 'm'), ('G', 'm'), ('A', 'm'), ('A', 'M')],
        [('D5', 4), ('F5', 4), ('E5', 4), ('D5', 4),
         ('A4', 4), ('C5', 4), ('D5', 8),
         ('F5', 2), ('E5', 2), ('D5', 4), ('C5', 4), ('A4', 4),
         ('D5', 6), ('E5', 2), ('F5', 8)],
        lead_wave='tri', arp_duty=0.125, seed=13, drums='light',
        pad=True, lead_gain=0.26))

    # Summer mountains: fast, heroic, major
    made.append(build_track(
        'music_summer', 152, 8,
        [('D', 'M'), ('A', 'M'), ('B', 'm'), ('G', 'M'),
         ('D', 'M'), ('A', 'M'), ('G', 'M'), ('A', 'M')],
        [('D5', 2), ('E5', 2), ('F#5', 4), ('A5', 4), ('F#5', 4),
         ('E5', 2), ('D5', 2), ('E5', 4), ('F#5', 8),
         ('B4', 2), ('D5', 2), ('F#5', 4), ('E5', 4), ('D5', 4),
         ('A4', 4), ('B4', 4), ('D5', 8)],
        lead_wave='pulse', lead_duty=0.5, arp_duty=0.25, seed=21,
        drums='drive', lead_gain=0.21))
    return made


# --------------------------------------------------------------------------
# Engine loops + effects
# --------------------------------------------------------------------------

ENGINE_STEPS = 16

# One entry per engine family. A four-stroke fires each cylinder once every
# two revolutions, so `firings` is cylinders/2 per revolution.
ENGINES = {
    'v8': dict(firings=4, jitter=0.040, res=104, decay=105, noise=0.22,
               drive=1.5, sub=0.42, base=42, span=0.150, bright=0.55),
    'v12': dict(firings=6, jitter=0.006, res=182, decay=150, noise=0.16,
                drive=1.3, sub=0.14, base=46, span=0.150, bright=0.80),
    'four': dict(firings=2, jitter=0.014, res=158, decay=95, noise=0.26,
                 drive=1.7, sub=0.10, base=56, span=0.155, bright=0.90),
    'diesel': dict(firings=2, jitter=0.034, res=74, decay=62, noise=0.34,
                   drive=1.9, sub=0.30, base=32, span=0.132, bright=0.32,
                   clatter=1.10),
}


def circ_lowpass(x, width):
    """Moving average that wraps around the end of the buffer.

    The ordinary one starts from a cold state, so the first `width` samples
    come out attenuated and the loop clicks at the seam. Filtering circularly
    keeps a loop a loop.
    """
    width = int(width)
    if width < 2:
        return x
    n = len(x)
    ext = np.concatenate([x, x[:width]])
    c = np.cumsum(np.insert(ext, 0, 0))
    return (c[width:width + n] - c[:n]) / width


def _burst(res, decay, clatter, rng, length):
    """One exhaust pulse: a resonant thump with a little mechanical clatter."""
    t = np.arange(length) / SR
    env = np.exp(-t * decay)
    w = (np.sin(2 * np.pi * res * t)
         + 0.55 * np.sin(2 * np.pi * res * 2.0 * t + 0.7)
         + 0.30 * np.sin(2 * np.pi * res * 3.7 * t + 1.9))
    if clatter:
        w += clatter * rng.uniform(-1, 1, length) * np.exp(-t * decay * 3.2)
    return w * env


def engine_loop(spec, step, rng):
    """A seamless loop of an engine turning at one speed.

    Built from firing impulses rather than a stack of sine harmonics: the
    pulse train is what makes an engine sound like an engine, and adding the
    bursts with wraparound means the loop joins itself perfectly with no
    crossfade over the seam.
    """
    rise = 1.0 + step * spec['span']
    f_rev = spec['base'] * rise
    revs = max(4, int(round(f_rev * 0.30)))
    revs += revs % 2                       # even, so half-order sits in tune
    n = int(round(SR * revs / f_rev))
    f_rev = SR * revs / n                  # exact, for a clean loop

    firings = spec['firings']
    kernel = _burst(spec['res'] * (0.85 + 0.30 * rise), spec['decay'],
                    spec.get('clatter', 0.0), rng,
                    min(n, int(SR * 0.075)))
    sig = np.zeros(n)
    per_rev = n / revs
    for r in range(revs):
        for k in range(firings):
            # a little jitter on each firing is what gives a V8 its burble
            wobble = spec['jitter'] * (1 if (r + k) % 2 else -1)
            pos = int((r + (k + 0.5) / firings + wobble) * per_rev) % n
            end = pos + len(kernel)
            if end <= n:
                sig[pos:end] += kernel
            else:                          # wrap, keeping the loop seamless
                cut = n - pos
                sig[pos:] += kernel[:cut]
                sig[:end - n] += kernel[cut:]

    t = np.arange(n) / SR
    if spec['sub']:
        sig += spec['sub'] * np.sin(2 * np.pi * (f_rev / 2) * t)
    # intake and exhaust roar, brighter and louder the harder it is working
    width = max(2, int(46 - step * 2.4))
    nz = circ_lowpass(rng.uniform(-1, 1, n), width)
    sig += nz * spec['noise'] * (0.62 + 0.26 * step / 15.0)

    sig /= np.max(np.abs(sig)) or 1.0
    drive = spec['drive'] * (1.0 + 0.16 * step / 15.0)
    sig = np.tanh(sig * drive) / np.tanh(drive)
    sig = circ_lowpass(sig, max(2, int(9 - spec['bright'] * 6)))
    sig /= np.max(np.abs(sig)) or 1.0
    return sig


def gen_engine():
    """A bank of seamless loops per engine family, at rising revs. The game
    crossfades between neighbouring steps so the note tracks the rev counter."""
    made = []
    for family, spec in ENGINES.items():
        rng = np.random.default_rng(abs(hash(family)) % 10000)
        for i in range(ENGINE_STEPS):
            sig = engine_loop(spec, i, rng)
            name = 'engine_%s_%02d' % (family, i)
            write_wav(os.path.join(OUT, name + '.wav'), sig * 0.88)
            made.append(name)

    # a broadband layer that rides on top, tied to road speed
    rng = np.random.default_rng(7)
    n = int(1.6 * SR)
    nz = circ_lowpass(rng.uniform(-1, 1, n), 5)
    nz -= circ_lowpass(nz, 60)
    nz /= np.max(np.abs(nz)) or 1.0
    write_wav(os.path.join(OUT, 'engine_roar.wav'), nz * 0.7)
    made.append('engine_roar')

    # turbo whistle, looped while the boost is lit
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    base_hz = round(2450 * n / SR) * SR / n      # whole cycles in the loop
    vib_hz = round(11 * n / SR) * SR / n
    whine = np.zeros(n)
    for h, a in ((1, 1.0), (2, 0.35), (3, 0.12)):
        whine += a * np.sin(2 * np.pi * base_hz * h * t
                            + 0.6 * np.sin(2 * np.pi * vib_hz * t))
    whine += 0.25 * circ_lowpass(rng.uniform(-1, 1, n), 3)
    whine /= np.max(np.abs(whine)) or 1.0
    write_wav(os.path.join(OUT, 'engine_turbo.wav'), whine * 0.5)
    made.append('engine_turbo')
    return made


def gen_sfx():
    made = []
    rng = np.random.default_rng(4)

    def out(name, data, peak=0.85):
        d = data / (np.max(np.abs(data)) or 1.0) * peak
        write_wav(os.path.join(OUT, name + '.wav'), d)
        made.append(name)

    # skid: filtered noise with a bit of squeal, loops
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    nz = fast_lowpass(rng.uniform(-1, 1, n), 8)
    squeal = np.sin(2 * np.pi * (1180 + 90 * np.sin(2 * np.pi * 6.5 * t)) * t)
    sig = nz * 0.85 + squeal * 0.22
    x = int(n * 0.05)
    sig[:x] *= np.linspace(0, 1, x)
    sig[-x:] *= np.linspace(1, 0, x)
    out('sfx_skid', sig, 0.55)

    # crash: thump + debris
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * (np.cumsum(190 * np.exp(-t * 20) + 50) / SR))
    deb = fast_lowpass(rng.uniform(-1, 1, n), 3) * np.exp(-t * 9)
    metal = np.sin(2 * np.pi * 660 * t) * np.exp(-t * 26) * 0.3
    out('sfx_crash', (thump * np.exp(-t * 11) * 1.2 + deb * 0.9 + metal))

    # gentle scrape for kerbs / off-road
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    r = fast_lowpass(rng.uniform(-1, 1, n), 12) * (1 - t / t[-1])
    out('sfx_rumble', r, 0.5)

    def beep(freq, dur, wave='pulse', duty=0.5, decay=6.0, vib=0.0):
        n = int(dur * SR)
        t = np.arange(n) / SR
        f = freq * (1 + vib * np.sin(2 * np.pi * 7 * t))
        p = np.mod(np.cumsum(f) / SR, 1.0)
        w = np.where(p < duty, 1.0, -1.0) if wave == 'pulse' \
            else 4 * np.abs(p - 0.5) - 1
        return w * np.exp(-t * decay) * (1 - np.exp(-t * 400))

    out('sfx_countdown', beep(523.25, 0.28, decay=7))
    out('sfx_go', np.concatenate([beep(1046.5, 0.5, decay=3.2),
                                  np.zeros(int(0.01 * SR))]))
    out('sfx_blip', beep(880, 0.07, duty=0.25, decay=26), 0.6)
    out('sfx_select', np.concatenate([beep(523, 0.06, duty=0.25, decay=22),
                                      beep(784, 0.06, duty=0.25, decay=22),
                                      beep(1046, 0.16, duty=0.25, decay=10)]),
        0.7)
    out('sfx_lap', np.concatenate([beep(784, 0.12, duty=0.25, decay=12),
                                   beep(1175, 0.30, duty=0.25, decay=7)]), 0.75)
    out('sfx_extend', np.concatenate([beep(659, 0.09, duty=0.5, decay=16),
                                      beep(880, 0.09, duty=0.5, decay=16),
                                      beep(1318, 0.26, duty=0.5, decay=8)]))

    # gearchange: a mechanical clack with a hint of driveline
    n = int(0.10 * SR)
    t = np.arange(n) / SR
    clack = rng.uniform(-1, 1, n) * np.exp(-t * 150)
    clack += np.sin(2 * np.pi * 220 * t) * np.exp(-t * 90) * 0.5
    clack += np.sin(2 * np.pi * 1400 * t) * np.exp(-t * 210) * 0.3
    out('sfx_shift', clack, 0.45)

    # turbo dump valve on lift
    n = int(0.34 * SR)
    t = np.arange(n) / SR
    air = fast_lowpass(rng.uniform(-1, 1, n), 3)
    air = air - fast_lowpass(air, 26)
    out('sfx_blowoff', air * np.exp(-t * 11) * (1 - np.exp(-t * 300)), 0.6)

    # short victory fanfare (played over the results screen)
    fan = []
    for f, d in ((523, 0.13), (659, 0.13), (784, 0.13), (1046, 0.42),
                 (880, 0.13), (1046, 0.55)):
        fan.append(beep(f, d, duty=0.5, decay=3.6) * 0.8 +
                   beep(f * 2, d, duty=0.25, decay=4.4) * 0.25)
    out('sfx_fanfare', np.concatenate(fan), 0.8)

    # failure sting
    down = []
    for f, d in ((392, 0.18), (330, 0.18), (262, 0.18), (196, 0.6)):
        down.append(beep(f, d, duty=0.5, decay=3.0))
    out('sfx_gameover', np.concatenate(down), 0.8)
    return made


def main():
    os.makedirs(OUT, exist_ok=True)
    m = gen_music()
    e = gen_engine()
    s = gen_sfx()
    print('generated %d tunes, %d engine loops, %d effects -> %s'
          % (len(m), len(e), len(s), OUT))


if __name__ == '__main__':
    main()
