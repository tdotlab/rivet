#!/usr/bin/env python3
"""Slice-27 survey phase 5: full walk dumps + coverage analysis.
For each gap: walk from verified entries + post-ret candidate starts,
report which bytes are covered / uncovered / double-covered.
Also dump full walk text for key regions.
Run: python3 tools/survey27e.py [gapname]
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, spans  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()
RET_OPS = {0xC9, 0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8}


def coverage(bank, lo, hi, seeds):
    reached, rst08, notes = walk(bank, seeds)
    cov = {}
    for addr, (ln, text, kind, tgt) in reached.items():
        for a in range(addr, addr + ln):
            cov.setdefault(a, []).append(addr)
    uncov = [a for a in range(lo, hi) if a not in cov]
    # compress uncovered into ranges
    ranges = []
    for a in uncov:
        if ranges and ranges[-1][1] == a:
            ranges[-1][1] = a + 1
        else:
            ranges.append([a, a + 1])
    dbl = {a: v for a, v in cov.items() if len(v) > 1}
    print(f"  bank {bank} ${lo:04x}-${hi:04x} seeds={[f'${s:04x}' for s in seeds]}: "
          f"{len(reached)} instrs, spans "
          f"{[(f'${a:04x}', f'${c:04x}') for a, c in spans(reached)]}")
    print(f"    uncovered: {[(f'${a:04x}', f'${b:04x}') for a, b in ranges]}")
    if dbl:
        print(f"    double-covered addrs: {len(dbl)} "
              f"(e.g. {[(f'${a:04x}', [f'${v:04x}' for v in vs]) for a, vs in list(dbl.items())[:5]]})")
    print(f"    rst08={list(rst08)} notes={notes[:2]}")
    return reached


def dump_walk(bank, seeds, maxn=200):
    reached, _, notes = walk(bank, seeds)
    print(f"  walk bank {bank} {['$%04x' % s for s in seeds]}: "
          f"{len(reached)} instrs spans "
          f"{[(f'${a:04x}', f'${c:04x}') for a, c in spans(reached)]} notes={notes[:2]}")
    for addr, (ln, text, kind, tgt) in sorted(reached.items())[:maxn]:
        print(f"    ${addr:04x}: {text}")
    return reached


def post_ret_seeds(bank, lo, hi):
    b = rom[bank * 0x4000:(bank + 1) * 0x4000]
    out = []
    for a in range(lo, hi - 1):
        if b[a - 0x4000] in RET_OPS:
            out.append(a + 1)
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "b7-67a1"):
        print("== bank7 $67a1 full walk ==")
        dump_walk(7, [0x67A1], 120)
    if which in ("all", "b7-768a"):
        print("== bank7 $768a + $76c5 + $771e full walk ==")
        dump_walk(7, [0x768A, 0x76C5, 0x771E, 0x7722, 0x773A, 0x773D, 0x7786], 200)
    if which in ("all", "b7-7abb"):
        print("== bank7 $7abb full walk (false-seed check: seeds are bank-10 entries, expect spurious) ==")
        dump_walk(7, [0x7ABB], 120)
    if which in ("all", "b7-7001"):
        print("== bank7 $7001 table entries walk ==")
        dump_walk(7, [0x701B, 0x7068, 0x706C, 0x708F, 0x70C2, 0x70E4, 0x70F0,
                      0x70F1, 0x7107, 0x7124, 0x7125, 0x7128], 200)
    if which in ("all", "b8-5905"):
        print("== bank8 $5905 verified-seeds-only walk ==")
        dump_walk(8, [0x5905, 0x5962, 0x59CB, 0x5A32, 0x5A5E, 0x5AB4,
                      0x5C51, 0x5D07], 400)
    if which in ("all", "b8-611f"):
        print("== bank8 $611f coverage: post-ret seeds ==")
        seeds = sorted(set([0x611F, 0x61DC] + post_ret_seeds(8, 0x611F, 0x6274)))
        coverage(8, 0x611F, 0x6274, seeds)
    if which in ("all", "b8-6283"):
        print("== bank8 $6283 coverage: post-ret seeds ==")
        seeds = sorted(set([0x6283] + post_ret_seeds(8, 0x6283, 0x63B5)))
        coverage(8, 0x6283, 0x63B5, seeds)
    if which in ("all", "b8-6669"):
        print("== bank8 $6669 coverage ==")
        coverage(8, 0x6669, 0x67BD, sorted(set([0x6669, 0x66FD] + post_ret_seeds(8, 0x6669, 0x67BD))))
    if which in ("all", "b8-67cc"):
        print("== bank8 $67cc coverage ==")
        coverage(8, 0x67CC, 0x68B8, sorted(set([0x67CC] + post_ret_seeds(8, 0x67CC, 0x68B8))))
    if which in ("all", "b8-68ef"):
        print("== bank8 $68ef coverage ==")
        coverage(8, 0x68EF, 0x69AF, sorted(set([0x68EF, 0x6902] + post_ret_seeds(8, 0x68EF, 0x69AF))))
    if which in ("all", "b8-69be"):
        print("== bank8 $69be coverage ==")
        coverage(8, 0x69BE, 0x6A25, sorted(set([0x69BE] + post_ret_seeds(8, 0x69BE, 0x6A25))))
    if which in ("all", "b8-6a34"):
        print("== bank8 $6a34 coverage ==")
        coverage(8, 0x6A34, 0x6ABB, sorted(set([0x6A34, 0x6A8B] + post_ret_seeds(8, 0x6A34, 0x6ABB))))
    if which in ("all", "b8-6aca"):
        print("== bank8 $6aca coverage ==")
        coverage(8, 0x6ACA, 0x6D8A, sorted(set([0x6ACA, 0x6B77, 0x6C52] + post_ret_seeds(8, 0x6ACA, 0x6D8A))))
    if which in ("all", "b8-7292"):
        print("== bank8 $7292/$74f4/$7588/$762a/$76b6 coverage ==")
        coverage(8, 0x7292, 0x7310, [0x7292, 0x72A9, 0x72D3])
        coverage(8, 0x74F4, 0x7526, [0x74F4])
        coverage(8, 0x7588, 0x7602, [0x7588])
        coverage(8, 0x762A, 0x7685, [0x762A, 0x765D])
        coverage(8, 0x76B6, 0x76E3, [0x76B6])
    if which in ("all", "b7-6581"):
        print("== bank7 $6581 coverage ==")
        coverage(7, 0x6581, 0x664D, sorted(set([0x6581, 0x662A] + post_ret_seeds(7, 0x6581, 0x664D))))
    if which in ("all", "b7-6ed2"):
        print("== bank7 $6ed2 coverage ==")
        coverage(7, 0x6ED2, 0x6F06, [0x6ED2])
    if which in ("all", "b7-7e18"):
        print("== bank7 $7e18 coverage ==")
        coverage(7, 0x7E18, 0x7EDD, sorted(set([0x7E18, 0x7E22, 0x7ECB] + post_ret_seeds(7, 0x7E18, 0x7EDD))))
    if which in ("all", "b7-7610"):
        print("== bank7 $7610 coverage ==")
        coverage(7, 0x7610, 0x77A9, sorted(set([0x7610, 0x768A, 0x76C5, 0x771E] + post_ret_seeds(7, 0x7610, 0x77A9))))


if __name__ == "__main__":
    main()
