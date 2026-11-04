# 챕터 제목 카드(TI01~TI11) 한글화: 256x192 4bpp 비트맵 타일
import numpy as np, os
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FH = os.path.join(ROOT, 'NanumSquareNeo-eHv.ttf')
TITLES = [
    ('제1화', '마법 나라에서', '안녕하세요!'),
    ('제2화', '천재 소녀', '이자벨라 등장!'),
    ('제3화', '립의', '아르바이트'),
    ('제4화', '마법을 못 쓰게', '돼 버렸어!'),
    ('제5화', '흑마관의', '비밀을 쫓아라!'),
    ('제6화', '이자벨라가', '파트너!'),
    ('제7화', '거짓말! 마법이', '들켜 버렸어?'),
    ('제8화', '드디어 대결!', '립 VS 이자벨라!'),
    ('제9화', '비뚤어진 사랑의', '초콜릿'),
    ('제10화', '마계에서 온', '탈옥범!'),
    ('제11화', '안녕', '그리고… 고마워'),
]
H = 192
def dec(b):
    st = len(b) - 64 - 26624
    raw = np.frombuffer(b[st:st + 26624], np.uint8).reshape(832, 8, 4)
    px = np.zeros((832, 8, 8), np.uint8)
    px[:, :, 0::2] = raw >> 4; px[:, :, 1::2] = raw & 15
    return st, px.reshape(26, 32, 8, 8).transpose(0, 2, 1, 3).reshape(208, 256)
def enc(a):
    t = a.reshape(26, 8, 32, 8).transpose(0, 2, 1, 3).reshape(832, 8, 8)
    return ((t[:, :, 0::2] << 4) | t[:, :, 1::2]).astype(np.uint8).tobytes()
def mask_text(s, size, fit):
    while True:
        f = ImageFont.truetype(FH, size)
        bb = f.getbbox(s)
        if bb[2] - bb[0] <= fit or size <= 12: return f, bb
        size -= 1
def draw_line(a, s, size, fit, x, y, idx, right=False, shadow=1):
    f, bb = mask_text(s, size, fit)
    w = bb[2] - bb[0]
    im = Image.new('L', (256 + 40, H + 40), 0); d = ImageDraw.Draw(im)
    ox = (x - w if right else x) - bb[0]
    d.text((ox + 20, y - bb[1] + 20), s, font=f, fill=255)
    m = np.array(im)[20:20 + H, 20:20 + 256] >= 110
    if shadow is not None:
        sh = np.zeros_like(m)
        sh[1:, 1:] |= m[:-1, :-1]; sh[1:, :] |= m[:-1, :]; sh[:, 1:] |= m[:, :-1]
        a[:H][sh & ~m] = shadow
    a[:H][m] = idx
def patch(b, i):
    st, a = dec(b)
    a = a.copy()
    # 글자 지우기: 행별 배경 띠 색(9~f 중 최빈)으로
    for y in range(24, 158):
        row = a[y, 16:240]
        vals, cnt = np.unique(row[row >= 9], return_counts=True)
        bg = vals[cnt.argmax()]
        for x in range(16, 240):
            v = a[y, x]
            if v in (1, 3) or (v >= 9 and v != bg and y < 66):
                a[y, x] = bg
    lab, l1, l2 = TITLES[i]
    draw_line(a, lab, 24, 120, 44, 29, 15, shadow=None)
    draw_line(a, l1, 32, 212, 30, 66, 3)
    draw_line(a, l2, 32, 212, 232, 108, 3, right=True)
    return b[:st] + enc(a) + b[st + 26624:]
if __name__ == '__main__':
    import sys; sys.path.insert(0, os.path.dirname(__file__))
    os.chdir(os.path.join(ROOT, 'work'))
    from scan import get
    sheet = Image.new('L', (256 * 4, 192 * 3))
    for i in range(11):
        nb = patch(get(f'TI{i+1:02d}'), i)
        _, a = dec(nb)
        sheet.paste(Image.fromarray((a[:192] * 16).astype(np.uint8)), ((i % 4) * 256, (i // 4) * 192))
    sheet.save('shots/ti_new.png')
