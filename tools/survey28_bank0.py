#!/usr/bin/env python3
"""Slice-28 survey: bank-0 raw regions left in src/main.asm.

Regions (INCBIN in main.asm): $0674-$067f, $0df4-$0f08, $0f74-$0f94,
$0fa1-$0fc0, $1075-$10aa, $1e6b-$1e85, $3689-$3736. Known entry points
from carved callers (see survey output): $067b, $0df4, $0e29, $0e64,
$0ea9, $0ecd, $0f74, $1075, $1097, $1e6b. $0fa1/$0fae and $370f/$3723
look like data pointers, not code entries.

Run: python3 tools/survey28_bank0.py [region]
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, spans  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()
# TRUE GB ret opcodes only. (Earlier survey scripts also listed 0xE0/0xE8/
# 0xF0/0xF8, which are LDH/ADD-SP/LDH/LD-HL-SP, NOT rets -- that seeds
# garbage decodes overlapping real instructions, e.g. $0e6c here.)
RET_OPS = {0xC9, 0xC0, 0xC8, 0xD0, 0xD8}


def hexd(lo, hi):
    d = rom[lo:hi]
    for i in range(0, len(d), 16):
        print(f"${lo+i:04x}: {' '.join(f'{x:02x}' for x in d[i:i+16])}")


def post_ret(lo, hi):
    return [a + 1 for a in range(lo, hi - 1) if rom[a] in RET_OPS]


def dump(lo, hi, seeds, label):
    reached, rst08, notes = walk(0, list(seeds))
    print(f"== {label} ${lo:04x}-${hi:04x} seeds={[f'${s:04x}' for s in seeds]}: "
          f"{len(reached)} instrs ==")
    print(f"   spans {[(f'${a:04x}', f'${c:04x}') for a, c in spans(reached)]}")
    print(f"   rst08={list(rst08)} notes={notes[:6]}")
    for addr, (ln, text, kind, tgt) in sorted(reached.items()):
        print(f"    ${addr:04x}: {text}")
    return reached


REGIONS = {
    "0674": (0x0674, 0x067F, [0x067B]),
    "0df4": (0x0DF4, 0x0F08, [0x0DF4, 0x0E29, 0x0E64, 0x0EA9, 0x0ECD]),
    "0f74": (0x0F74, 0x0F94, [0x0F74]),
    "0fa1": (0x0FA1, 0x0FC0, [0x0FA1, 0x0FAE]),
    "1075": (0x1075, 0x10AA, [0x1075, 0x1097]),
    "1e6b": (0x1E6B, 0x1E85, [0x1E6B]),
    "3689": (0x3689, 0x3736, [0x3689, 0x370F, 0x3723]),
}


def main():
    names = sys.argv[1:] or list(REGIONS)
    for name in names:
        lo, hi, seeds = REGIONS[name]
        print(f"--- raw ${lo:04x}-${hi:04x} ---")
        hexd(lo, hi + 1)
        allseeds = post_ret(lo, hi) + seeds
        dump(lo, hi, allseeds, f"b0-{name}")


if __name__ == "__main__":
    main()
