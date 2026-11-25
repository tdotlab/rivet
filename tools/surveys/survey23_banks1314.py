#!/usr/bin/env python3
"""Slice-23 survey: banks 13 ($0d) and 14 ($0e) -- level-data streams?

Reproduces the numbers in tools/generators/gen_slice23.py's header (bank 13/14
section). Run: python3 tools/surveys/survey23_banks1314.py
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"


def bank_bytes(bank):
    return open(ROM, "rb").read()[bank * 0x4000:(bank + 1) * 0x4000]


def survey_bank(bank):
    b = bank_bytes(bank)
    print(f"bank {bank}: $ff={b.count(0xff)}, $00={b.count(0)}")
    i = len(b) - 1
    while b[i] == 0xFF:
        i -= 1
    print(f"  last non-$ff window addr ${0x4000 + i:04x} (byte "
          f"${b[i]:02x}); tail all $ff: {set(b[i + 1:]) == {0xff}}")
    for base in range(0, 0x4000, 0x1000):
        ch = b[base:base + 0x1000]
        print(f"  ${0x4000 + base:04x}: ret(c9)={ch.count(0xc9)} "
              f"call(cd)={ch.count(0xcd)} jp(c3)={ch.count(0xc3)} "
              f"rst10(d7)={ch.count(0xd7)} rst08(cf)={ch.count(0xcf)} "
              f"jp(hl)(e9)={ch.count(0xe9)}")
    reached, rst08, notes = walk(bank, [0x4000])
    print(f"  gb_rd walk from $4000: {len(reached)} instrs, "
          f"{len(rst08)} rst $08, notes={notes[:3]}")


def main():
    rom = open(ROM, "rb").read()
    for bank, val in ((13, 0x0D), (14, 0x0E)):
        sites = []
        for off in range(len(rom) - 2):
            if rom[off] == 0x3E and rom[off + 1] == val and rom[off + 2] == 0xD7:
                bk = off // 0x4000
                addr = (off % 0x4000) + (0x4000 if bk > 0 else 0)
                sites.append((bk, addr))
        print(f"`ld a,${val:02x}; rst $10` sites: {sites}")
        survey_bank(bank)
    # Any `ld a,$xx` where xx is 13/14 used as a *variable* bank?
    # (bank-0 $2480 reads a bank byte from bank-14 data into [$c810]
    # and rst $10's it -- values come from data, not immediates.)
    # Count how often each byte value 0x0d/0x0e appears as an
    # `ld a,imm` in bank 0 (curated code region only, rough).
    print("done")


if __name__ == "__main__":
    main()
