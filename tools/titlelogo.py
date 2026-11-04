# 타이틀 화면 로고/안내문 한글화 (OP01 내 LZSS 압축 그래픽)
# 魔法の少女 → 마법의 소녀, シルキーリップ → 실키 립, スタートボタンを、押してね。♥ → 스타트 버튼을 눌러줘♥
import os, numpy as np
from PIL import Image, ImageDraw, ImageFont
from lzss import decode, encode
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_BIG = os.path.join(ROOT, 'NanumSquareNeo-eHv.ttf')
F_BIGW = os.path.join(ROOT, 'NanumSquareNeo-dEb.ttf')
F_TOP = os.path.join(ROOT, 'NanumSquareNeo-dEb.ttf')
F_SMALL = os.path.join(ROOT, 'tools', 'fonts', 'Galmuri7.ttf')
SC = 0x2c74e   # VRAM 0x0000~0x417F
SD = 0x309da   # VRAM 0x4180~0xA07F
END_C, END_D = 0x2e9da, 0x3247c

# 스프라이트 (x, y, w, h, 첫 타일) — 타이틀 SAT 덤프 기준
SPR_TOP = [(108, 41, 4, 3, 0x01), (140, 41, 4, 3, 0x0d), (172, 41, 4, 3, 0x19), (204, 41, 1, 3, 0x25)]
SPR_BIG = [(45 + 32 * i, 73, 4, 4, 0x28 + 0x18 * i) for i in range(7)] + \
          [(45 + 32 * i, 105, 4, 2, 0x38 + 0x18 * i) for i in range(7)]
SPR_HEART = [(253, 65, 3, 1, 0xd0), (269, 73, 1, 3, 0xd3)]
SPR_PRESS = [(88, 168, 4, 1, 0x416), (120, 168, 4, 1, 0x41a), (152, 168, 4, 1, 0x41e),
             (184, 168, 4, 1, 0x410), (216, 168, 2, 1, 0x414)]

def get_tile(v, t):
    b = np.frombuffer(bytes(v[t * 32:t * 32 + 32]), np.uint8)
    a = np.zeros((8, 8), np.uint8); a[:, 0::2] = (b >> 4).reshape(8, 4); a[:, 1::2] = (b & 15).reshape(8, 4)
    return a
def put_tile(v, t, a):
    v[t * 32:t * 32 + 32] = ((a[:, 0::2] << 4) | a[:, 1::2]).astype(np.uint8).tobytes()

def compose(v, sprs, cv):
    for x, y, w, h, t0 in sprs:
        for cx in range(w):
            for cy in range(h):
                cv[y + cy * 8:y + cy * 8 + 8, x + cx * 8:x + cx * 8 + 8] = get_tile(v, t0 + cx * h + cy)
def scatter(v, sprs, cv):
    for x, y, w, h, t0 in sprs:
        for cx in range(w):
            for cy in range(h):
                put_tile(v, t0 + cx * h + cy, cv[y + cy * 8:y + cy * 8 + 8, x + cx * 8:x + cx * 8 + 8])
def cover(sprs, shape):
    m = np.zeros(shape, bool)
    for x, y, w, h, t0 in sprs: m[y:y + h * 8, x:x + w * 8] = True
    return m

