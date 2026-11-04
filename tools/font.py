# 한글 12x12 1bpp 폰트 생성 + 한글<->SJIS(한자 슬롯) 매핑
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(ROOT, 'NanumSquareNeo-bRg.ttf')
KANJI_BASE = 0x11182          # LOAD 내 JIS 16구 1점(亜) 글리프 위치
GLYPH = 18

def ks_hangul():
    out = []
    for hi in range(0xB0, 0xC9):
        for lo in range(0xA1, 0xFF):
            out.append(bytes([hi, lo]).decode('euc-kr'))
    return out
HANGUL = ks_hangul()           # 2350자
assert len(HANGUL) == 2350

def slot_sjis(i):
    row = 16 + i // 94; col = 1 + i % 94
    j1 = row + 0x20; j2 = col + 0x20
    s1 = (j1 + 1) // 2 + (0x70 if j1 <= 0x5E else 0xB0)
    if j1 & 1:
        s2 = j2 + (0x1F if j2 <= 0x5F else 0x20)
    else:
        s2 = j2 + 0x7E
    return bytes([s1, s2])

H2S = {ch: slot_sjis(i) for i, ch in enumerate(HANGUL)}
S2H = {v: k for k, v in H2S.items()}

def render(ch, size=12, th=100):
    f = ImageFont.truetype(FONT_PATH, size)
    im = Image.new('L', (24, 24), 0); d = ImageDraw.Draw(im)
    # 고정 기준선: '한'의 세로 위치를 기준으로 모든 글자 동일 오프셋
    ref = d.textbbox((0, 0), '한', font=f)
    bb = d.textbbox((0, 0), ch, font=f)
    w = bb[2] - bb[0]
    x = 12 - w // 2 - bb[0]
    y = 12 - (ref[3] - ref[1]) // 2 - ref[1]
    d.text((x, y), ch, font=f, fill=255)
    a = np.array(im)[6:18, 6:18] >= th
    return a

def pack(a):
    bits = ''.join('1' if v else '0' for v in a.flatten())
    return int(bits, 2).to_bytes(18, 'big')

# 합자: 3음절을 2칸(24px)에 압축해 표시 (고정 길이 이름용)
LIGS = ['아나메', '헤이지', '진로쿠']
LIG_CH = {}
for _k, _w in enumerate(LIGS):
    LIG_CH[_w] = chr(0xE000 + 2 * _k) + chr(0xE001 + 2 * _k)
for _k in range(2 * len(LIGS)):
    H2S[chr(0xE000 + _k)] = slot_sjis(2350 + _k)

def render_lig(word):
    cols = []
    for ch in word:
        a = render(ch).astype(np.uint8) * 255
        im = Image.fromarray(a).resize((8, 12), Image.LANCZOS)
        cols.append(np.array(im) >= 90)
    big = np.concatenate(cols, axis=1)   # 12x24
    return big[:, :12], big[:, 12:]

def patch_load(load: bytearray):
    for i, ch in enumerate(HANGUL):
        off = KANJI_BASE + i * GLYPH
        load[off:off + GLYPH] = pack(render(ch))
    for k, w in enumerate(LIGS):
        l, r = render_lig(w)
        for j, a in enumerate((l, r)):
            off = KANJI_BASE + (2350 + 2 * k + j) * GLYPH
            load[off:off + GLYPH] = pack(a)
    return load
