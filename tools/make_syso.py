"""Generuje app/rsrc_windows_amd64.syso – obiekt COFF z sekcją .rsrc (ikona programu i manifest) dołączany przez
`go build` do KrotkiWspornikST.exe. Grupa ikon ma ID 2 (WindowOptions.IconId w app/main.go), manifest ID 1.
Bez zależności zewnętrznych (format: PE/COFF, katalog zasobów IMAGE_RESOURCE_DIRECTORY)."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RT_ICON, RT_GROUP_ICON, RT_MANIFEST = 3, 14, 24
LANG = 0x0409


def read_ico(path: Path):
    b = path.read_bytes()
    _, typ, n = struct.unpack_from('<HHH', b, 0)
    if typ != 1 or n < 1:
        raise ValueError('niepoprawny plik .ico')
    imgs = []
    for i in range(n):
        w, h, cc, _r, planes, bpp, size, off = struct.unpack_from('<BBBBHHII', b, 6 + 16 * i)
        imgs.append(((w, h, cc, planes, bpp, size), b[off:off + size]))
    return imgs


def build(ico: Path, manifest: Path, out: Path) -> None:
    imgs = read_ico(ico)
    grp = struct.pack('<HHH', 0, 1, len(imgs)) + b''.join(
        struct.pack('<BBBBHHIH', w, h, cc, 0, planes, bpp, size, i + 1) for i, ((w, h, cc, planes, bpp, size), _) in enumerate(imgs))
    # zasoby: typ -> [(id, dane)]
    res = {RT_ICON: [(i + 1, d) for i, (_, d) in enumerate(imgs)], RT_GROUP_ICON: [(2, grp)], RT_MANIFEST: [(1, manifest.read_bytes())]}
    types = sorted(res)
    # układ: katalog główny, katalogi nazw, katalogi języków, wpisy danych, dane
    dir_size = lambda n: 16 + 8 * n  # noqa: E731
    off = dir_size(len(types))
    name_off = {}
    for t in types:
        name_off[t] = off
        off += dir_size(len(res[t]))
    lang_off = {}
    for t in types:
        for rid, _ in res[t]:
            lang_off[(t, rid)] = off
            off += dir_size(1)
    entry_off = {}
    for t in types:
        for rid, _ in res[t]:
            entry_off[(t, rid)] = off
            off += 16
    data_off = {}
    for t in types:
        for rid, d in res[t]:
            off = (off + 7) & ~7
            data_off[(t, rid)] = off
            off += len(d)
    raw = bytearray(off)
    hdr = lambda n: struct.pack('<IIHHHH', 0, 0, 4, 0, 0, n)  # noqa: E731
    raw[0:16] = hdr(len(types))
    for k, t in enumerate(types):
        struct.pack_into('<II', raw, 16 + 8 * k, t, 0x80000000 | name_off[t])
        o = name_off[t]
        raw[o:o + 16] = hdr(len(res[t]))
        for j, (rid, _) in enumerate(sorted(res[t])):
            struct.pack_into('<II', raw, o + 16 + 8 * j, rid, 0x80000000 | lang_off[(t, rid)])
    relocs = []
    for t in types:
        for rid, d in res[t]:
            o = lang_off[(t, rid)]
            raw[o:o + 16] = hdr(1)
            struct.pack_into('<II', raw, o + 16, LANG, entry_off[(t, rid)])
            e = entry_off[(t, rid)]
            struct.pack_into('<IIII', raw, e, data_off[(t, rid)], len(d), 0, 0)
            relocs.append(e)                                  # pole OffsetToData = RVA → relokacja ADDR32NB
            raw[data_off[(t, rid)]:data_off[(t, rid)] + len(d)] = d
    n_sec, sec_hdr = 1, 40
    p_raw = 20 + sec_hdr
    p_rel = p_raw + len(raw)
    p_sym = p_rel + 10 * len(relocs)
    coff = struct.pack('<HHIIIHH', 0x8664, n_sec, 0, p_sym, 1, 0, 0)
    sect = struct.pack('<8sIIIIIIHHI', b'.rsrc', 0, 0, len(raw), p_raw, p_rel, 0, len(relocs), 0, 0x40000040)
    rel = b''.join(struct.pack('<IIH', r, 0, 3) for r in relocs)         # IMAGE_REL_AMD64_ADDR32NB względem symbolu .rsrc
    sym = struct.pack('<8sIhHBB', b'.rsrc', 0, 1, 0, 3, 0)               # symbol sekcji (IMAGE_SYM_CLASS_STATIC)
    strtab = struct.pack('<I', 4)
    out.write_bytes(coff + sect + bytes(raw) + rel + sym + strtab)
    print(out, out.stat().st_size, 'B;', len(imgs), 'obrazów ikony')


if __name__ == '__main__':
    build(ROOT / 'app' / 'icon.ico', ROOT / 'app' / 'app.manifest', ROOT / 'app' / 'rsrc_windows_amd64.syso')
    sys.exit(0)
