"""Draws the app icon (1024x1024) from the same primitives as the sprites."""
import os
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from game import pixelfont  # noqa: E402
from tools.gen_assets import draw_car, mix  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def main():
    pygame.init()
    N = 1024
    s = pygame.Surface((N, N), pygame.SRCALPHA)
    # dusk gradient plate
    for y in range(N):
        t = y / (N - 1)
        s.fill(mix((22, 18, 54), (232, 96, 74), t ** 0.8), (0, y, N, 1))
    # road wedge
    pygame.draw.polygon(s, (58, 58, 70), [(N * 0.5, N * 0.42),
                                          (N * 1.06, N), (N * -0.06, N)])
    pygame.draw.polygon(s, (240, 240, 240), [(N * 0.5, N * 0.44),
                                             (N * 0.56, N), (N * 0.44, N)])
    # checkered band
    cell = N // 16
    for i in range(16):
        for j in range(2):
            c = (245, 245, 245) if (i + j) % 2 == 0 else (24, 24, 30)
            s.fill(c, (i * cell, N * 0.06 + j * cell * 0.6, cell,
                       int(cell * 0.6)))
    car = draw_car((214, 32, 40), w=120, h=68, lean=0)
    cw = int(N * 0.68)
    ch = int(cw * car.get_height() / car.get_width())
    car = pygame.transform.scale(car, (cw, ch))
    s.blit(car, ((N - cw) // 2, int(N * 0.54)))
    pixelfont.draw_text(s, 'LATE', N // 2, int(N * 0.20), (255, 236, 120),
                        scale=20, center=True, shadow=(140, 20, 40))
    pixelfont.draw_text(s, 'APEX', N // 2, int(N * 0.36), (255, 236, 120),
                        scale=20, center=True, shadow=(140, 20, 40))

    out = os.path.join(ROOT, 'assets', 'icon.png')
    pygame.image.save(s, out)
    print('wrote', out)


if __name__ == '__main__':
    main()
