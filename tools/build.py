# 마법소녀 실키립 한글패치 빌드
import sys, os, re, json, struct, glob, subprocess, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disc import Disc
from font import H2S, KANJI_BASE, patch_load, LIG_CH, LIGS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, 'work')
TR = os.path.join(WORK, 'tr')
BASE = 0x200000
CR = chr(13)
W_MAX = 13       # 한 줄 최대 칸
W_PREF = 13      # 자동 줄바꿈 목표 칸
L_MAX = 4        # 한 페이지 최대 줄

OV = {}
def load_tr():
    uniq = json.load(open(os.path.join(TR, 'uniq.json'), encoding='utf-8'))
    m = {}
    for fn in sorted(glob.glob(os.path.join(TR, 'k*.txt'))):
        for ln in open(fn, encoding='utf-8'):
            ln = ln.rstrip('\n')
            if not ln.strip(): continue
            i, kr = ln.split('\t', 1)
            for w in LIGS: kr = kr.replace('{' + w + '}', LIG_CH[w])
            if '@' in i:
                f, o = i.split('@'); OV[(f, int(o, 16))] = kr
            else:
                m[uniq[int(i)]] = kr
    return m

def wrap_page(text, width=W_PREF, indent=False):
    lines = []
    def lim():
        return width - 1 if (indent and lines) else width
    def push(l):
        lines.append(('　' + l) if (indent and lines) else l)
    for seg in text.split('|'):
        if seg.startswith('　'):
            lines.append(seg); continue
        cur = ''
        for w in seg.split(' '):
            cand = w if not cur else cur + ' ' + w
            if len(cand) <= lim(): cur = cand
            elif not cur: cur = w
            else:
                push(cur); cur = w
        push(cur)
    return lines

def compose(jp, kr, errs, tag):
    jpp = jp.split('@'); krp = kr.split('@')
    if len(jpp) != len(krp):
        errs.append(f'{tag}: 페이지 수 불일치 {len(jpp)}!={len(krp)}')
    out = []
    for pi, page in enumerate(krp):
        lead = 0
        if pi < len(jpp):
            o = jpp[pi]
            while lead < len(o) and o[lead] == '\r': lead += 1
        ind = False
        if pi < len(jpp):
            ol = jpp[pi].lstrip(CR).split(CR)
            ind = ol[0].startswith('「') and len(ol) > 1 and all(x.startswith('　') for x in ol[1:])
        lines = wrap_page(page, indent=ind and page.startswith('「'))
        body = [l for l in lines]
        # 앞쪽 줄바꿈(원문 유지) 제외 후 줄 수 검사
        vis = body[:]
        if len(vis) > L_MAX + (1 if page.startswith('|') else 0) + max(0, lead - 1):
            errs.append(f'{tag}: p{pi} {len(vis)}줄 {page}')
        for l in vis:
            if len(l) > W_MAX: errs.append(f'{tag}: 줄 길이 {len(l)} {l}')
        out.append('\r' * lead + '\r'.join(body))
    return '@'.join(out)

def encode(s, errs, tag):
    out = bytearray()
    for ch in s:
        if ch in H2S: out += H2S[ch]
        elif ch == '\r': out += b'\r'
        elif ch == ' ': out += b' '
        elif '\uac00' <= ch <= '\ud7a3':
            errs.append(f'{tag}: KS 미지원 음절 {ch}'); out += '？'.encode('cp932')
        else:
            try:
                b = ch.encode('cp932')
            except UnicodeEncodeError:
                errs.append(f'{tag}: 인코딩 불가 {ch!r}'); b = '？'.encode('cp932')
            if len(b) == 1 and ch not in '@':
                # 반각 문자는 전각으로 통일
                try: b = chr(ord(ch) + 0xFEE0).encode('cp932')
                except Exception: errs.append(f'{tag}: 반각 {ch!r}')
            out += b
    return bytes(out)

def ptr_map(b):
    P = {}
    for k in range(0, len(b) - 3, 2):
        v = struct.unpack('>I', b[k:k + 4])[0] - BASE
        if 0 <= v < len(b): P.setdefault(v, []).append(k)
    return P

def layout_file(name, b, items, tr, errs, stats):
    """items: [(s,e,ref,jp)] 정렬됨"""
    b = bytearray(b)
    P = ptr_map(bytes(b))
    enc = {}
    for s, e, ref, jp in items:
        kr = OV.get((name, s), tr.get(jp))
        if kr is None:
            stats['missing'] += 1; enc[s] = b[s:e]; continue
        enc[s] = encode(compose(jp, kr, errs, f'{name}@{s:x}'), errs, f'{name}@{s:x}')
    # 연속 블록 구성
    runs = []; cur = []
    for it in items:
        if cur and it[0] != cur[-1][1] + 1:
            runs.append(cur); cur = []
        cur.append(it)
    if cur: runs.append(cur)
    newpos = {}
    for run in runs:
        start = run[0][0]; end = run[-1][1] + 1   # end: 마지막 종료문자 다음
        movable = all(r[2] for r in run)
        if movable:
            pos = start
            for s, e, ref, jp in run:
                data = enc[s] + b'\0'
                newpos[s] = pos; pos += len(data)
            if pos > end:
                errs.append(f'{name}: 블록 {start:x}-{end:x} 초과 {pos-end}바이트')
                stats['over'] += pos - end
                continue
            buf = bytearray(end - start)
            for s, e, ref, jp in run:
                d = enc[s] + b'\0'; p = newpos[s] - start
                buf[p:p + len(d)] = d
            b[start:end] = buf
        else:
            starts = set(x[0] for x in items)
            for idx, (s, e, ref, jp) in enumerate(run):
                d = enc[s]
                if len(d) > e - s and idx == len(run) - 1:
                    k = e + 1
                    while k < len(b) and b[k] == 0 and k not in starts and k + 1 not in starts: k += 1
                    room = k - 1 - s   # 마지막 0은 종료문자로 남김
                    if len(d) <= room:
                        b[s:s + len(d)] = d; b[s + len(d)] = 0
                        newpos[s] = s; continue
                if len(d) > e - s:
                    errs.append(f'{name}@{s:x}: 고정 문자열 초과 {len(d)}>{e-s} {tr.get(jp)}')
                    stats['over'] += len(d) - (e - s); continue
                d = d + b' ' * (e - s - len(d))
                b[s:e] = d; newpos[s] = s
    # 포인터 갱신
    for s, np_ in newpos.items():
        if np_ != s:
            for k in P.get(s, []):
                b[k:k + 4] = struct.pack('>I', BASE + np_)
    return bytes(b)

