#!/usr/bin/env python3
"""Slice-25 survey: bank 1 ($01) code continuation $5a00-$5a80.

Reproduces the numbers in tools/generators/gen_slice25.py's header (bank 1).
The carved bank-1 code ends at $59ff; its last routine ($59c4 loop)
falls through at $59fd into $5a00, and calls $5a45/$5a76 from
$59d6/$59dd -- the only two control-flow targets into $5a00-$79ff
anywhere in src/banks/bank1.asm. Run: python3 tools/surveys/survey25_bank1.py
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"


def main():
    txt = open("src/banks/bank1.asm").read()
    cf = re.compile(r"\b(?:call|jp|jr)\s+(?:[a-z]+\s*,\s*)?\$([0-9a-f]{4})\b")
    hits = {}
    for m in cf.finditer(txt):
        a = int(m.group(1), 16)
        if 0x5A00 <= a <= 0x79FF:
            hits.setdefault(a, 0)
            hits[a] += 1
    print(f"bank1.asm control-flow targets into $5a00-$79ff: "
          f"{ {f'${k:04x}': v for k, v in sorted(hits.items())} }")
    for seeds in ([0x5A00], [0x5A45], [0x5A76], [0x5A00, 0x5A45, 0x5A76]):
        reached, rst08, notes = walk(1, seeds)
        addrs = sorted(reached)
        covered = set()
        for a, (ln, _t, _k, _tg) in reached.items():
            covered.update(range(a, a + ln))
        print(f"  walk seeds {[f'${s:04x}' for s in seeds]}: "
              f"{len(reached)} instrs, ${addrs[0]:04x}-${addrs[-1]:04x}, "
              f"bytes ${min(covered):04x}-${max(covered):04x} "
              f"({len(covered)} bytes), rst08={len(rst08)}")
    # $5a81+: no walk reaches it; $5d48+ are ld-hl data pointers.
    ld = re.compile(r"ld\s+(?:hl|de|bc),\s*\$([0-9a-f]{4})")
    ptrs = sorted(set(int(m.group(1), 16) for m in ld.finditer(txt)
                      if 0x5A81 <= int(m.group(1), 16) <= 0x79FF))
    print(f"  ld-pointer targets into $5a81-$79ff (data reads): "
          f"{[f'${p:04x}' for p in ptrs]}")


if __name__ == "__main__":
    main()
