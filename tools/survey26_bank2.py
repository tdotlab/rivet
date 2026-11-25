#!/usr/bin/env python3
"""Slice-26 survey (part 2): bank 2 ($02) gaps $4000-$4003,
$4009-$4010, $43b0-$45a9, $48ea-$6212, $6492-$7fff.

Questions:
  1. Where do the 119 bank-2 $47fc sound-table entries point?
     (Reader: bank-2 tick $4694, `ld hl,$47fc` -- parallel to the
     bank-3 $48f1 song table.) Do they tile $48ea-$6212?
  2. Is $43b0-$45a9 identical to bank 3 (carved in slice 26 pt 1)?
  3. What is $6492-$7fff (last non-$ff? any structure?) and the two
     tiny entry-stub gaps?
  4. Any call/jp/jr targets into these gaps from carved bank-2 or
     bank-0 code (table targets only -- never ld hl pointers)?
Run: python3 tools/survey26_bank2.py
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
    b2 = bank_bytes(2)
    b3 = bank_bytes(3)

    # --- 1. sound table entries ($47fc, 119 dw) ---
    tbl = []
    for i in range(119):
        off = 0x47FC - 0x4000 + 2 * i
        tbl.append(b2[off] | (b2[off + 1] << 8))
    print(f"sound table entries (119): min ${min(tbl):04x} max ${max(tbl):04x}")
    print(f"  unique: {len(set(tbl))}; sorted unique: "
          f"{[f'${t:04x}' for t in sorted(set(tbl))]}")
    print(f"  entries < $48ea: {[f'${t:04x}' for t in tbl if t < 0x48EA]}")
    print(f"  entries >= $6212: {[f'${t:04x}' for t in tbl if t >= 0x6212]}")
    print(f"  entries in $6492-$7fff: {[f'${t:04x}' for t in tbl if t >= 0x6492]}")

    # --- 2. $43b0-$45a9 vs bank 3 ---
    g2 = b2[0x43B0 - 0x4000:0x45A9 - 0x4000]
    g3 = b3[0x43B0 - 0x4000:0x45A9 - 0x4000]
    print(f"$43b0-$45a9 bank2==bank3: {g2 == g3}")

    # --- 3. $6492-$7fff + tiny gaps ---
    tail = b2[0x6492 - 0x4000:]
    last_nz = max(i for i, x in enumerate(tail) if x != 0xFF)
    print(f"$6492-$7fff last non-$ff at ${0x6492 + last_nz:04x} "
          f"({last_nz + 1} bytes to there)")
    print(f"  $4000-$4003: {b2[0:3].hex()}  $4009-$4010: "
          f"{b2[0x4009 - 0x4000:0x4010 - 0x4000].hex()}")
    print(f"  $48ea head: {b2[0x48EA - 0x4000:0x48EA - 0x4000 + 24].hex()}")
    print(f"  $6492 head: {b2[0x6492 - 0x4000:0x6492 - 0x4000 + 24].hex()}")
    # ff runs in $6492-$7fff
    s = tail
    runs = []
    i = 0
    while i < len(s):
        if s[i] == 0xFF:
            j = i
            while j < len(s) and s[j] == 0xFF:
                j += 1
            if j - i >= 32:
                runs.append((0x6492 + i, j - i))
            i = j
        else:
            i += 1
    print(f"  $ff runs >=32 in $6492-$7fff: {runs}")

    # --- 4. gb_rd walks ---
    for seeds in ([0x48EA], [0x6492], [0x5000], [0x6000], [0x7000],
                  [tbl[0]], [0x43B0], [0x454B]):
        reached, rst08, notes = walk(2, seeds)
        sp = spans(reached)
        print(f"  walk seeds {[f'${s:04x}' for s in seeds]}: "
              f"{len(reached)} instrs, spans "
              f"{[(f'${a:04x}', f'${b:04x}') for a, b in sp][:6]}, "
              f"rst08={len(rst08)}, notes={notes[:1]}")

    # --- 5. cf targets into the gaps ---
    cf = re.compile(r"\b(?:call|jp|jr)\s+(?:[a-z]+\s*,\s*)?\$([0-9a-f]{4})\b")
    for fname in ("src/bank2.asm", "src/bank2slice12.asm"):
        txt = open(fname).read()
        hits = {}
        for m in cf.finditer(txt):
            a = int(m.group(1), 16)
            if (0x48EA <= a <= 0x6211 or 0x6492 <= a <= 0x7FFF
                    or 0x43B0 <= a <= 0x45A8):
                hits.setdefault(a, 0)
                hits[a] += 1
        inner = ", ".join(f"${k:04x}: {v}" for k, v in sorted(hits.items()))
        print(f"  {fname} cf targets into gaps: {{{inner}}}")

    # --- 6. SFX heads: first bytes at each unique entry in $48ea-$6212 ---
    print("  SFX heads (first 10 bytes) at unique entries in $48ea-$6212:")
    for t in sorted(set(x for x in tbl if 0x48EA <= x < 0x6212)):
        off = t - 0x4000
        print(f"    ${t:04x}: {b2[off:off + 10].hex()}")


if __name__ == "__main__":
    main()
