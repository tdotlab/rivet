#!/usr/bin/env python3
"""Slice-27 survey: bank 7 gaps, bank 8 gaps, bank-0 tail $3947-$3fff,
bank 11 $7e3d-$7fff.

Questions per gap:
  1. Code or data? (gb_rd walk from gap start; ret density; distinct bytes)
  2. Entry points: call/jp/jr/table targets only -- ROM-wide byte search
     for absolute cf targets into the gap, plus carved-src cf references.
  3. Any code touching hStateTimer ($ff90), [$c70b], or the clear chain?
  4. Bank 11 $7e3d-$7fff: truly all $ff? Bank-0 tail: SGB code continuation?
Run: python3 tools/survey27_gaps.py
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, spans  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()


def bank_bytes(n):
    return rom[n * 0x4000:(n + 1) * 0x4000]


GAPS = {
    7: [(0x6581, 0x664D), (0x67A1, 0x68AC), (0x68C4, 0x695A),
        (0x6ED2, 0x6F05), (0x7001, 0x714B), (0x71BA, 0x7509),
        (0x7610, 0x77A8), (0x7ABB, 0x7D5D), (0x7E18, 0x7EDC),
        (0x7F0D, 0x8000)],
    8: [(0x5809, 0x5E36), (0x611F, 0x6273), (0x6283, 0x63B4),
        (0x6669, 0x67BC), (0x67CC, 0x68B7), (0x68EF, 0x69AE),
        (0x69BE, 0x6A24), (0x6A34, 0x6ABA), (0x6ACA, 0x6D89),
        (0x7292, 0x730F), (0x74F4, 0x7525), (0x7588, 0x7601),
        (0x762A, 0x7684), (0x76B6, 0x76E2), (0x781A, 0x8000)],
    11: [(0x7E3D, 0x8000)],
}

# absolute cf opcodes with a 16-bit target: call, jp, jp cc
ABS_OPS = {0xC3, 0xCD, 0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA}


def rom_cf_targets(lo, hi):
    """ROM-wide byte search for absolute cf instructions whose target
    lands in [lo, hi). Returns {target: [(bank, addr, opcode)]}.
    (Byte search: hits in data regions are possible; callers are
    verified against carved code afterwards.)"""
    hits = {}
    for bank in range(32):
        base = bank * 0x4000
        b = rom[base:base + 0x4000]
        for i in range(len(b) - 2):
            op = b[i]
            if op in ABS_OPS:
                tgt = b[i + 1] | (b[i + 2] << 8)
                if lo <= tgt < hi:
                    addr = 0x4000 + i if bank else i
                    hits.setdefault(tgt, []).append((bank, addr, op))
    return hits


def src_cf_targets(lo, hi):
    cf = re.compile(r"\b(?:call|jp|jr)\s+(?:[a-z]+\s*,\s*)?\$([0-9a-f]{4})\b")
    ld = re.compile(r"ld\s+(?:hl|de|bc),\s*\$([0-9a-f]{4})")
    out_cf, out_ld = {}, {}
    import glob
    for fname in sorted(glob.glob("src/*.asm")):
        txt = open(fname).read()
        for m in cf.finditer(txt):
            a = int(m.group(1), 16)
            if lo <= a < hi:
                out_cf.setdefault(a, []).append(fname)
        for m in ld.finditer(txt):
            a = int(m.group(1), 16)
            if lo <= a < hi:
                out_ld.setdefault(a, []).append(fname)
    return out_cf, out_ld


def survey_gap(bank, lo, hi):
    b = bank_bytes(bank)
    seg = b[lo - 0x4000:hi - 0x4000]
    nff = seg.count(0xFF)
    nz = seg.count(0x00)
    distinct = len(set(seg))
    rets = seg.count(0xC9)
    last_nz = None
    for i in range(len(seg) - 1, -1, -1):
        if seg[i] != 0xFF:
            last_nz = lo + i
            break
    print(f"  bank {bank} ${lo:04x}-${hi:04x} len={hi-lo} ff={nff} "
          f"zero={nz} distinct={distinct} ret(c9)={rets} "
          f"last_non_ff=${last_nz:04x}" if last_nz else
          f"  bank {bank} ${lo:04x}-${hi:04x} len={hi-lo} ALL $ff")
    print(f"    head: {seg[:32].hex()}")
    if nff < len(seg):
        reached, rst08, notes = walk(bank, [lo])
        sp = spans(reached)
        print(f"    walk from ${lo:04x}: {len(reached)} instrs, "
              f"spans {[(f'${a:04x}', f'${c:04x}') for a, c in sp][:8]}, "
              f"rst08={ {f'${k:04x}': len(v) for k, v in rst08.items()} }, "
              f"notes={notes[:3]}")
        # hStateTimer / c70b / ff8e patterns in the raw bytes
        for pat, name in ((b"\xe0\x90", "ldh [$ff90],a"),
                          (b"\xf0\x90", "ldh a,[$ff90]"),
                          (b"\xea\x0b\xc7", "ld [$c70b],a"),
                          (b"\xfa\x0b\xc7", "ld a,[$c70b]"),
                          (b"\xe0\x8e", "ldh [$ff8e],a")):
            idx = seg.find(pat)
            if idx >= 0:
                print(f"    !! {name} pattern at ${lo + idx:04x}")
    cf = rom_cf_targets(lo, hi)
    if cf:
        summ = ", ".join(
            f"${t:04x}: {len(v)}x" for t, v in sorted(cf.items()))
        print(f"    ROM-wide abs-cf targets into gap: {{{summ}}}")
        for t, v in sorted(cf.items()):
            for bank2, addr, op in v[:6]:
                print(f"      ${t:04x} <- bank {bank2} ${addr:04x} "
                      f"op ${op:02x}")
    scf, sld = src_cf_targets(lo, hi)
    if scf:
        print(f"    carved-src cf targets: "
              f"{ {f'${k:04x}': sorted(set(v)) for k, v in sorted(scf.items())} }")
    if sld:
        print(f"    carved-src ld-pointer reads: "
              f"{ {f'${k:04x}': len(set(v)) for k, v in sorted(sld.items())} }")


def main():
    for bank, gaps in GAPS.items():
        print(f"== bank {bank} ==")
        for lo, hi in gaps:
            survey_gap(bank, lo, hi)
    # bank-0 tail
    print("== bank 0 tail $3947-$3fff ==")
    seg = rom[0x3947:0x4000]
    print(f"  len={len(seg)} ff={seg.count(0xFF)} zero={seg.count(0)} "
          f"distinct={len(set(seg))} ret(c9)={seg.count(0xC9)}")
    print(f"  head: {seg[:64].hex()}")
    reached, rst08, notes = walk(0, [0x3947])
    sp = spans(reached)
    print(f"  walk from $3947: {len(reached)} instrs, "
          f"spans {[(f'${a:04x}', f'${c:04x}') for a, c in sp][:8]}, "
          f"rst08={ {f'${k:04x}': len(v) for k, v in rst08.items()} }, "
          f"notes={notes[:3]}")
    cf = rom_cf_targets(0x3947, 0x4000)
    if cf:
        print(f"  ROM-wide abs-cf targets: "
              f"{ {f'${t:04x}': len(v) for t, v in sorted(cf.items())} }")
    scf, sld = src_cf_targets(0x3947, 0x4000)
    if scf:
        print(f"  carved-src cf targets: "
              f"{ {f'${k:04x}': sorted(set(v)) for k, v in sorted(scf.items())} }")
    if sld:
        print(f"  carved-src ld-pointer reads: "
              f"{ {f'${k:04x}': len(set(v)) for k, v in sorted(sld.items())} }")
    # what precedes $3947? last carved SGB bytes
    print(f"  $391b-$3947 head: {rom[0x391b:0x3947].hex()}")


if __name__ == "__main__":
    main()