def main(out_bin=os.path.join(WORK, 'test.bin'), check_only=False):
    tr = load_tr()
    S = json.load(open(os.path.join(WORK, 'strings.json'), encoding='utf-8'))
    byfile = {}
    for o in S:
        byfile.setdefault(o['f'], []).append((o['s'], o['e'], o['ref'], o['jp']))
    errs = []; stats = {'missing': 0, 'over': 0}
    D = Disc()
    # 폰트
    L = D.get('LOAD'); ref = L[KANJI_BASE:KANJI_BASE + 2350 * 18]
    newblk = bytes(patch_load(bytearray(L))[KANJI_BASE:KANJI_BASE + 2350 * 18 + 2 * len(LIGS) * 18])
    ref = L[KANJI_BASE:KANJI_BASE + 2350 * 18 + 2 * len(LIGS) * 18]
    newfiles = {}
    for n in D.files:
        b = D.get(n)
        if ref[:64] in b:
            b = b.replace(ref, newblk)
        newfiles[n] = b
    # 텍스트
    for n, items in byfile.items():
        items.sort()
        targets = [n]
        if n == 'P000': targets = [f'P{i:03d}' for i in range(89)]
        for t in targets:
            ob = D.get(t)
            for s, e, r, jp in items:
                if ob[s:e] != jp.encode('cp932'):
                    errs.append(f'{t}: 원문 불일치 {s:x}')
            newfiles[t] = layout_file(t, newfiles[t], items, tr, errs if t == targets[0] else [], stats)
    # 스크립트 기호가 섞인 문자열: 원문 바이트를 찾아 같은 길이로 치환
    RAW = [
        ('「シゴウしゃげたるぞ」', '「혼쭐내 줄 테다」'),
        ('「こんなん　どこの\r　もんじゃ？」', '「이건 대체 어디 거야？」'),
        ('「こんなん　どこん\r　もんじゃ？」', '「이건 대체 어디 거야？」'),
        ('「ワレ　道あけんかい！」', '「야 길 비켜！」'),
        ('「ほんとうの自由って何\r　だろう・・・」', '「진정한 자유란\r　뭘까・・・」'),
        ('「今日はさくら通りの\r　おもちゃやに\r　', '「오늘 사쿠라 거리\r　장난감 가게에\r　'),
        ('　１／１４４　改良強化\r　新型グフが入荷する', '　１／１４４ 개량강화\r　신형 구프가 들어올'),
        ('\r　はずだ　急いで帰ら\r　ないと・・・」', '\r　거야 빨리 집에\r　가야지・・・」'),
    ]
    for n in list(newfiles):
        if not re.match(r'^E\d\d\d$', n): continue
        b = bytearray(newfiles[n])
        for jp, kr in RAW:
            o = jp.encode('cp932'); k = encode(kr, errs, f'RAW {n}')
            if len(k) > len(o): errs.append(f'RAW 초과 {n} {kr}'); continue
            k = k + b' ' * (len(o) - len(k))
            p = b.find(o)
            while p >= 0:
                b[p:p + len(o)] = k; p = b.find(o, p + len(o))
        newfiles[n] = bytes(b)
    # 챕터 제목 카드
    import titlecard
    for i in range(11):
        n = f'TI{i+1:02d}'
        newfiles[n] = titlecard.patch(newfiles[n], i)
    # 타이틀 안내 문구
    import titlelogo
    newfiles['OP01'] = titlelogo.patch(newfiles['OP01'])[0]
    # 정보창 라벨 (M 파일 공통 블록)
    import panel
    m0 = D.get('M000'); sig = m0[0x14afa:0x14afa + panel.NT * 32]
    print('정보창 패치 파일 수', panel.patch_files(newfiles, sig))
    import hudlogo
    print('HUD 로고 패치 파일 수', hudlogo.patch_files(newfiles))
    for n, b in newfiles.items():
        if b != D.get(n): D.put(n, b)
    print('누락', stats['missing'], '초과', stats['over'], '오류', len(errs))
    with open(os.path.join(WORK, 'build_errors.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(errs))
    # 디스크 헤더 국내 게임명 (SJIS 48바이트 → UTF-8 한글)
    nm = '마법의 소녀 실키립'.encode('utf-8'); D.iso[0x120:0x150] = nm + b' ' * (48 - len(nm))
    if check_only: return errs
    ch = D.write_bin(os.path.join(WORK, 'orig.bin'), out_bin)
    print('변경 섹터', len(ch))
    return errs

if __name__ == '__main__':
    main(check_only='--check' in sys.argv)
