# 정보창(INFORMATION) 그래픽 라벨 한글화: M000~M088 공통 타일 블록
import os, numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_LABEL = os.path.join(ROOT, 'NanumSquareNeo-cBd.ttf')
F_SMALL = os.path.join(ROOT, 'tools', 'fonts', 'Galmuri9.ttf')
T0 = 0x300            # 블록 첫 타일 번호(VRAM)
NT = 0x38b - 0x300    # 타일 수

def find_block(b, sig):
    return b.find(sig)

def get_tile(blk, k):
    t = np.frombuffer(bytes(blk[(k - T0) * 32:(k - T0) * 32 + 32]), np.uint8)
    a = np.zeros((8, 8), np.uint8); a[:, 0::2] = (t >> 4).reshape(8, 4); a[:, 1::2] = (t & 15).reshape(8, 4)
    return a
def put_tile(blk, k, a):
    blk[(k - T0) * 32:(k - T0) * 32 + 32] = ((a[:, 0::2] << 4) | a[:, 1::2]).astype(np.uint8).tobytes()
def canvas(blk, rows):
    return np.vstack([np.hstack([get_tile(blk, k) for k in r]) for r in rows])
def store(blk, rows, c):
    for i, r in enumerate(rows):
        for j, k in enumerate(r):
            put_tile(blk, k, c[i * 8:i * 8 + 8, j * 8:j * 8 + 8])

