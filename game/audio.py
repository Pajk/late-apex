"""Sound front-end: streams the music, keeps a bank of engine loops and
crossfades between them so the revs follow the throttle."""

import os

import pygame

ENGINE_STEPS = 16


class Audio:
    def __init__(self, root):
        self.dir = os.path.join(root, 'assets', 'audio')
        self.ok = True
        try:
            # pygame.init() may already have opened the mixer with defaults;
            # reopen it at the rate the generated audio was written at.
            pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2,
                              buffer=512)
            pygame.mixer.set_num_channels(24)
        except pygame.error:
            self.ok = False
            return
        self.sfx = {}
        for fn in os.listdir(self.dir):
            if fn.startswith('sfx_') and fn.endswith('.wav'):
                self.sfx[fn[:-4]] = pygame.mixer.Sound(
                    os.path.join(self.dir, fn))
        self.engines = [pygame.mixer.Sound(
            os.path.join(self.dir, 'engine_%02d.wav' % i))
            for i in range(ENGINE_STEPS)]
        self.eng_ch = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
        self.skid_ch = pygame.mixer.Channel(2)
        self.cur_engine = -1
        self.slot = 0
        self.engine_on = False
        self.music_name = None
        self.music_volume = 0.55
        self.sfx_volume = 0.8
        self.skidding = False

    # -- music ----------------------------------------------------------
    def play_music(self, name, fade=400):
        if not self.ok or name == self.music_name:
            return
        path = os.path.join(self.dir, name + '.wav')
        if not os.path.exists(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1, fade_ms=fade)
            self.music_name = name
        except pygame.error:
            pass

    def stop_music(self, fade=300):
        if not self.ok:
            return
        pygame.mixer.music.fadeout(fade)
        self.music_name = None

    def set_music_volume(self, v):
        self.music_volume = max(0.0, min(1.0, v))
        if self.ok:
            pygame.mixer.music.set_volume(self.music_volume)

    # -- engine ---------------------------------------------------------
    def engine(self, rpm, load):
        """rpm 0..1 picks the sample, load 0..1 sets how hard it sings."""
        if not self.ok:
            return
        idx = max(0, min(ENGINE_STEPS - 1, int(rpm * (ENGINE_STEPS - 1) + 0.5)))
        vol = (0.16 + 0.34 * load) * self.sfx_volume
        if idx != self.cur_engine:
            self.slot ^= 1
            ch = self.eng_ch[self.slot]
            ch.play(self.engines[idx], loops=-1)
            ch.set_volume(vol)
            self.eng_ch[self.slot ^ 1].fadeout(90)
            self.cur_engine = idx
        else:
            self.eng_ch[self.slot].set_volume(vol)
        self.engine_on = True

    def engine_off(self):
        if not self.ok or not self.engine_on:
            return
        for ch in self.eng_ch:
            ch.fadeout(150)
        self.cur_engine = -1
        self.engine_on = False

    def skid(self, on, vol=0.5):
        if not self.ok:
            return
        if on and not self.skidding:
            self.skid_ch.play(self.sfx['sfx_skid'], loops=-1)
            self.skidding = True
        elif not on and self.skidding:
            self.skid_ch.fadeout(120)
            self.skidding = False
        if self.skidding:
            self.skid_ch.set_volume(vol * self.sfx_volume)

    # -- one shots ------------------------------------------------------
    def play(self, name, vol=1.0):
        if not self.ok:
            return
        s = self.sfx.get(name)
        if s is None:
            return
        ch = pygame.mixer.find_channel(True)
        if ch is not None:
            ch.set_volume(vol * self.sfx_volume)
            ch.play(s)

    def quiet(self):
        self.engine_off()
        self.skid(False)
