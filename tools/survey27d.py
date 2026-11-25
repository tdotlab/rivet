#!/usr/bin/env python3
"""Slice-27 survey phase 4: resolve ambiguous sub-regions.
  - raw byte dumps of contested spans
  - ld-pointer readers with context (which carved routine reads each gap base)
  - neighbor carved-span endings (fall-through?)
  - bank8 vs bank16 pocket comparison ($61b2/$617c/$6b32/$6b85)
  - walks from bank-16 $617c/$61b2/$6b32/$6b85 (bank-0 calls map bank 16!)
  - bank-7 $7e20/$7e22 alignment bytes, $67df walk, $7001 table dump
Run: python3 tools/survey27d.py
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, spans  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()


def dump(bank, lo, hi):
    b = rom[bank * 0x4000 + lo - 0x4000:bank * 0x4000 + hi - 0x4000]
    print(f"  bank {bank} ${lo:04x}-${hi:04x} ({hi-lo} B): {b.hex()}")


def readers(target, files):
    pat = re.compile(r"ld\s+(?:hl|de|bc),\s*\$%04x" % target)
    for fname in files:
        try:
            lines = open(fname).read().splitlines()
        except FileNotFoundError:
            continue
        for i, ln in enumerate(lines):
            if pat.search(ln):
                ctx = " | ".join(l.strip() for l in lines[max(0, i - 2):i + 1])
                print(f"  reader ${target:04x} in {fname.split('/')[-1]}: {ctx}")


def main():
    print("== bank7 $7e18 alignment ==")
    dump(7, 0x7E18, 0x7E30)
    print("== bank7 $67df-$68ab ==")
    dump(7, 0x67DF, 0x68AC)
    reached, _, notes = walk(7, [0x67DF])
    print(f"  walk $67df: {len(reached)} instrs spans "
          f"{[(f'${a:04x}', f'${c:04x}') for a, c in spans(reached)]} notes={notes[:2]}")
    for a, (ln, t, k, tg) in sorted(reached.items())[:40]:
        print(f"    ${a:04x}: {t}")
    print("== bank7 $6646-$664c + $6581 reader ==")
    dump(7, 0x6646, 0x664D)
    readers(0x6581, ["src/bank7slice5.asm", "src/bank7.asm"])
    readers(0x7001, ["src/bank7slice5.asm", "src/bank7.asm",
                      "src/bank7slice10.asm", "src/bank7slice13.asm"])
    print("== bank7 $7001 table bytes ==")
    dump(7, 0x7001, 0x7030)
    print("== bank7 $76c5-$771d ==")
    dump(7, 0x76C5, 0x771E)
    print("== bank7 $767b-$7689 ==")
    dump(7, 0x767B, 0x768A)
    print("== bank7 $6b70-$6b80 n/a; bank8 $6b70-$6b80 ==")
    dump(8, 0x6B70, 0x6B80)
    print("== bank8 vs bank16 pockets ==")
    for lo, hi in ((0x61B2, 0x61DC), (0x617C, 0x61F0), (0x6B32, 0x6B7C),
                   (0x6B85, 0x6BA1)):
        a = rom[8 * 0x4000 + lo - 0x4000:8 * 0x4000 + hi - 0x4000]
        b = rom[16 * 0x4000 + lo - 0x4000:16 * 0x4000 + hi - 0x4000]
        d = sum(1 for p, q in zip(a, b) if p != q)
        print(f"  bank8 vs bank16 ${lo:04x}-${hi:04x}: {d}/{hi-lo} differ")
    print("== bank16 walks from $617c/$61b2/$6b32/$6b85 ==")
    for seeds in ([0x617C], [0x61B2], [0x6B32], [0x6B85],
                  [0x617C, 0x61B2, 0x6B32, 0x6B85]):
        reached, rst08, notes = walk(16, seeds)
        print(f"  walk {['$%04x' % s for s in seeds]}: {len(reached)} instrs "
              f"spans {[(f'${a:04x}', f'${c:04x}') for a, c in spans(reached)]} "
              f"rst08={list(rst08)} notes={notes[:2]}")
    print("== bank8 $611f-$61dc bytes ==")
    dump(8, 0x611F, 0x61DC)
    print("== bank8 $5bec-$5c50 + $5c9e-$5cea bytes (heads) ==")
    dump(8, 0x5BEC, 0x5C10)
    dump(8, 0x5C9E, 0x5CC0)
    print("== bank8 $671a-$67bb bytes (head) ==")
    dump(8, 0x671A, 0x6740)
    print("== bank8 $67cc-$68b7 bytes (head) ==")
    dump(8, 0x67CC, 0x67F0)
    print("== bank8 $691f-$69ab bytes (head) ==")
    dump(8, 0x691F, 0x6940)
    print("== bank8 $6a02-$6a24 + $6a34-$6a8a bytes ==")
    dump(8, 0x6A02, 0x6A24)
    dump(8, 0x6A34, 0x6A60)
    print("== bank8 $6cc5-$6d89 bytes (head) ==")
    dump(8, 0x6CC5, 0x6CF0)
    print("== bank8 $6283-$62cd bytes ==")
    dump(8, 0x6283, 0x62CD)
    print("== bank7 $7f0d-$7f8f bytes ==")
    dump(7, 0x7F0D, 0x7F90)
    print("== ld-ptr readers (bank8 gaps) ==")
    for t in (0x611F, 0x6283, 0x6ACA, 0x67CC, 0x69BE, 0x6A34, 0x5809):
        readers(t, ["src/bank8slice15.asm", "src/bank8slice16.asm",
                    "src/bank8.asm"])
    print("== ld-ptr readers (bank7 gaps) ==")
    for t in (0x68C4, 0x71BA, 0x7610, 0x7B14, 0x7BDA, 0x7C3D, 0x7CA0):
        readers(t, ["src/bank7slice5.asm", "src/bank7.asm",
                    "src/bank7slice10.asm", "src/bank7slice11.asm",
                    "src/bank7slice12.asm", "src/bank7slice13.asm",
                    "src/bank7slice14.asm"])


if __name__ == "__main__":
    main()