def glyph_mask(ch, font, size, th=120):
    f = ImageFont.truetype(font, size)
    im = Image.new('L', (32, 32), 0); d = ImageDraw.Draw(im)
    bb = d.textbbox((0, 0), ch, font=f)
    d.text((8 - bb[0], 8 - bb[1]), ch, font=f, fill=255)
    m = np.array(im) >= th
    ys, xs = np.nonzero(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
def draw(c, m, x, y, fill, outline):
    h, w = m.shape
    big = np.zeros((c.shape[0] + 4, c.shape[1] + 4), bool)
    ys, xs = np.nonzero(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            yy = ys + y + dy + 2; xx = xs + x + dx + 2
            ok = (yy >= 0) & (yy < big.shape[0]) & (xx >= 0) & (xx < big.shape[1])
            big[yy[ok], xx[ok]] = True
    o = big[2:-2, 2:-2]
    c[o] = outline
    yy = ys + y; xx = xs + x
    ok = (yy >= 0) & (yy < c.shape[0]) & (xx >= 0) & (xx < c.shape[1])
    c[yy[ok], xx[ok]] = fill

def label(ch):
    return glyph_mask(ch, F_LABEL, 13)

def patch_block(blk):
    blk = bytearray(blk)
    # 체력
    R = [[0x315, 0x316, 0x317, 0x318], [0x319, 0x31a, 0x31b, 0x31c]]
    c = canvas(blk, R); c[:] = 8
    for ch, x in (('체', 2), ('력', 17)):
        m = label(ch); draw(c, m, x, 2 + (12 - m.shape[0]) // 2 + 1, 15, 1)
    store(blk, R, c)
    # 마도력 / 마도LV (마도 타일 공유)
    R = [[0x325, 0x326, 0x327, 0x328, 0x329], [0x32a, 0x32b, 0x32c, 0x32d, 0x32e]]
    c = canvas(blk, R); c[:] = 8
    for ch, x in (('마', 1), ('도', 13), ('력', 27)):
        m = label(ch); draw(c, m, x, 2 + (12 - m.shape[0]) // 2 + 1, 15, 1)
    store(blk, R, c)
    # 희 노 애
    for ch, R in (('희', [[0x31f, 0x320], [0x323, 0x324]]),
                  ('노', [[0x32f, 0x330], [0x331, 0x332]]),
                  ('애', [[0x339, 0x33a], [0x33b, 0x33c]])):
        c = canvas(blk, R); c[:] = 8
        m = label(ch); draw(c, m, (16 - m.shape[1]) // 2, 2 + (12 - m.shape[0]) // 2 + 1, 15, 1)
        store(blk, R, c)
    # 第 → 제, 話 → 화 (리본 위, 글자색 6)
    for ch, R, x0 in (('제', [[0x30a, 0x30b], [0x30f, 0x310]], 1),
                      ('화', [[0x311, 0x312], [0x313, 0x314]], 2)):
        c = canvas(blk, R)
        c[(c == 1) | (c == 6)] = 8
        m = label(ch); draw(c, m, x0, 2 + (12 - m.shape[0]) // 2 + 1, 6, 1)
        store(blk, R, c)
    # 시간대 리본: 아침/낮/저녁/밤
    for base, s in ((0x33d, '아침'), (0x349, '낮'), (0x355, '저녁'), (0x361, '밤')):
        R = [[base + 2 * i for i in range(6)], [base + 2 * i + 1 for i in range(6)]]
        c = canvas(blk, R)
        tm = (c == 1) | (c == 6)
        ys, xs = np.nonzero(tm)
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        # 텍스트 판 지우고 새로 그림
        f = ImageFont.truetype(F_SMALL, 10)
        im = Image.new('L', (64, 24), 0); d = ImageDraw.Draw(im)
        bb = d.textbbox((0, 0), s, font=f)
        d.text((0 - bb[0], 0 - bb[1]), s, font=f, fill=255)
        m = np.array(im) >= 128
        yy, xx = np.nonzero(m); m = m[:yy.max() + 1, :xx.max() + 1]
        h, w = m.shape
        cx = (x0 + x1 + 1) // 2 - w // 2; cy = (y0 + y1 + 1) // 2 - h // 2
        # 판: 새 글자 영역 + 원래 글자 영역 = 1, 원래 글자 6 제거
        c[tm] = 1
        c[y0:y1 + 1, x0:x1 + 1] = 1
        c[max(cy - 1, 0):cy + h + 1, max(cx - 1, 0):cx + w + 1] = 1
        sub = c[cy:cy + h, cx:cx + w]; sub[m] = 6
        store(blk, R, c)
    return bytes(blk)

def patch_files(newfiles, sig):
    n = 0
    for name, b in list(newfiles.items()):
        p = b.find(sig)
        if p < 0: continue
        blk = patch_block(b[p:p + NT * 32])
        nb = bytearray(b); nb[p:p + NT * 32] = blk
        q = bytes(nb).find(sig, p + 1)
        newfiles[name] = bytes(nb); n += 1
    return n

if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.chdir(os.path.join(ROOT, 'work'))
    from scan import get
    M = get('M000'); p = 0x14afa
    blk = patch_block(M[p:p + NT * 32])
    rows = [[0x307, 0x308, 0x309, 0x30a, 0x30b, 0x301, 0x36f, 0x311, 0x312, 0x33d, 0x33f, 0x341, 0x343, 0x345, 0x347],
            [0x30c, 0x30d, 0x30e, 0x30f, 0x310, 0x301, 0x370, 0x313, 0x314, 0x33e, 0x340, 0x342, 0x344, 0x346, 0x348],
            [0x315, 0x316, 0x317, 0x318, 0x301, 0x301, 0x377, 0x36d, 0x31d, 0x31e, 0x31f, 0x320, 0x301, 0x301, 0x301],
            [0x319, 0x31a, 0x31b, 0x31c, 0x301, 0x301, 0x378, 0x36e, 0x321, 0x322, 0x323, 0x324, 0x301, 0x301, 0x301],
            [0x325, 0x326, 0x327, 0x328, 0x329, 0x301, 0x36f, 0x36d, 0x321, 0x322, 0x32f, 0x330, 0x301, 0x301, 0x301],
            [0x32a, 0x32b, 0x32c, 0x32d, 0x32e, 0x301, 0x370, 0x36e, 0x321, 0x322, 0x331, 0x332, 0x301, 0x301, 0x301],
            [0x325, 0x326, 0x327, 0x333, 0x334, 0x301, 0x301, 0x389, 0x321, 0x322, 0x339, 0x33a, 0x301, 0x301, 0x301],
            [0x32a, 0x32b, 0x32c, 0x335, 0x336, 0x301, 0x301, 0x38a, 0x337, 0x338, 0x33b, 0x33c, 0x301, 0x301, 0x301]]
    pal = {0: (0, 0, 0), 1: (0, 0, 0), 4: (200, 0, 0), 5: (120, 0, 0), 6: (255, 255, 0), 8: (16, 64, 96), 15: (255, 255, 255)}
    out = []
    for B in (M[p:p + NT * 32], blk):
        c = canvas(B, rows)
        im = np.zeros(c.shape + (3,), np.uint8)
        for k in range(16): im[c == k] = pal.get(k, (k * 16,) * 3)
        out.append(im)
    for i, base in enumerate((0x349, 0x355, 0x361)):
        R = [[base + 2 * j for j in range(6)], [base + 2 * j + 1 for j in range(6)]]
        c = canvas(blk, R); im = np.zeros((16, 120, 3), np.uint8)
        sub = np.zeros(c.shape + (3,), np.uint8)
        for k in range(16): sub[c == k] = pal.get(k, (k * 16,) * 3)
        im[:, :48] = sub; out.append(im)
    W = max(o.shape[1] for o in out)
    full = np.vstack([np.pad(o, ((0, 4), (0, W - o.shape[1]), (0, 0))) for o in out])
    Image.fromarray(full).resize((full.shape[1] * 4, full.shape[0] * 4), Image.NEAREST).save('shots/panel_new.png')
