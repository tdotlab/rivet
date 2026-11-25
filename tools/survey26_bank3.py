#!/usr/bin/env python3
"""Slice-26 survey: bank 3 ($03) gaps $43b0-$45a9, $4943-$76eb, $78b0-$7fff.

Questions:
  1. Is $4943-$76eb code or data? The slice-12 song table ($48f1, 41 dw
     entries) points into it -- check every entry, its reader, and
     whether the entries tile the region (song boundaries).
  2. What is $43b0-$45a9 (also a gap in bank 2)? Compare bank 2 vs 3.
  3. What is $78b0-$7990 (after the carved $76eb-$78af sound code)?
  4. Who maps bank 3, and which carved code targets into these gaps
     (call/jp/jr/table targets only -- never ld hl pointers)?
Run: python3 tools/survey26_bank3.py
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
    b3 = bank_bytes(3)
    b2 = bank_bytes(2)

    # --- 1. song table entries ($48f1-$4942, 41 dw) ---
    tbl = []
    for i in range(41):
        off = 0x48F1 - 0x4000 + 2 * i
        tbl.append(b3[off] | (b3[off + 1] << 8))
    print(f"song table entries (41): {[f'${t:04x}' for t in tbl]}")
    print(f"  unique sorted: {[f'${t:04x}' for t in sorted(set(tbl))]}")
    print(f"  min ${min(tbl):04x} max ${max(tbl):04x}; "
          f"entries < $4943: {[f'${t:04x}' for t in tbl if t < 0x4943]}")
    print(f"  entries == $4941: {tbl.count(0x4941)}; == $4ac3: {tbl.count(0x4AC3)}")

    # --- 2. bank 2 vs bank 3 $43b0-$45a9 ---
    g3 = b3[0x43B0 - 0x4000:0x45A9 - 0x4000]
    g2 = b2[0x43B0 - 0x4000:0x45A9 - 0x4000]
    print(f"$43b0-$45a9 bank2==bank3: {g2 == g3} "
          f"(differing bytes: {sum(1 for a, b in zip(g2, g3) if a != b)})")
    # as dw table: first 32 words
    words = [g3[2 * i] | (g3[2 * i + 1] << 8) for i in range(32)]
    print(f"  as dw (first 32): {[f'${w:04x}' for w in words]}")
    inc = all(words[i] < words[i + 1] for i in range(len(words) - 1))
    print(f"  strictly increasing: {inc}")
    print(f"  first bytes: {g3[:32].hex()}")

    # --- 3. $78b0-$7fff structure ---
    tail = b3[0x78B0 - 0x4000:]
    last_nz = max(i for i, x in enumerate(tail) if x != 0xFF)
    print(f"$78b0-$7fff last non-$ff at ${0x78B0 + last_nz:04x} "
          f"({last_nz + 1} bytes to there)")
    print(f"  bytes $78b0-$78d2: {tail[:0x22].hex()}")
    print(f"  bytes $78d2-$78e8: {tail[0x22:0x38].hex()}")
    print(f"  bytes $7942-$7990: {tail[0x92:0xE0].hex()}")

    # --- 4. gb_rd walks from gap starts + song entries ---
    for seeds in ([0x43B0], [0x4943], [0x454B], [0x4AC3], [0x78B0],
                  [0x4943, 0x454B, 0x4AC3, 0x4D0F, 0x5D3C, 0x7370, 0x764F]):
        reached, rst08, notes = walk(3, seeds)
        sp = spans(reached)
        print(f"  walk seeds {[f'${s:04x}' for s in seeds]}: "
              f"{len(reached)} instrs, spans "
              f"{[(f'${a:04x}', f'${b:04x}') for a, b in sp][:6]}, "
              f"rst08={len(rst08)}, notes={notes[:2]}")

    # --- 5. bank-3 select sites + control-flow targets into the gaps ---
    cf = re.compile(r"\b(?:call|jp|jr)\s+(?:[a-z]+\s*,\s*)?\$([0-9a-f]{4})\b")
    for fname in ("src/bank3.asm", "src/bank3slice12.asm"):
        txt = open(fname).read()
        hits = {}
        for m in cf.finditer(txt):
            a = int(m.group(1), 16)
            if 0x4943 <= a <= 0x76EA or 0x43B0 <= a <= 0x45A8 or 0x78B0 <= a <= 0x7990:
                hits.setdefault(a, 0)
                hits[a] += 1
        inner = ", ".join(f"${k:04x}: {v}" for k, v in sorted(hits.items()))
        print(f"  {fname} cf targets into gaps: {{{inner}}}")
    # bank-select sites for bank 3 across all src
    sel = re.compile(r"ld\s+a,\s*\$03\b")
    for fname in ("src/bank0slice3.asm", "src/main.asm", "src/states.asm",
                  "src/bank2.asm", "src/bank3.asm"):
        try:
            txt = open(fname).read()
        except FileNotFoundError:
            continue
        for m in sel.finditer(txt):
            ctx = txt[max(0, m.start() - 60):m.start() + 80].replace("\n", " | ")
            print(f"  bank-3 select in {fname}: ...{ctx.strip()[-120:]}")

    # --- 6. song data: first bytes at each unique entry ---
    print("  song heads (first 12 bytes at each unique entry):")
    for t in sorted(set(tbl)):
        off = t - 0x4000
        print(f"    ${t:04x}: {b3[off:off + 12].hex()}")


if __name__ == "__main__":
    main()
