#!/usr/bin/env python3
"""Slice-24 survey: bank 17 ($11) and entry sites for the remaining banks.

Reproduces the numbers in tools/generators/gen_slice24.py's header (bank 17
section). Run: python3 tools/surveys/survey24_bank17.py
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"


def bank_bytes(bank):
    return open(ROM, "rb").read()[bank * 0x4000:(bank + 1) * 0x4000]


def last_non_ff(b):
    i = len(b) - 1
    while b[i] == 0xFF:
        i -= 1
    return 0x4000 + i, b[i]


def ld_sites(rom, val):
    """All `ld a,$val; rst $10` sites as (rom-bank, addr)."""
    sites = []
    for off in range(len(rom) - 2):
        if rom[off] == 0x3E and rom[off + 1] == val and rom[off + 2] == 0xD7:
            bk = off // 0x4000
            addr = (off % 0x4000) + (0x4000 if bk > 0 else 0)
            sites.append((bk, addr))
    return sites


def main():
    rom = open(ROM, "rb").read()
    print("`ld a,$xx; rst $10` sites for the remaining banks:")
    for bank in (17, 19, 20, 21, 22, 25, 26, 27, 28, 30):
        print(f"  bank {bank} (${bank:02x}): {ld_sites(rom, bank)}")

    b = bank_bytes(17)
    ln, lv = last_non_ff(b)
    print(f"\nbank 17: $ff={b.count(0xff)}, $00={b.count(0)}, "
          f"last non-$ff ${ln:04x} (${lv:02x})")
    print("  first 64 bytes: " +
          " ".join(f"{x:02x}" for x in b[:64]))
    for base in range(0, 0x4000, 0x1000):
        ch = b[base:base + 0x1000]
        print(f"  ${0x4000 + base:04x}: ret(c9)={ch.count(0xc9)} "
              f"call(cd)={ch.count(0xcd)} jp(c3)={ch.count(0xc3)} "
              f"rst10(d7)={ch.count(0xd7)} rst08(cf)={ch.count(0xcf)} "
              f"jp(hl)(e9)={ch.count(0xe9)}")
    reached, rst08, notes = walk(17, [0x4000])
    print(f"  gb_rd walk from $4000: {len(reached)} instrs, "
          f"{len(rst08)} rst $08, notes={notes[:5]}")
    # Any 16-byte repeating structure / zero runs in the data region?
    # Longest run of $00 and of $ff inside $4000-$69ef.
    def longest_run(data, val):
        best = cur = 0
        for x in data:
            cur = cur + 1 if x == val else 0
            best = max(best, cur)
        return best
    print(f"  longest $00 run in $4000-$69ef: "
          f"{longest_run(b[:0x29f0], 0)}")
    print(f"  longest $ff run in $4000-$69ef: "
          f"{longest_run(b[:0x29f0], 0xff)}")
    # dw values pointing in-bank (pointer-table test, cf. bank 6).
    ptrs = 0
    for a in range(0x4000, 0x69f0):
        w = b[a - 0x4000] | (b[a - 0x4000 + 1] << 8)
        if 0x4000 <= w <= 0x7fff:
            ptrs += 1
    print(f"  dw values pointing in-bank: {ptrs} / {0x69f0 - 0x4000}")
    # Does bank 17 share its opening with any other bank (cf. banks 13/14)?
    for other in (13, 14, 19, 20, 21, 22, 25, 26, 27, 28, 30):
        ob = bank_bytes(other)
        same = sum(1 for i in range(16) if b[i] == ob[i])
        print(f"  first-16-bytes match with bank {other}: {same}/16")

    # --- structure: $4000 dw table, $4010 4-byte records -------------
    def rdw17(a):
        return b[a - 0x4000] | (b[a - 0x4000 + 1] << 8)

    print("\n$4000 dw table (bank-0 $3202 reads $4000+B*2, B=queue B):")
    for i in range(8):
        print(f"  entry {i} @${0x4000 + 2 * i:04x}: ${rdw17(0x4000 + 2 * i):04x}")
    print(f"  entry 8 would read ${rdw17(0x4010):04x} (invalid pointer "
          f"-- partition test, table is 8 entries)")
    print("$4010 4-byte records [flag][00][dw ptr], k=0..24:")
    for k in range(25):
        a = 0x4010 + 4 * k
        fl, b1, dw = b[a - 0x4000], b[a - 0x4000 + 1], rdw17(a + 2)
        ok = fl in (0, 1) and b1 == 0 and 0x4070 <= dw <= 0x69EF
        print(f"  k={k:2d} ${a:04x}: flag={fl:02x} b1={b1:02x} "
              f"dw=${dw:04x} plausible={ok}")
    print("  record dw set: "
          f"{sorted(set(rdw17(0x4010 + 4 * k + 2) for k in range(24)))}")
    print("  flags k=0..23: "
          f"{[b[0x4010 + 4 * k - 0x4000] for k in range(24)]}")
    # Queue B values (bank-12 $4f97, 331 (C,B) pairs, slice 4).
    q = bank_bytes(12)
    pairs = [(q[0xF97 + 2 * i - 0x4000], q[0xF97 + 2 * i + 1 - 0x4000])
             for i in range(331)]
    print("\nbank-12 queue: B values for C==3 (the $3202 gate): "
          f"{sorted(set(bb for cc, bb in pairs if cc == 3))}")
    # $4050-group reader entry: `ld de,$4050` at bank 0 $32fc.
    hits = []
    pat = bytes([0x11, 0x50, 0x40])
    i = rom.find(pat)
    while i != -1:
        hits.append(hex(i))
        i = rom.find(pat, i + 1)
    print(f"`ld de,$4050` sites (file offsets): {hits} "
          f"(bank 0 $32fc = the $4050-group entry)")


if __name__ == "__main__":
    main()
