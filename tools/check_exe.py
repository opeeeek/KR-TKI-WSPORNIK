"""Kontrola pliku .exe: podsystem GUI, zasoby (ikona – grupa ID 2, manifest – ID 1) i osadzony interfejs HTML."""
import struct
import sys

p = sys.argv[1]
b = open(p, 'rb').read()
pe = struct.unpack_from('<I', b, 0x3C)[0]
assert b[pe:pe + 4] == b'PE\0\0', 'brak nagłówka PE'
nsec = struct.unpack_from('<H', b, pe + 6)[0]
opt = pe + 24
optsz = struct.unpack_from('<H', b, pe + 20)[0]
subsystem = struct.unpack_from('<H', b, opt + 68)[0]
rva_rsrc, size_rsrc = struct.unpack_from('<II', b, opt + 112 + 2 * 8)
secs = []
for i in range(nsec):
    o = opt + optsz + 40 * i
    name, vsize, va, rsize, praw = struct.unpack_from('<8sIIII', b, o)
    secs.append((name.rstrip(b'\0').decode(), va, vsize, praw, rsize))
def off(rva):
    for n, va, vs, pr, rs in secs:
        if va <= rva < va + max(vs, rs):
            return pr + rva - va
    raise ValueError(rva)
base = off(rva_rsrc)
found = []
def walk(o, path):
    nn, ni = struct.unpack_from('<HH', b, base + o + 12)
    for k in range(nn + ni):
        name, ptr = struct.unpack_from('<II', b, base + o + 16 + 8 * k)
        if ptr & 0x80000000:
            walk(ptr & 0x7FFFFFFF, path + [name])
        else:
            rva, size = struct.unpack_from('<II', b, base + ptr)
            found.append((path + [name], size, b[off(rva):off(rva) + 8]))
walk(0, [])
print('podsystem:', subsystem, '(2 = GUI)')
for path, size, head in found:
    print('zasób typ/id/jęz:', path, size, 'B', head)
types = {(f[0][0], f[0][1]) for f in found}
assert subsystem == 2
assert (14, 2) in types, 'brak grupy ikon ID 2'
assert (24, 1) in types, 'brak manifestu ID 1'
assert 'Krótki wspornik ST'.encode('utf8') in b, 'brak interfejsu HTML'
print('OK – plik', p, len(b), 'B')
