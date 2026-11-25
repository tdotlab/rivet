#!/usr/bin/env python3
"""Slice-28 survey: bank-16 $0fd9-inline-table pockets.

`call $0fd9` is NOT a call to the RST8 handler as a subroutine: $0fd9 pops
the return address (= the address just after the call), adds A*2, and jumps
to the dw stored there. So the bytes after `call $0fd9` are an inline dw
jump table (same family as rst $08 tables, but entered via call). The
table-entry routines `ret` to whatever the caller pushed (or to the call's
return address when nothing was pushed). $0fd9 itself has been carved in
src/main.asm since slice 1 -- the slice-27 task premise that it is raw is
wrong; the real work is decoding these inline tables.

Run: python3 tools/survey28_b16.py [part]
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, spans, decode  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()


def raw(bank, lo, hi):
    off = bank * 0x4000 + (lo - 0x4000)
    return rom[off:off + (hi - lo)]


def hexd(bank, lo, hi):
    d = raw(bank, lo, hi)
    for i in range(0, len(d), 16):
        print(f"${lo+i:04x}: {' '.join(f'{x:02x}' for x in d[i:i+16])}")


def table(bank, at, n):
    """Read n dw entries at `at`, print them, return list."""
    d = raw(bank, at, at + 2 * n)
    out = [d[2 * i] | (d[2 * i + 1] << 8) for i in range(n)]
    print(f"table @${at:04x}: {[f'${e:04x}' for e in out]}")
    return out


def dump(bank, seeds, label):
    reached, rst08, notes = walk(bank, seeds)
    print(f"== {label} bank {bank} seeds={[f'${s:04x}' for s in seeds]}: "
          f"{len(reached)} instrs ==")
    print(f"   spans {[(f'${a:04x}', f'${c:04x}') for a, c in spans(reached)]}")
    print(f"   rst08={list(rst08)} notes={notes[:6]}")
    return reached


def main():
    part = sys.argv[1] if len(sys.argv) > 1 else "all"
    if part in ("all", "raw"):
        print("=== bank16 $6b90-$6d52 raw ===")
        hexd(16, 0x6B90, 0x6D52)
        print("=== bank16 $6d91-$6e20 raw ===")
        hexd(16, 0x6D91, 0x6E20)
        print("=== bank16 $6cf0-$6d10 raw ===")
        hexd(16, 0x6CF0, 0x6D10)
        print("=== bank16 $6db0-$6e00 raw ===")
        hexd(16, 0x6DB0, 0x6E00)
    if part in ("all", "tables"):
        print("=== inline tables after call $0fd9 ===")
        table(16, 0x61B5, 6)
        table(16, 0x6B39, 6)
        table(16, 0x6B8C, 8)
        table(16, 0x6D67, 21)
    if part in ("all", "walks"):
        # $61b2 table entries
        dump(16, [0x61C1, 0x622B, 0x633C, 0x63D7, 0x63D8, 0x649D],
             "b16 61b2-table entries")
        # $6b32 table entries
        dump(16, [0x6B45, 0x6B57, 0x6B69, 0x6B6F, 0x6B70, 0x6B84],
             "b16 6b32-table entries")
        # $6b85 table entries, 2-entry reading
        dump(16, [0x6B9C, 0x6BAE], "b16 6b85-table entries (2)")
        # $6b85 table entries, 8-entry reading
        dump(16, [0x6B9C, 0x6BAE, 0x6CFC, 0x6D14, 0x6D2C, 0x6D3E,
                 0x6D50, 0x6D51], "b16 6b85-table entries (8)")
        # $6d52 dispatch table entries
        dump(16, [0x6DBF, 0x6DC5, 0x6DD1, 0x6DE4, 0x6DF1, 0x6DFE, 0x6E10,
                 0x6E34, 0x6E42, 0x6E50, 0x6E60, 0x6E70, 0x6E80, 0x6EA8,
                 0x6F06, 0x6F2E, 0x6F60, 0x6F7E, 0x6FD1, 0x6FDC, 0x6FE9],
             "b16 6d67-table entries")
        # heads
        dump(16, [0x617C, 0x61A0, 0x61A6, 0x61AC, 0x61B2, 0x6B32, 0x6B85,
                 0x6D52, 0x72E4], "b16 heads + 72e4")


if __name__ == "__main__":
    main()
