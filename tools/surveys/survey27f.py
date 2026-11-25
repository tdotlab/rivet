#!/usr/bin/env python3
"""Slice-27 survey phase 6: full walk dumps with priority-ordered seeds
(verified entries LAST in the list = processed FIRST by gb_rd's LIFO stack;
post-ret filler seeds first = processed last, only filling unreached bytes).
Run: python3 tools/surveys/survey27f.py <name>
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, spans  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()
RET_OPS = {0xC9, 0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8}


def post_ret(bank, lo, hi):
    b = rom[bank * 0x4000:(bank + 1) * 0x4000]
    return [a + 1 for a in range(lo, hi - 1)
            if b[a - 0x4000] in RET_OPS]


def dump(bank, seeds, label):
    reached, rst08, notes = walk(bank, seeds)
    print(f"== {label} bank {bank} seeds={[f'${s:04x}' for s in seeds]}: "
          f"{len(reached)} instrs ==")
    print(f"   spans {[(f'${a:04x}', f'${c:04x}') for a, c in spans(reached)]}")
    print(f"   rst08={list(rst08)} notes={notes[:4]}")
    for addr, (ln, text, kind, tgt) in sorted(reached.items()):
        print(f"    ${addr:04x}: {text}")
    return reached


def main():
    name = sys.argv[1]
    if name == "b8-5905":
        dump(8, [0x5905, 0x5962, 0x59CB, 0x5A32, 0x5A5E, 0x5AB4,
                 0x5C51, 0x5D07], "b8-5905 verified only")
    elif name == "b8-5905x":
        # uncovered pockets: walk from their starts to see if code
        dump(8, [0x5BEC, 0x5C9E, 0x5D59], "b8-5905 uncovered pockets")
    elif name == "b7-6581":
        seeds = post_ret(7, 0x6581, 0x664D) + [0x662A]
        dump(7, seeds, "b7-6581 postret+662a")
    elif name == "b8-611f":
        seeds = post_ret(8, 0x611F, 0x6274) + [0x61DC]
        dump(8, seeds, "b8-611f postret+61dc")
    elif name == "b8-6283":
        seeds = post_ret(8, 0x6283, 0x63B5) + [0x6290]
        dump(8, seeds, "b8-6283 postret+6290")
    elif name == "b8-6a34":
        seeds = post_ret(8, 0x6A34, 0x6ABB) + [0x6A8B]
        dump(8, seeds, "b8-6a34 postret+6a8b")
    elif name == "b7-67df":
        dump(7, [0x67EF, 0x67FD, 0x68A5, 0x688E, 0x6894, 0x67A1],
             "b7-67df table routines + 67a1")
    elif name == "b7-7e18":
        seeds = post_ret(7, 0x7E18, 0x7EDD) + [0x7E22, 0x7ECB, 0x7E18]
        dump(7, seeds, "b7-7e18 postret+verified")
    elif name == "b7-7610":
        seeds = post_ret(7, 0x7610, 0x77A9) + [0x768A, 0x76C5, 0x771E]
        dump(7, seeds, "b7-7610 postret+verified")
    elif name == "b8-6669":
        seeds = post_ret(8, 0x6669, 0x67BD) + [0x6669, 0x66FD]
        dump(8, seeds, "b8-6669 postret+verified")
    elif name == "b8-67cc":
        seeds = post_ret(8, 0x67CC, 0x68B8) + [0x67CC]
        dump(8, seeds, "b8-67cc postret")
    elif name == "b8-68ef":
        seeds = post_ret(8, 0x68EF, 0x69AF) + [0x68EF, 0x6902]
        dump(8, seeds, "b8-68ef postret+verified")
    elif name == "b8-69be":
        seeds = post_ret(8, 0x69BE, 0x6A25) + [0x69BE]
        dump(8, seeds, "b8-69be postret")
    elif name == "b8-6aca":
        seeds = post_ret(8, 0x6ACA, 0x6D8A) + [0x6B77, 0x6C52]
        dump(8, seeds, "b8-6aca postret+verified")
    elif name == "b8-7292":
        dump(8, [0x7292, 0x72A9, 0x72D3, 0x74F4, 0x7588, 0x762A, 0x765D,
                 0x76B6], "b8 small gaps verified")
    elif name == "b7-6ed2":
        dump(7, [0x6ED2], "b7-6ed2")
    elif name == "b7-7001":
        dump(7, [0x701B, 0x7068, 0x706C, 0x708F, 0x70C2, 0x70E4, 0x70F0,
                 0x70F1, 0x7107, 0x7124, 0x7125, 0x7128],
             "b7-7001 table entries")
    elif name == "b16":
        dump(16, [0x617C, 0x61B2, 0x6B32, 0x6B85],
             "b16 pockets (bank-0 calls map bank 16)")


if __name__ == "__main__":
    main()
