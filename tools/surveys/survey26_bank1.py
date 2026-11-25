#!/usr/bin/env python3
"""Slice-26 survey (part 4): bank 1 ($01) gap $5a81-$7fff (9,599 B).

Slice 25 §6: tables at $5d48+ are ld-pointer reads -- survey the
$5a81-$5d47 span first, then the tables.
Questions:
  1. Is $5a81-$5d47 code (walk from $5a81 -- fall-through from the
     $59c4 loop via $5a00-$5a80?) or data?
  2. What are the $5d48+ tables (ld-pointer reads -- list every
     reader in carved bank-1 code)?
  3. What is $5d48-$7fff (last non-$ff? walks? structure?)?
  4. Any call/jp/jr targets into $5a81-$7fff from carved code
     (table targets only -- never ld hl pointers)?
Run: python3 tools/surveys/survey26_bank1.py
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, spans  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"


def bank_bytes(n):
    rom = open(ROM, "rb").read()
    return rom[n * 0x4000:(n + 1) * 0x4000]


def main():
    b = bank_bytes(1)

    # --- 1+3. walks ---
    for seeds in ([0x5A81], [0x5D48], [0x6000], [0x7000], [0x7800], [0x5A81, 0x5D48]):
        reached, rst08, notes = walk(1, seeds)
        sp = spans(reached)
        print(f"  walk seeds {[f'${s:04x}' for s in seeds]}: "
              f"{len(reached)} instrs, spans "
              f"{[(f'${a:04x}', f'${b:04x}') for a, b in sp][:6]}, "
              f"rst08={ {f'${k:04x}': len(v) for k, v in rst08.items()} }, "
              f"notes={notes[:2]}")

    # --- structure ---
    tail = b[0x5A81 - 0x4000:]
    last_nz = max(i for i, x in enumerate(tail) if x != 0xFF)
    print(f"  $5a81-$7fff last non-$ff at ${0x5A81 + last_nz:04x}")
    print(f"  $5a81 head: {tail[:48].hex()}")
    print(f"  $5d48 head: {b[0x5D48-0x4000:0x5D48-0x4000+48].hex()}")
    for val, name in ((0x00, "zero"), (0xFF, "ff")):
        runs = []
        i = 0
        while i < len(tail):
            if tail[i] == val:
                j = i
                while j < len(tail) and tail[j] == val:
                    j += 1
                if j - i >= 32:
                    runs.append((0x5A81 + i, j - i))
                i = j
            else:
                i += 1
        print(f"  {name} runs >=32: {runs[:8]}")

    # --- 2+4. cf targets + ld-pointer reads ---
    cf = re.compile(r"\b(?:call|jp|jr)\s+(?:[a-z]+\s*,\s*)?\$([0-9a-f]{4})\b")
    ld = re.compile(r"ld\s+(?:hl|de|bc),\s*\$([0-9a-f]{4})")
    for fname in ("src/banks/bank1.asm", "src/banks/bank1slice25.asm"):
        txt = open(fname).read()
        hits = {}
        for m in cf.finditer(txt):
            a = int(m.group(1), 16)
            if 0x5A81 <= a <= 0x7FFF:
                hits.setdefault(a, 0)
                hits[a] += 1
        inner = ", ".join(f"${k:04x}: {v}" for k, v in sorted(hits.items()))
        print(f"  {fname} cf targets into $5a81-$7fff: {{{inner}}}")
        ptrs = {}
        for m in ld.finditer(txt):
            a = int(m.group(1), 16)
            if 0x5A81 <= a <= 0x7FFF:
                ptrs.setdefault(a, 0)
                ptrs[a] += 1
        inner = ", ".join(f"${k:04x}: {v}" for k, v in sorted(ptrs.items()))
        print(f"  {fname} ld-pointer reads into $5a81-$7fff: {{{inner}}}")


if __name__ == "__main__":
    main()
