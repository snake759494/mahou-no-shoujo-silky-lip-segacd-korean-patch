# 게임 화면 우측 하트 로고 (魔法の少女 シルキーリップ → 마법의 소녀 / 실키립)
# M000~M088 공통 LZSS 스트림 (M000 0x15D7A, 압축 최대 0x25E 바이트, VRAM 0x3F0~)
import os, numpy as np
from PIL import Image, ImageDraw, ImageFont
from lzss import decode, encode
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, 'tools', 'fonts')
POS0, MAXLEN = 0x15d7a, 0x25e

def tiles_to_cv(out):
    cv = np.zeros((64, 64), np.uint8)
    for r in range(8):
        for c in range(8):
            t = 1 + r * 8 + c
            x = np.frombuffer(out[t * 32:t * 32 + 32], np.uint8)
            a = cv[r * 8:r * 8 + 8, c * 8:c * 8 + 8]; a[:, 0::2] = (x >> 4).reshape(8, 4); a[:, 1::2] = (x & 15).reshape(8, 4)
    return cv
def cv_to_tiles(out, cv):
    out = bytearray(out)
    for r in range(8):
        for c in range(8):
            t = 1 + r * 8 + c; a = cv[r * 8:r * 8 + 8, c * 8:c * 8 + 8]
            out[t * 32:t * 32 + 32] = ((a[:, 0::2] << 4) | a[:, 1::2]).astype(np.uint8).tobytes()
    return bytes(out)

def text_mask(s, font, size, spacing=0):
    f = ImageFont.truetype(os.path.join(FONTS, font), size)
    parts = []
    for ch in s:
        im = Image.new('L', (40, 20), 0); d = ImageDraw.Draw(im); d.fontmode = '1'
        if ch == ' ':
            parts.append(np.zeros((1, 3), bool)); continue
        bb = d.textbbox((0, 0), ch, font=f); d.text((-bb[0], -bb[1]), ch, font=f, fill=255)
        parts.append(np.array(im) >= 128)
    H = max(p.shape[0] for p in parts)
    cols = []
    for p in parts:
        ys, xs = np.nonzero(p)
        if len(xs) == 0: cols.append(np.zeros((H, 3), bool)); continue
        q = np.zeros((H, xs.max() + 1), bool); q[:p.shape[0], :] = p[:H, :xs.max() + 1][:, :]
        cols.append(q[:, xs.min():])
    gap = np.zeros((H, 1 + spacing), bool)
    m = cols[0]
    for q in cols[1:]: m = np.hstack([m, gap, q])
    ys, xs = np.nonzero(m)
    return m[:ys.max() + 1, :]

def dil(m):
    o = m.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1): o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o

def redraw(cv):
    cv = cv.copy()
    # 하트 모양 복원: 글자가 걸친 줄(18~40)은 위아래 하트 폭을 보간
    span = {}
    for y in range(64):
        xs = np.nonzero(cv[y] != 8)[0]
        if len(xs): span[y] = (xs.min(), xs.max())
    # 27행까지는 원래 외곽 유지, 28~40행은 27행과 41행 폭을 직선 보간 (글자가 하트 밖으로 삐져나온 부분)
    for y in range(18, 28):
        l, r = span[y]; row = cv[y].copy(); cv[y, :] = 8; cv[y, l:r + 1] = 4
    a, b = span[27], span[41]
    for y in range(28, 41):
        t = (y - 27) / 14
        l = round(a[0] + (b[0] - a[0]) * t); r = round(a[1] + (b[1] - a[1]) * t)
        cv[y, :] = 8; cv[y, l:r + 1] = 4
    def put(m, x, y):
        g = np.zeros((64, 64), bool); h, w = m.shape; g[y:y + h, x:x + w] = m
        cv[dil(g) & ~g] = 1; cv[g] = 15
    m1 = text_mask('마법의 소녀', 'Galmuri7.ttf', 8)
    put(m1, (64 - m1.shape[1]) // 2, 20)
    m2 = text_mask('실키립', 'Galmuri11-Bold.ttf', 12, spacing=3)
    put(m2, (64 - m2.shape[1]) // 2, 29)
    return cv

def build(mfile):
    out, used = decode(mfile, POS0)
    assert used <= MAXLEN
    cv = redraw(tiles_to_cv(out))
    new = encode(cv_to_tiles(out, cv))
    assert len(new) <= MAXLEN, ('HUD 로고 압축 초과', len(new), MAXLEN)
    return bytes(mfile[POS0:POS0 + MAXLEN]), new + bytes(MAXLEN - len(new)), cv

def patch_files(newfiles):
    old, new, _ = build(newfiles['M000'])
    n = 0
    for k, b in list(newfiles.items()):
        if not (k.startswith('M') and k[1:].isdigit()): continue
        p = b.find(old)
        if p < 0: continue
        nb = bytearray(b); nb[p:p + MAXLEN] = new; newfiles[k] = bytes(nb); n += 1
    return n

if __name__ == '__main__':
    import json
    W = os.path.join(ROOT, 'work')
    iso = open(os.path.join(W, 'track1.iso'), 'rb').read()
    F = {n: (l, s) for n, l, s in json.load(open(os.path.join(W, 'files.json')))}
    l, s = F['M000']; m = iso[l * 2048:l * 2048 + s]
    old, new, cv = build(m)
    print('압축', len(new.rstrip(b'\0')), '/', MAXLEN)
    pal = {1: (0, 0, 0), 4: (255, 0, 0), 8: (0, 68, 98), 15: (255, 255, 255)}
    im = np.zeros((64, 64, 3), np.uint8)
    for k, c in pal.items(): im[cv == k] = c
    Image.fromarray(im).resize((256, 256), Image.NEAREST).save(os.path.join(W, 's', 'hud_new.png'))
