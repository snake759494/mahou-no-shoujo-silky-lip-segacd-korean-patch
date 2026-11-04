# 실키립 그래픽 압축 (LZSS, 1KB 창, 초기 0x000~0x2FF=0, 0x300~0x3FF=0xFF)
# 형식: [크기 LE16] { 플래그바이트(MSB부터, 1=참조) ; 리터럴 1바이트 | 참조 2바이트 LE: 하위10비트=창 절대위치, 상위6비트=길이 }

def _win():
    return bytearray(0x300) + bytearray(b'\xff' * 0x100)

def decode(src, pos=0):
    n = src[pos] | (src[pos + 1] << 8); p = pos + 2
    w = _win(); wp = 0; out = bytearray()
    while len(out) < n:
        fl = src[p]; p += 1
        for bit in range(8):
            if len(out) >= n: break
            if fl & (0x80 >> bit):
                v = src[p] | (src[p + 1] << 8); p += 2
                off = v & 0x3ff; ln = v >> 10
                for _ in range(ln):
                    c = w[off]; off = (off + 1) & 0x3ff
                    w[wp] = c; wp = (wp + 1) & 0x3ff; out.append(c)
                    if len(out) >= n: break
            else:
                c = src[p]; p += 1
                w[wp] = c; wp = (wp + 1) & 0x3ff; out.append(c)
    return bytes(out), p - pos

def encode(data):
    n = len(data); assert n < 0x10000
    w = _win(); wp = 0
    out = bytearray([n & 0xff, n >> 8])
    i = 0
    MAXL = 63
    while i < n:
        flag_pos = len(out); out.append(0); fl = 0
        for bit in range(8):
            if i >= n: break
            # 창에서 최장 일치 탐색 (겹침 복사 시뮬레이션)
            best = 0; boff = 0
            lim = min(MAXL, n - i)
            if lim >= 3:
                first = data[i]
                for off in range(0x400):
                    if w[off] != first: continue
                    # 시뮬레이션: 창 복사 중 쓰기가 읽기 앞을 덮을 수 있음
                    tw = None; l = 0; ro = off; wo = wp
                    while l < lim:
                        if tw is None:
                            c = w[ro]
                        else:
                            c = tw.get(ro, w[ro])
                        if c != data[i + l]: break
                        if tw is None: tw = {}
                        tw[wo] = c; wo = (wo + 1) & 0x3ff; ro = (ro + 1) & 0x3ff; l += 1
                    if l > best:
                        best = l; boff = off
                        if l == lim: break
            if best >= 3:
                fl |= 0x80 >> bit
                v = boff | (best << 10)
                out += bytes([v & 0xff, v >> 8])
                for k in range(best):
                    c = w[(boff + k) & 0x3ff]
                    w[wp] = c; wp = (wp + 1) & 0x3ff
                i += best
            else:
                w[wp] = data[i]; wp = (wp + 1) & 0x3ff
                out.append(data[i]); i += 1
        out[flag_pos] = fl
    return bytes(out)