def mask(text, font, size, th=128):
    f = ImageFont.truetype(font, size)
    im = Image.new('L', (size * len(text) * 2 + 20, size * 2), 0); d = ImageDraw.Draw(im)
    bb = d.textbbox((0, 0), text, font=f); d.text((10 - bb[0], 10 - bb[1]), text, font=f, fill=255)
    m = np.array(im) >= th; ys, xs = np.nonzero(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
def dil(m, r=1):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o
def shift(m, dy, dx):
    return np.roll(np.roll(m, dy, 0), dx, 1)
def place(H, W, m, x, y):
    o = np.zeros((H, W), bool); h, w = m.shape; o[y:y + h, x:x + w] = m; return o

def draw_big(cv, cov, heart):
    H, W = cv.shape
    syl = [('실', 5), ('키', 6), ('립', 7)]
    ms = [mask(s, F_BIGW, 48, 120) for s, _ in syl]
    gap = 6; space = 10
    x0, x1 = 49, 262
    raw = sum(m.shape[1] for m in ms); k = min(1.35, (x1 - x0 - gap * 2 - space) / raw)
    x0 = (45 + 262 - (round(raw * k) + gap * 2 + space)) // 2
    ms = [np.array(Image.fromarray(m.astype(np.uint8) * 255).resize(
        (round(m.shape[1] * k), m.shape[0]), Image.NEAREST)) >= 128 for m in ms]
    x = x0; y = 76 + (40 - max(m.shape[0] for m in ms)) // 2
    full = np.zeros((H, W), bool); fills = []
    for i, m in enumerate(ms):
        g = place(H, W, m, x, y); fills.append((g, syl[i][1])); full |= g
        x += m.shape[1] + gap + (space if i == 1 else 0)
    def layer(full, fills):
        r1 = dil(full, 1); r2 = dil(full, 2)
        sh = (shift(r2, 1, 1) | shift(r2, 2, 1)) & ~r2
        cv[sh & cov & (cv == 0)] = 1
        cv[(r2 & ~r1) & cov] = 11
        cv[(r1 & ~full) & cov] = 15
        for g, c in fills: cv[g & cov] = c
    layer(full, fills)
    layer(heart, [(heart, 3)])

def draw_top(cv, cov):
    H, W = cv.shape
    m = mask('마법의 소녀', F_TOP, 20, 110)
    h, w = m.shape
    x = 108 + (104 - w) // 2; y = 41 + (22 - h) // 2
    g = place(H, W, m, x, y)
    r1 = dil(g, 1)
    sh = (shift(r1, 1, 0) | shift(r1, 1, 1)) & ~r1
    cv[sh & cov] = 14
    cv[(r1 & ~g) & cov] = 12
    hi = g & ~shift(g, 1, 0)       # 윗면 하이라이트
    cv[g & cov] = 10
    cv[hi & cov] = 13

def draw_press(cv, cov, col_a=3):
    H, W = cv.shape
    f = ImageFont.truetype(F_SMALL, 8)
    def m_of(s):
        im = Image.new('L', (200, 16), 0); d = ImageDraw.Draw(im); d.fontmode = '1'
        bb = d.textbbox((0, 0), s, font=f); d.text((-bb[0], -bb[1]), s, font=f, fill=255)
        a = np.array(im) >= 128; ys, xs = np.nonzero(a); return a[:ys.max() + 1, :xs.max() + 1]
    a = m_of('스타트 버튼'); b = m_of('을 눌러줘')
    tw = a.shape[1] + b.shape[1] + 2
    x = 220 - tw
    for m, col, xx in ((a, col_a, x), (b, 15, x + a.shape[1] + 2)):
        h, w = m.shape; yy = 168 + (7 - h) // 2 if h <= 7 else 168
        g = place(H, W, m[:8], xx, yy)
        cv[g & cov] = col

def patch(op01):
    b = bytearray(op01)
    C, nc = decode(b, SC); D, nd = decode(b, SD)
    assert SC + nc <= END_C and SD + nd <= END_D
    v = bytearray(C + D)
    cv = np.zeros((224, 320), np.uint8)
    # 위 작은 글자
    cov = cover(SPR_TOP, cv.shape); compose(v, SPR_TOP, cv); cv[cov] = 0
    draw_top(cv, cov); scatter(v, SPR_TOP, cv)
    # 큰 글자 (하트 장식은 유지)
    cv[:] = 0
    S = SPR_BIG + SPR_HEART
    cov = cover(S, cv.shape); compose(v, S, cv)
    hz = np.zeros(cv.shape, bool); hz[71:92, 256:278] = True
    heart = hz & (cv == 3)                                    # 하트 장식 모양은 원본에서 추출
    cv[cov] = 0
    draw_big(cv, cov, heart)
    scatter(v, S, cv)
    # 안내문 (끝의 하트 유지)
    cv[:] = 0
    cov = cover(SPR_PRESS, cv.shape); compose(v, SPR_PRESS, cv)
    keep = cv.copy(); cv[cov] = 0
    cv[168:176, 224:232] = keep[168:176, 224:232]   # ♥
    cov2 = cov.copy(); cov2[:, 222:] = False
    draw_press(cv, cov2); scatter(v, SPR_PRESS, cv)
    # 깜박임용 흰색 버전 (0x404~0x40F)
    alt = [(88, 168, 4, 1, 0x404), (120, 168, 4, 1, 0x408), (152, 168, 4, 1, 0x40c)]
    cv[:] = 0
    cova = cover(alt, cv.shape); compose(v, alt, cv); cv[cova] = 0
    draw_press(cv, cova, 15); scatter(v, alt, cv)
    nC = encode(bytes(v[:len(C)])); nD = encode(bytes(v[len(C):]))
    assert len(nC) <= END_C - SC, ('C 초과', len(nC), END_C - SC)
    assert len(nD) <= END_D - SD, ('D 초과', len(nD), END_D - SD)
    b[SC:SC + len(nC)] = nC; b[SD:SD + len(nD)] = nD
    return bytes(b), bytes(v)

if __name__ == '__main__':
    W = os.path.join(ROOT, 'work', 's')
    O = open(os.path.join(W, 'OP01.bin'), 'rb').read()
    nb, v = patch(O)
    pal = {0: (0, 128, 0), 1: (0, 0, 0), 3: (222, 0, 0), 5: (255, 101, 189), 6: (255, 153, 222), 7: (255, 186, 222),
           10: (189, 153, 0), 11: (156, 153, 156), 12: (255, 222, 0), 13: (255, 255, 0), 14: (65, 32, 0), 15: (255, 255, 255)}
    cv = np.zeros((224, 320), np.uint8)
    for s in (SPR_TOP, SPR_BIG, SPR_HEART, SPR_PRESS): compose(v, s, cv)
    im = np.zeros((224, 320, 3), np.uint8)
    for k, c in pal.items(): im[cv == k] = c
    Image.fromarray(im[30:185, 30:290]).resize((260 * 3, 155 * 3), Image.NEAREST).save(os.path.join(W, 'logo_new.png'))
