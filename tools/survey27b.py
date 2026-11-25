#!/usr/bin/env python3
"""Slice-27 survey phase 2: filter cf noise to same-bank + bank-0 hits only,
dump walk text from gap starts and from same-bank entry seeds, and check
neighbor carved-span endings (fall-through vs ret/jp).
Run: python3 tools/survey27b.py
"""
import glob
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, spans, decode, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()
ABS_OPS = {0xC3, 0xCD, 0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA}

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

BANK_FILES = {
    7: ["src/bank7.asm", "src/bank7slice5.asm", "src/bank7slice10.asm",
        "src/bank7slice11.asm", "src/bank7slice12.asm",
        "src/bank7slice13.asm", "src/bank7slice14.asm"],
    8: ["src/bank8.asm", "src/bank8slice15.asm", "src/bank8slice16.asm"],
    11: ["src/bank11.asm", "src/bank11slice18.asm"],
    0: ["src/main.asm", "src/bank0slice3.asm", "src/bank0slice6.asm",
        "src/bank0slice7.asm", "src/bank0slice14.asm",
        "src/bank0slice17.asm", "src/bank0a.asm", "src/bank0aslice16.asm",
        "src/states.asm", "src/stat.asm", "src/transfer.asm",
        "src/decomp.asm", "src/frame.asm", "src/sgb.asm",
        "src/sgbpackets.asm"],
}


def rom_hits(bank, lo, hi):
    """Absolute-cf hits from the gap's own bank or bank 0 only."""
    out = {}
    for src_bank in (bank, 0):
        base = src_bank * 0x4000
        b = rom[base:base + 0x4000]
        for i in range(len(b) - 2):
            if b[i] in ABS_OPS:
                tgt = b[i + 1] | (b[i + 2] << 8)
                if lo <= tgt < hi:
                    addr = i if src_bank == 0 else 0x4000 + i
                    out.setdefault(tgt, []).append((src_bank, addr, b[i]))
    return out


def src_hits(bank, lo, hi):
    cf = re.compile(r"\b(?:call|jp|jr)\s+(?:[a-z]+\s*,\s*)?\$([0-9a-f]{4})\b")
    ld = re.compile(r"ld\s+(?:hl|de|bc),\s*\$([0-9a-f]{4})")
    out_cf, out_ld = {}, {}
    for fname in BANK_FILES.get(bank, []):
        try:
            txt = open(fname).read()
        except FileNotFoundError:
            continue
        for m in cf.finditer(txt):
            a = int(m.group(1), 16)
            if lo <= a < hi:
                out_cf.setdefault(a, []).append(fname.split("/")[-1])
        for m in ld.finditer(txt):
            a = int(m.group(1), 16)
            if lo <= a < hi:
                out_ld.setdefault(a, []).append(fname.split("/")[-1])
    return out_cf, out_ld


def dump_walk(bank, seeds, maxn=25):
    reached, rst08, notes = walk(bank, seeds)
    items = sorted(reached.items())
    print(f"    walk {['$%04x' % s for s in seeds]}: {len(reached)} instrs, "
          f"spans {[(f'${a:04x}', f'${c:04x}') for a, c in spans(reached)]}, "
          f"rst08={list(rst08)}, notes={notes[:3]}")
    for addr, (ln, text, kind, tgt) in items[:maxn]:
        print(f"      ${addr:04x}: {text}")
    return reached


def main():
    for bank, gaps in GAPS.items():
        print(f"===== bank {bank} =====")
        for lo, hi in gaps:
            print(f"--- ${lo:04x}-${hi:04x} ---")
            h = rom_hits(bank, lo, hi)
            if h:
                print("  same-bank/bank0 ROM cf hits:")
                for t, v in sorted(h.items()):
                    print(f"    ${t:04x}: " +
                          ", ".join(f"b{b} ${a:04x} op ${o:02x}"
                                    for b, a, o in v))
            scf, sld = src_hits(bank, lo, hi)
            if scf:
                print(f"  same-bank carved-src cf: "
                      f"{ {f'${k:04x}': sorted(set(v)) for k, v in sorted(scf.items())} }")
            if sld:
                print(f"  same-bank carved-src ld-ptr: "
                      f"{ {f'${k:04x}': sorted(set(v)) for k, v in sorted(sld.items())} }")
            dump_walk(bank, [lo], maxn=12)
            # extra seeds: same-bank cf targets inside the gap
            extra = sorted(t for t in h if t != lo)
            if extra:
                dump_walk(bank, extra, maxn=60)


if __name__ == "__main__":
    main()
