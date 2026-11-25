#!/usr/bin/env python3
"""Slice-22 survey: is bank 4 code, data, or graphics?

Reproduces the numbers in tools/generators/gen_slice22.py's header from the ROM
bytes. Run: python3 tools/surveys/survey22_bank4.py
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"


def main():
    rom = open(ROM, "rb").read()
    b4 = rom[0x10000:0x14000]
    print(f"bank 4: {len(b4)} bytes, $ff={b4.count(0xff)}, "
          f"$00={b4.count(0)}")
    i = len(b4) - 1
    while b4[i] == 0xFF:
        i -= 1
    print(f"last non-$ff window addr ${0x4000 + i:04x} "
          f"(byte ${b4[i]:02x}); $76b0-$7fff all $ff: "
          f"{set(b4[0x36b0:]) == {0xff}}")
    print(f"carve span $4000-$76af = {0x36b0} bytes = "
          f"{0x36b0 // 16} tiles of 16 bytes")
    print(f"$5f30 tile #: {(0x5f30 - 0x4000) // 16}, "
          f"$67b0 tile #: {(0x67b0 - 0x4000) // 16}")
    for base in range(0, 0x4000, 0x1000):
        ch = b4[base:base + 0x1000]
        print(f"  ${0x4000 + base:04x}: ret(c9)={ch.count(0xc9)} "
              f"call(cd)={ch.count(0xcd)} jp(c3)={ch.count(0xc3)} "
              f"rst10(d7)={ch.count(0xd7)} rst08(cf)={ch.count(0xcf)} "
              f"jp(hl)(e9)={ch.count(0xe9)}")
    sites = []
    for off in range(len(rom) - 2):
        if rom[off] == 0x3E and rom[off + 1] == 0x04 and rom[off + 2] == 0xD7:
            bank = off // 0x4000
            addr = (off % 0x4000) + (0x4000 if bank > 0 else 0)
            sites.append((bank, addr))
    print(f"`ld a,$04; rst $10` sites in whole ROM: {sites}")
    for seed in (0x4000, 0x5F30, 0x67B0):
        reached, rst08, notes = walk(4, [seed])
        print(f"gb_rd walk from ${seed:04x}: {len(reached)} instrs, "
              f"{len(rst08)} rst $08 sites, notes={notes[:3]}")
    # Render tiles 0-2 as ASCII (2bpp: low plane then high plane).
    for t in range(3):
        off = 0x10000 + 16 * t
        d = rom[off:off + 16]
        print(f"tile {t} @ ${0x4000 + 16 * t:04x}:")
        for r in range(8):
            lo, hi = d[2 * r], d[2 * r + 1]
            print("   " + "".join(
                "#" if (hi >> (7 - c)) & 1 else
                ("+" if (lo >> (7 - c)) & 1 else ".")
                for c in range(8)))


if __name__ == "__main__":
    main()
