#!/usr/bin/env python3
"""Slice-29 survey (d): render the live 1-1 WRAM map as text.
Each cell prints pair0 (type,subtype) as 2 hex bytes, rows 0-19,
cols 0-21 (the visible playfield). Type $0b cells are marked with *.

Usage: python3 tools/surveys/survey29d_render.py <wram.bin>
"""
import sys

BASE = 0xC86D - 0xC000


def main():
    wram = open(sys.argv[1], "rb").read()
    assert len(wram) == 8192
    print("    " + "".join(f"{c:5d}" for c in range(22)))
    for row in range(20):
        line = f"{row:3d} "
        for col in range(22):
            off = BASE + row * 128 + col * 4
            b0, b1, b2, b3 = wram[off:off + 4]
            mark = "*" if b0 == 0x0B or b2 == 0x0B else " "
            line += f"{b0:02x}{b1:02x}{mark} "
        print(line)
    print("(* = a $0b cell in this position; pair0 shown, pair1 after /)")


if __name__ == "__main__":
    main()
