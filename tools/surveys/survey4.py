#!/usr/bin/env python3
"""Slice-4 survey: recursive-descent reachability over mgbdis' scaffold.

Parses build/raw-mgbdis/bank_XXX.asm (linear sweep; instruction bytes are
authoritative, the mnemonics are a starting point) and walks control flow
from given seed addresses, following call/jp/jr targets inside the bank.
Reports the reachable address set per bank as merged ranges, plus:
  * rst $08 sites reached (inline tables -- bytes after are NOT code;
    the table entries are followed as additional seeds when they decode
    as in-bank pointers)
  * jr @+/-$off unresolved jumps (target = addr +/- off, slice-3 lesson)
  * call/jp targets outside the bank window (ignored: banked dispatch)

This is a SURVEY tool: its ranges guide the carve config in
tools/generators/gen_slice4.py, they are not themselves the disassembly. The
byte-match check (`make`) arbitrates every carve.
"""
import re
import sys

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
RAW = "build/raw-mgbdis"

LINE_RE = re.compile(
    r"^\s*(?P<code>[^;]*?)\s*; \$(?P<addr>[0-9a-f]{4}): (?P<bytes>(?:\$[0-9a-f]{2} ?)+)\s*$")
LABEL_RE = re.compile(r"^(?:Call|Jump|jr)_([0-9a-f]{3})_([0-9a-f]{4})\b")
AT_RE = re.compile(r"@([+-])\$([0-9a-f]+)")


def parse_raw(bank):
    """-> {addr: (code, nbytes)} from mgbdis output."""
    entries = {}
    for raw in open(f"{RAW}/bank_{bank:03x}.asm"):
        m = LINE_RE.match(raw.rstrip("\n"))
        if not m:
            continue
        addr = int(m.group("addr"), 16)
        nbytes = len(re.findall(r"\$[0-9a-f]{2}", m.group("bytes")))
        entries[addr] = (m.group("code").strip(), nbytes)
    return entries


def targets(code, addr, nbytes):
    """Yield (kind, target_addr_or_None, falls_through_bool)."""
    if not code:
        return
    # rst $08: inline table follows; control does NOT fall through here.
    if code.startswith("rst RST_08"):
        yield ("rst08", None, False)
        return
    if code.startswith("ret") or code.startswith("reti"):
        yield ("ret", None, False)
        return
    m = re.match(r"(?:call|jp)(?: [a-z]+,)?\s+(.*)$", code)
    if m:
        arg = m.group(1).strip()
        lm = LABEL_RE.match(arg)
        if lm:
            yield ("jump", int(lm.group(2), 16),
                   code.startswith("call"))
            return
        hm = re.match(r"\$([0-9a-f]{4})$", arg)
        if hm:
            yield ("jump", int(hm.group(1), 16),
                   code.startswith("call"))
            return
        # jp (hl) / jp [hl] / rst targets etc: no static target
        yield ("indirect", None, code.startswith("call"))
        return
    m = re.match(r"jr(?: ([a-z]+),)?\s+(.*)$", code)
    if m:
        cond, arg = m.group(1), m.group(2).strip()
        falls = cond is not None  # unconditional jr does not fall through
        lm = LABEL_RE.match(arg)
        if lm:
            yield ("jump", int(lm.group(2), 16), falls)
            return
        am = AT_RE.match(arg)
        if am:
            off = int(am.group(2), 16)
            if am.group(1) == "-":
                off = -off
            yield ("jump", addr + off, falls)
            return
        hm = re.match(r"\$([0-9a-f]{4})$", arg)
        if hm:
            yield ("jump", int(hm.group(1), 16), falls)
            return
        yield ("indirect", None, falls)
        return
    yield ("fall", None, True)


def walk(bank, seeds):
    """Recursive-descent reachability. Returns (reached, rst08_sites, notes)."""
    entries = parse_raw(bank)
    rom = open(ROM, "rb").read()
    reached = {}  # addr -> nbytes
    rst08 = {}
    notes = []
    stack = list(seeds)
    while stack:
        addr = stack.pop()
        if addr in reached or addr not in entries:
            if addr not in entries and 0x4000 <= addr <= 0x7FFF:
                notes.append(f"bank {bank}: target ${addr:04x} not an "
                             f"instruction boundary in mgbdis output")
            continue
        code, nbytes = entries[addr]
        reached[addr] = nbytes
        for kind, tgt, falls in targets(code, addr, nbytes):
            if kind == "rst08":
                # Bytes after are a dw table; scan it as in-bank pointers.
                tbl = []
                t = addr + 1
                while t + 1 <= 0x7FFF:
                    off = bank * 0x4000 + t - 0x4000
                    w = rom[off] | (rom[off + 1] << 8)
                    if not (0x4000 <= w <= 0x7FFF):
                        break
                    tbl.append(w)
                    t += 2
                    if len(tbl) > 64:
                        break
                rst08[addr] = tbl
                for w in tbl:
                    if w not in reached:
                        stack.append(w)
                # control returns to the caller of the rst $08 site, so
                # there is no fall-through into the table bytes.
            elif kind == "jump" and tgt is not None:
                if 0x4000 <= tgt <= 0x7FFF and tgt not in reached:
                    stack.append(tgt)
            if falls and kind != "rst08":
                nxt = addr + nbytes
                if nxt not in reached and nxt in entries:
                    stack.append(nxt)
    return reached, rst08, notes


def ranges(reached):
    """reached: {addr: nbytes} -> merged [lo, hi] byte spans."""
    spans = sorted((a, a + n - 1) for a, n in reached.items())
    out = []
    for lo, hi in spans:
        if out and lo <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def main():
    seeds = {}
    for spec in sys.argv[1:]:
        bank, addrs = spec.split(":")
        seeds[int(bank)] = [int(a, 16) for a in addrs.split(",")]
    for bank, sd in sorted(seeds.items()):
        reached, rst08, notes = walk(bank, sd)
        print(f"=== bank {bank} seeds {[f'${s:04x}' for s in sd]}: "
              f"{len(reached)} instrs, {len(rst08)} rst $08 sites")
        for lo, hi in ranges(reached):
            print(f"    ${lo:04x}-${hi:04x} ({hi - lo + 1} bytes)")
        for addr, tbl in sorted(rst08.items()):
            print(f"    rst $08 at ${addr:04x}: {len(tbl)} table entries "
                  f"-> {[f'${w:04x}' for w in tbl[:12]]}"
                  f"{' ...' if len(tbl) > 12 else ''}")
        for n in notes[:10]:
            print(f"    NOTE: {n}")


if __name__ == "__main__":
    main()
