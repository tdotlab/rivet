#!/usr/bin/env python3
"""Slice 27 survey g: re-walk bank 7 $7abb-$7d5d and $7e18-$7edc with the
$6e54-verified seeds (handlers jp $6e54 with HL=blob; $6e54 ends jp hl,
so the blobs ARE executed as code), plus bank 7 $768a-$77a8.

$6e54 targets (from bank7slice10 handlers):
  $7b14 (B=$10), $7bda (B=$18), $7c3d (B=$26), $7ca0 (B=$2a),
  $7689 (B=$2e, 1-byte ret), $7d96 (B=$22), $7dbe (B=$4a),
  $7e43 (B=$3e), $7e55 (B=$42), $7e67 (B=$46), $7e79 (B=$3a).
Heads (routine starts whose mid-point is the $6e54 target):
  $7abb (head of $7b14), $7e3f (head of $7e43).
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, spans  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()
RET_OPS = {0xC9, 0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8}


def post_ret(bank, lo, hi):
    b = rom[bank * 0x4000:(bank + 1) * 0x4000]
    return [a + 1 for a in range(lo, hi - 1) if b[a - 0x4000] in RET_OPS]


def run(bank, lo, hi, seeds, tag):
    # post-ret seeds FIRST (processed last), verified seeds LAST (first).
    allseeds = post_ret(bank, lo, hi) + seeds
    reached, rst08, notes = walk(bank, allseeds)
    sp = spans(reached)
    cov = {x for a, c in sp for x in range(a, c + 1)}
    uncov, cur = [], None
    for x in range(lo, hi + 1):
        if x not in cov:
            cur = [x, x] if cur is None else [cur[0], x]
        elif cur:
            uncov.append(tuple(cur)); cur = None
    if cur:
        uncov.append(tuple(cur))
    print(f"== {tag} bank {bank} ${lo:04x}-${hi:04x} seeds={[f'${s:04x}' for s in seeds]}: "
          f"{len(reached)} instrs ==")
    print(f"   spans {[(f'${a:04x}', f'${c:04x}') for a, c in sp]}")
    print(f"   rst08={list(rst08)} notes={notes[:4]}")
    print(f"   uncovered {[(f'${a:04x}', f'${b:04x}') for a, b in uncov]}")
    for addr, (ln, text, kind, tgt) in sorted(reached.items()):
        print(f"    ${addr:04x}: {text}")
    print()


if __name__ == "__main__":
    which = sys.argv[1]
    if which == "b7-7abb":
        run(7, 0x7ABB, 0x7D5D, [0x7ABB, 0x7B14, 0x7BDA, 0x7C3D, 0x7CA0], "b7-7abb")
    elif which == "b7-7e18":
        run(7, 0x7E18, 0x7EDC, [0x7E18, 0x7E3F, 0x7E43, 0x7E55, 0x7E67, 0x7E79, 0x7ECB], "b7-7e18")
    elif which == "b7-768a":
        run(7, 0x768A, 0x77A8, [0x768A, 0x76C5, 0x771E], "b7-768a")
