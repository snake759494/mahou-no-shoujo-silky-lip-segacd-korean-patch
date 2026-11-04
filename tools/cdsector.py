# Mode 1 섹터 EDC/ECC 재계산
EDC_T = []
for i in range(256):
    e = i
    for _ in range(8):
        e = (e >> 1) ^ (0xD8018001 if e & 1 else 0)
    EDC_T.append(e)
F_LUT = [0] * 256; B_LUT = [0] * 256
for i in range(256):
    j = (i << 1) ^ (0x11D if i & 0x80 else 0)
    F_LUT[i] = j & 0xFF
    B_LUT[i ^ j & 0xFF] = i

def edc(data):
    e = 0
    for b in data:
        e = (e >> 8) ^ EDC_T[(e ^ b) & 0xFF]
    return e

def _ecc_pq(sec, major_count, minor_count, major_mult, minor_inc, out_off):
    size = major_count * minor_count
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for minor in range(minor_count):
            t = sec[0xC + index]
            index += minor_inc
            if index >= size: index -= size
            a ^= t; b ^= t; a = F_LUT[a]
        a = B_LUT[F_LUT[a] ^ b]
        sec[out_off + major] = a
        sec[out_off + major + major_count] = a ^ b

def fix_mode1(sec):
    """sec: bytearray(2352), header/data already set"""
    e = edc(sec[0:0x810])
    sec[0x810:0x814] = e.to_bytes(4, 'little')
    sec[0x814:0x81C] = b'\0' * 8
    _ecc_pq(sec, 86, 24, 2, 86, 0x81C)
    _ecc_pq(sec, 52, 43, 86, 88, 0x8C8)
    return sec
