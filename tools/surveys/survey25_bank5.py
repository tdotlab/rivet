#!/usr/bin/env python3
"""Slice-25 survey: bank 5 ($05) run-0 stage data, bank 18 ($12) run-2
stage data, bank 24 ($18) stream region, bank 23 ($17) low region, and
extent/opcode scans of the other remaining gaps.

Reproduces the numbers in tools/generators/gen_slice25.py's header.
Run: python3 tools/surveys/survey25_bank5.py
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()

# Bank-5 stage table (src/banks/bank5.asm, slice 4): 106 dw entries.
# Run 0 (indices 0-44) -> bank 5; run 1 (45-79) -> bank 6 (slice 24);
# run 2 (80-105) -> bank 18.
STAGE5 = [0x4200, 0x42c8, 0x43a1, 0x4453, 0x44d2, 0x45c1, 0x4726, 0x4809,
          0x491b, 0x49f0, 0x4abd, 0x4bb9, 0x4c76, 0x4e1d, 0x4f61, 0x5076,
          0x515d, 0x52bc, 0x5447, 0x5630, 0x5753, 0x583d, 0x59be, 0x5b46,
          0x5c14, 0x5da4, 0x5f3b, 0x60a1, 0x624b, 0x63c7, 0x64ad, 0x6613,
          0x6773, 0x6919, 0x6a4a, 0x6bda, 0x6d29, 0x6eab, 0x70a6, 0x72b0,
          0x73ab, 0x75ad, 0x782d, 0x7a56, 0x7b64]
STAGE18 = [0x4000, 0x4188, 0x43a1, 0x4575, 0x4694, 0x4862, 0x49b7, 0x4b18,
           0x4c83, 0x4e21, 0x508f, 0x5294, 0x53b6, 0x5506, 0x566f, 0x585a,
           0x598a, 0x5aca, 0x5c5a, 0x5d84, 0x5e32, 0x5ed6, 0x5f7d, 0x602c,
           0x60df, 0x61b2]


def bank_bytes(bank):
    return rom[bank * 0x4000:(bank + 1) * 0x4000]


def last_non_ff(b):
    i = len(b) - 1
    while b[i] == 0xFF:
        i -= 1
    return 0x4000 + i, b[i]


def ld_sites(val):
    """`ld a,$xx; rst $10` sites in the whole ROM, as (bank, addr)."""
    sites = []
    for off in range(len(rom) - 2):
        if rom[off] == 0x3E and rom[off + 1] == val and rom[off + 2] == 0xD7:
            bk = off // 0x4000
            addr = (off % 0x4000) + (0x4000 if bk > 0 else 0)
            sites.append((bk, addr))
    return sites


def survey_bank(bank):
    b = bank_bytes(bank)
    ln, lv = last_non_ff(b)
    print(f"bank {bank}: $ff={b.count(0xff)}, $00={b.count(0)}, "
          f"last non-$ff ${ln:04x} (${lv:02x})")
    for base in range(0, 0x4000, 0x1000):
        ch = b[base:base + 0x1000]
        print(f"  ${0x4000 + base:04x}: ret(c9)={ch.count(0xc9)} "
              f"call(cd)={ch.count(0xcd)} jp(c3)={ch.count(0xc3)} "
              f"rst10(d7)={ch.count(0xd7)} rst08(cf)={ch.count(0xcf)} "
              f"jp(hl)(e9)={ch.count(0xe9)}")
    reached, rst08, notes = walk(bank, [0x4000])
    print(f"  gb_rd walk from $4000: {len(reached)} instrs, "
          f"{len(rst08)} rst $08, notes={notes[:3]}")


def stage_report(bank, stages, first_stage_no):
    b = bank_bytes(bank)
    ln, _ = last_non_ff(b)
    print(f"bank {bank} stages {first_stage_no}-{first_stage_no + len(stages) - 1}:")
    for i, s in enumerate(stages):
        hdr = " ".join(f"{b[s - 0x4000 + k]:02x}" for k in range(5))
        nxt = stages[i + 1] if i + 1 < len(stages) else None
        sz = (nxt - s) if nxt else (ln - s + 1)
        print(f"  stage {first_stage_no + i} ${s:04x} size {sz} hdr: {hdr}")
    print(f"  strictly increasing: "
          f"{all(stages[i + 1] > stages[i] for i in range(len(stages) - 1))}")
    print(f"  last stage ${stages[-1]:04x} -> last non-$ff ${ln:04x}: "
          f"{ln - stages[-1] + 1} bytes")
    for k in range(5):
        print(f"  hdr byte{k} values: "
              f"{sorted(set(b[s - 0x4000 + k] for s in stages))}")
    ptrs = 0
    for a in range(0x4000, 0x7fff):
        w = b[a - 0x4000] | (b[a - 0x4000 + 1] << 8)
        if 0x4000 <= w <= 0x7fff:
            ptrs += 1
    print(f"  dw values pointing in-bank (any alignment): {ptrs} / 16383")


def main():
    print(f"`ld a,$05; rst $10` sites: {ld_sites(0x05)}")
    print(f"`ld a,$12; rst $10` sites: {ld_sites(0x12)}")
    print(f"`ld a,$18; rst $10` sites: {ld_sites(0x18)}")
    print(f"`ld a,$17; rst $10` sites: {ld_sites(0x17)}")
    # Bank 5: verify the table entries in src/banks/bank5.asm match the ROM.
    b5 = bank_bytes(5)
    tbl = [b5[2 * i] | (b5[2 * i + 1] << 8) for i in range(106)]
    assert tbl[:45] == STAGE5, "run-0 table mismatch"
    assert tbl[80:] == STAGE18, "run-2 table mismatch"
    print("bank-5 table entries 0-44 and 80-105 match src/banks/bank5.asm")
    print(f"bank 5 gap $40d4-$41ff ({0x4200 - 0x40d4} bytes): "
          + " ".join(f"{x:02x}" for x in b5[0x0d4:0x200]))
    survey_bank(5)
    stage_report(5, STAGE5, 0)
    print()
    survey_bank(18)
    stage_report(18, STAGE18, 80)
    print()
    print("bank 24 / 23 / 12 / 1 / 2 / 3 / 16 gap scans:")
    for bank in (24, 23, 12, 1, 2, 3, 16):
        survey_bank(bank)


if __name__ == "__main__":
    main()
