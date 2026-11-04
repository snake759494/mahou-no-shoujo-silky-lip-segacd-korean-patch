# ISO(트랙1) 파일 교체 및 BIN 재구성
import json, struct, os, shutil
from cdsector import fix_mode1

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')

class Disc:
    def __init__(self, iso_path=os.path.join(WORK, 'track1.iso')):
        self.iso = bytearray(open(iso_path, 'rb').read())
        self.orig = bytes(self.iso)
        self.files = {n: (l, s) for n, l, s in json.load(open(os.path.join(WORK, 'files.json')))}

    def get(self, n):
        l, s = self.files[n]; return bytes(self.iso[l * 2048:l * 2048 + s])

    def put(self, n, data):
        l, s = self.files[n]
        cap = (s + 2047) // 2048 * 2048
        assert len(data) <= cap, (n, len(data), cap)
        if len(data) != s:
            self._set_size(n, len(data))
        self.iso[l * 2048:l * 2048 + len(data)] = data
        # 섹터 잔여부는 원본 유지(0 패딩)
        if len(data) < cap:
            self.iso[l * 2048 + len(data):l * 2048 + cap] = bytes(cap - len(data))

    def _set_size(self, n, size):
        # 루트 디렉터리 레코드 크기 갱신
        pvd = self.iso[16 * 2048:17 * 2048]
        r = pvd[156:190]
        dl, ds = struct.unpack('<I', r[2:6])[0], struct.unpack('<I', r[10:14])[0]
        blk_off = dl * 2048; i = 0
        while i < ds:
            ln = self.iso[blk_off + i]
            if ln == 0: i = (i // 2048 + 1) * 2048; continue
            e = self.iso[blk_off + i: blk_off + i + ln]
            nm = bytes(e[33:33 + e[32]]).decode().split(';')[0].rstrip('.')
            if nm == n:
                self.iso[blk_off + i + 10:blk_off + i + 14] = struct.pack('<I', size)
                self.iso[blk_off + i + 14:blk_off + i + 18] = struct.pack('>I', size)
                l, _ = self.files[n]; self.files[n] = (l, size); return
            i += ln
        raise KeyError(n)

    def write_bin(self, src_bin, dst_bin):
        shutil.copyfile(src_bin, dst_bin)
        changed = [k for k in range(len(self.iso) // 2048)
                   if self.iso[k * 2048:(k + 1) * 2048] != self.orig[k * 2048:(k + 1) * 2048]]
        with open(dst_bin, 'r+b') as f:
            for k in changed:
                f.seek(k * 2352); sec = bytearray(f.read(2352))
                sec[16:16 + 2048] = self.iso[k * 2048:(k + 1) * 2048]
                fix_mode1(sec)
                f.seek(k * 2352); f.write(sec)
        return changed
