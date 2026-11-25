#!/usr/bin/env python3
"""Slice-24 survey: bank 28 ($1c) stream-record table + pool.

Reproduces the numbers in tools/generators/gen_slice24.py's header (bank 28
section). Run: python3 tools/surveys/survey24_bank28.py
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


def main():
    rom = open(ROM, "rb").read()
    b = bank_bytes(28)
    ln, lv = last_non_ff(b)
    print(f"bank 28 ($1c): $ff={b.count(0xff)}, $00={b.count(0)}, "
          f"last non-$ff ${ln:04x} (${lv:02x})")
    for base in range(0, 0x4000, 0x1000):
        ch = b[base:base + 0x1000]
        print(f"  ${0x4000 + base:04x}: ret(c9)={ch.count(0xc9)} "
              f"call(cd)={ch.count(0xcd)} jp(c3)={ch.count(0xc3)} "
              f"rst10(d7)={ch.count(0xd7)} rst08(cf)={ch.count(0xcf)} "
              f"jp(hl)(e9)={ch.count(0xe9)}")
    reached, rst08, notes = walk(28, [0x4000])
    print(f"  gb_rd walk from $4000: {len(reached)} instrs, "
          f"{len(rst08)} rst $08, notes={notes[:3]}")

    def rdw(a):
        return b[a - 0x4000] | (b[a - 0x4000 + 1] << 8)

    # $4000 dw table (bank-0 $1475: $4000 + C*2 -> stream base,
    # C = record byte0 & $7f). Extent by partition: entries while
    # the target is plausible (in-bank, >= the smallest target);
    # the first implausible entry ends the table.
    print("\n$4000 dw table (partition scan):")
    bad = []
    for i in range(128):
        t = rdw(0x4000 + 2 * i)
        if not (0x4000 <= t <= 0x7FFF):
            bad.append((i, t))
    print(f"  entries 0..127 with targets outside $4000-$7fff: "
          f"{[(i, hex(t)) for i, t in bad]}")
    tgts78 = [rdw(0x4000 + 2 * i) for i in range(78)]
    print(f"  entries 0..77: min target ${min(tgts78):04x}, "
          f"max ${max(tgts78):04x}, distinct {len(set(tgts78))}")
    print(f"  entry 78 @${0x409C:04x}: target ${rdw(0x409C):04x} "
          f"(implausible -- table is 78 entries, $4000-$409b)")
    print(f"  bytes $409c-$409d (pool head): "
          + " ".join(f"{x:02x}" for x in b[0x9C:0x9E]))
    print(f"  bytes $409e (min target): "
          + " ".join(f"{x:02x}" for x in b[0x9E:0xAE]))
    pool = b[0x9C:0x2C47]
    print(f"  pool $409c-$6c46: $f0 markers {pool.count(0xf0)}, "
          f"$f1 markers {pool.count(0xf1)}")
    print("  reader: bank-0 $143e StreamDispatchRecordD (via "
          "StreamIterateDual $13e7, which maps bank $1c) reads "
          "$4000+C*2 -> base, +B (record byte1*2), then walks "
          "2-byte values with $f0/$f1 high-byte markers; never "
          "jumps/calls into the pool. Second mapping: bank-0 "
          "$2470 B >= $af branch (stream data via $257f).")


if __name__ == "__main__":
    main()
