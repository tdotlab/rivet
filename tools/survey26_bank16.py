#!/usr/bin/env python3
"""Slice-26 survey (part 3): bank 16 ($10) gaps $4000-$4031,
$4044-$4993, $4eb2-$51c8, $59f1-$5a11, $5fd3-$7fff.

Questions:
  1. Is $4000-$4031 a code stub (jp/call targets into $4044-$4993)?
     Walk it with gb_rd and list every call/jp/jr target.
  2. Is $4044-$4993 code (walk from $4044 + stub targets)? Any
     rst $08 sites? Where does it end (ret/jp tails)?
  3. What is $4eb2-$51c8 (790 B, small-value bytes -- tables?) and
     $59f1-$5a11 (32 B, ASCII-ish)?
  4. What is $5fd3-$7fff (last non-$ff? structure? walks?)?
  5. Who maps bank 16, and which carved code targets into these
     gaps (call/jp/jr/table targets only)?
Run: python3 tools/survey26_bank16.py
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
    b = bank_bytes(16)

    # --- 1+2. walks ---
    for seeds in ([0x4000], [0x4044], [0x4000, 0x4044]):
        reached, rst08, notes = walk(16, seeds)
        sp = spans(reached)
        print(f"  walk seeds {[f'${s:04x}' for s in seeds]}: "
              f"{len(reached)} instrs, spans "
              f"{[(f'${a:04x}', f'${b:04x}') for a, b in sp]}, "
              f"rst08={ {f'${k:04x}': len(v) for k, v in rst08.items()} }, "
              f"notes={notes[:3]}")
        tgts = sorted(set(v[3] for v in reached.values()
                          if v[3] is not None and v[3] != "indirect"
                          and isinstance(v[3], int)))
        print(f"    control targets: {[f'${t:04x}' for t in tgts]}")

    # --- 3. $4eb2-$51c8 + $59f1-$5a11 dumps ---
    print(f"  $4eb2-$4f00: {b[0x4EB2-0x4000:0x4F00-0x4000].hex()}")
    print(f"  $59f1-$5a11: {b[0x59F1-0x4000:0x5A11-0x4000].hex()}")
    print(f"  $59f1-$5a11 ascii: {bytes(b[0x59F1-0x4000:0x5A11-0x4000])!r}")
    for seeds in ([0x4EB2], [0x5000], [0x59F1]):
        reached, rst08, notes = walk(16, seeds)
        sp = spans(reached)
        print(f"  walk seeds {[f'${s:04x}' for s in seeds]}: "
              f"{len(reached)} instrs, spans "
              f"{[(f'${a:04x}', f'${b:04x}') for a, b in sp][:4]}, "
              f"notes={notes[:1]}")

    # --- 4. $5fd3-$7fff ---
    tail = b[0x5FD3 - 0x4000:]
    last_nz = max(i for i, x in enumerate(tail) if x != 0xFF)
    print(f"  $5fd3-$7fff last non-$ff at ${0x5FD3 + last_nz:04x}")
    print(f"  $5fd3 head 64: {tail[:64].hex()}")
    # zero runs / ff runs
    for val, name in ((0x00, "zero"), (0xFF, "ff")):
        runs = []
        i = 0
        while i < len(tail):
            if tail[i] == val:
                j = i
                while j < len(tail) and tail[j] == val:
                    j += 1
                if j - i >= 32:
                    runs.append((0x5FD3 + i, j - i))
                i = j
            else:
                i += 1
        print(f"  {name} runs >=32: {runs[:10]}")
    for seeds in ([0x5FD3], [0x6000], [0x7000], [0x7800]):
        reached, rst08, notes = walk(16, seeds)
        sp = spans(reached)
        print(f"  walk seeds {[f'${s:04x}' for s in seeds]}: "
              f"{len(reached)} instrs, spans "
              f"{[(f'${a:04x}', f'${b:04x}') for a, b in sp][:4]}, "
              f"rst08={len(rst08)}, notes={notes[:1]}")

    # --- 5. cf targets + bank-16 select sites ---
    cf = re.compile(r"\b(?:call|jp|jr)\s+(?:[a-z]+\s*,\s*)?\$([0-9a-f]{4})\b")
    gaps = [(0x4000, 0x4031), (0x4044, 0x4993), (0x4EB2, 0x51C8),
            (0x59F1, 0x5A11), (0x5FD3, 0x8000)]
    for fname in ("src/bank16slice11.asm", "src/bank16slice16.asm"):
        txt = open(fname).read()
        hits = {}
        for m in cf.finditer(txt):
            a = int(m.group(1), 16)
            if any(lo <= a < hi for lo, hi in gaps):
                hits.setdefault(a, 0)
                hits[a] += 1
        inner = ", ".join(f"${k:04x}: {v}" for k, v in sorted(hits.items()))
        print(f"  {fname} cf targets into gaps: {{{inner}}}")
    sel = re.compile(r"ld\s+a,\s*\$10\b")
    import glob
    for fname in sorted(glob.glob("src/*.asm")):
        txt = open(fname).read()
        for m in sel.finditer(txt):
            ctx = txt[max(0, m.start() - 40):m.start() + 100].replace("\n", " | ")
            print(f"  bank-16 select in {fname}: ...{ctx.strip()[-140:]}")


if __name__ == "__main__":
    main()
