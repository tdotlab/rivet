#!/usr/bin/env python3
"""Recursive-descent Game Boy disassembler for the DK94 decomp.

Why not mgbdis: mgbdis linear-sweeps from $4000, so one embedded data
byte or rst $08 table throws its alignment off for the rest of the bank
(slice 3 caught this after $3477; bank 2's sweep is misaligned before
$45a9). This module decodes one instruction at a time from the ROM bytes
using mgbdis' own opcode tables (instruction_set.py), and walks control
flow from seed addresses, so only genuinely reachable code is decoded
and every instruction starts at a true boundary.

GB facts baked in (verified against the ROM + prior slices):
  * jr target = addr + 2 + s8 (offset is relative to PC-after-fetch).
    mgbdis prints @+/-$off relative to the instruction's own address,
    i.e. printed off = target - addr; do NOT reuse that arithmetic here.
  * rst $08 is an inline-table dispatch: the bytes after it are a dw
    table, not code; the table-entry routines `ret` to the rst site's
    caller, so there is no fall-through into the table.
  * rst $10 is the bank switch (returns normally: falls through).
  * stop is 2 bytes only when followed by $00, else the $10 is data.

API:
  decode(rom, file_off) -> (length, text, kind, target)
    kind: 'fall' | 'ret' | 'call' | 'jump' | 'jr' | 'rst08' | 'data'
    target: absolute window address ($4000-$7fff for ROMX) or None.
    text: RGBDS assembly for the instruction (numeric operands; jr/call/
    jp targets emitted as absolute $xxxx, which RGBDS accepts).
  walk(bank, seeds) -> (reached {addr: (len, text, kind, target)},
                        rst08 {site: [entries]}, notes [str])
"""
import sys

sys.path.insert(0, "/home/hatch/workspace/tools/mgbdis")
from instruction_set import instructions, cb_instructions  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

INVALID = {0xD3, 0xDB, 0xDD, 0xE3, 0xE4, 0xEB, 0xEC, 0xED, 0xF4, 0xFC, 0xFD}


def s8(b):
    return b - 256 if b >= 128 else b


def _fmt_operand(template, rom, off, addr, length_out):
    """Resolve one operand template. Returns (text, extra_len, value)."""
    if template == "a16":
        v = rom[off + 1] | (rom[off + 2] << 8)
        return f"${v:04x}", 2, v
    if template == "[a16]":
        v = rom[off + 1] | (rom[off + 2] << 8)
        return f"[${v:04x}]", 2, v
    if template == "d16":
        v = rom[off + 1] | (rom[off + 2] << 8)
        return f"${v:04x}", 2, v
    if template == "d8":
        return f"${rom[off + 1]:02x}", 1, rom[off + 1]
    if template in ("[a8]", "[$ff00+a8]", "[$ffa8]"):
        return f"[$ff{rom[off + 1]:02x}]", 1, 0xFF00 + rom[off + 1]
    if template == "r8":
        return f"${s8(rom[off + 1]):+d}", 1, s8(rom[off + 1])
    if template == "pc+r8":
        tgt = addr + 2 + s8(rom[off + 1])
        return f"${tgt:04x}", 1, tgt
    if template == "sp+r8":
        v = s8(rom[off + 1])
        return f"sp{'+' if v >= 0 else '-'}${abs(v):02x}", 1, v
    if template == "vec":
        return f"${rom[off] & 0x38:02x}", 0, rom[off] & 0x38
    if template == "[$ff00+c]":
        return "[c]", 0, None
    # plain register / condition / flag token
    return template, 0, None


def decode(rom, off, addr):
    """Decode one instruction at ROM file offset `off` (window addr `addr`).

    Returns (length, text, kind, target). kind 'data' means the byte is
    not a valid opcode start (emit as db); length is 1 then.
    """
    op = rom[off]
    if op in INVALID:
        return 1, f"db ${op:02x}", "data", None
    if op == 0xCB:
        cb = rom[off + 1]
        template = cb_instructions[cb]
        parts = template.split(" ", 1)
        name = parts[0]
        ops = parts[1].split(",") if len(parts) > 1 else []
        text = name + (" " + ", ".join(o.strip() for o in ops) if ops else "")
        return 2, text, "fall", None
    if op == 0x10:  # stop: 2 bytes only if followed by $00
        if rom[off + 1] == 0x00:
            return 2, "stop", "fall", None
        return 1, "db $10", "data", None
    template = instructions[op]
    parts = template.split(" ", 1)
    name = parts[0]
    raw_ops = parts[1].split(",") if len(parts) > 1 else []
    length = 1
    texts, values = [], []
    for t in raw_ops:
        t = t.strip()
        txt, extra, val = _fmt_operand(t, rom, off, addr, length)
        length += extra
        texts.append(txt)
        values.append(val)
    text = name + (" " + ", ".join(texts) if texts else "")
    # ldh forms: mgbdis/RGBDS style is `ldh a, [$ff8c]` / `ldh [$ff8c], a`
    # and `ldh a, [c]` / `ldh [c], a` (mgbdis emits ldh for E2/F2 too).
    if name == "ld" and any(o in ("[a8]", "[$ff00+a8]", "[$ffa8]",
                               "[c]", "[$ff00+c]") for o in raw_ops):
        text = "ldh " + ", ".join(texts)
    if name == "rst":
        vec = op & 0x38
        if vec == 0x08:
            return 1, "rst $08", "rst08", None
        return 1, f"rst ${vec:02x}", "fall", None
    if name in ("ret", "reti"):
        if name == "reti" or not raw_ops:
            return length, text, "ret", None
        # conditional ret falls through when the condition is false
        return length, text, "cret", None
    if name == "call":
        tgt = values[-1]
        return length, text, "call", tgt
    if name == "jp":
        # jp (hl) has operand '(hl)' -> no numeric target
        tgt = values[-1] if values and isinstance(values[-1], int) else None
        cond = len(raw_ops) > 1
        return length, text, "jump", tgt if tgt is not None else "indirect"
    if name == "jr":
        tgt = values[-1]
        cond = len(raw_ops) > 1
        return length, text, "jr", tgt
    return length, text, "fall", None


def file_off(bank, addr):
    return bank * 0x4000 + (addr - 0x4000 if bank else addr)


def walk(bank, seeds, max_rst08_table=128):
    """Recursive-descent walk. Returns (reached, rst08, notes)."""
    rom = open(ROM, "rb").read()
    reached = {}
    rst08 = {}
    notes = []
    stack = list(seeds)
    while stack:
        addr = stack.pop()
        if addr in reached:
            continue
        if not (0x4000 <= addr <= 0x7FFF) and bank != 0:
            notes.append(f"bank {bank}: target ${addr:04x} outside window")
            continue
        if bank == 0 and not (0x0000 <= addr <= 0x3FFF):
            notes.append(f"bank 0: target ${addr:04x} outside ROM0")
            continue
        off = file_off(bank, addr)
        length, text, kind, tgt = decode(rom, off, addr)
        if kind == "data":
            notes.append(f"bank {bank}: ${addr:04x} decodes as data "
                         f"({text}) -- path stops")
            continue
        reached[addr] = (length, text, kind, tgt)
        if kind == "rst08":
            tbl = []
            t = addr + 1
            while len(tbl) < max_rst08_table and t + 1 <= 0x7FFF:
                w = rom[file_off(bank, t)] | (rom[file_off(bank, t + 1)] << 8)
                if not (0x4000 <= w <= 0x7FFF or 0xC000 <= w <= 0xDFFF):
                    break
                tbl.append(w)
                t += 2
            rst08[addr] = tbl
            for w in tbl:
                if 0x4000 <= w <= 0x7FFF and w not in reached:
                    stack.append(w)
            continue
        if kind == "ret":
            continue
        if kind == "cret":
            nxt = addr + length
            if nxt not in reached:
                stack.append(nxt)
            continue
        if kind in ("call", "jump", "jr"):
            cond = False
            if kind == "call":
                if tgt is not None and tgt != "indirect" and tgt not in reached:
                    stack.append(tgt)
                # calls always fall through to the next instruction
                nxt = addr + length
                if nxt not in reached:
                    stack.append(nxt)
            elif kind == "jump":
                is_cond = "," in text
                if tgt not in (None, "indirect") and tgt not in reached:
                    stack.append(tgt)
                if is_cond:
                    nxt = addr + length
                    if nxt not in reached:
                        stack.append(nxt)
            elif kind == "jr":
                is_cond = "," in text
                if tgt not in reached:
                    stack.append(tgt)
                if is_cond:
                    nxt = addr + length
                    if nxt not in reached:
                        stack.append(nxt)
            continue
        # fall: next instruction
        nxt = addr + length
        if nxt not in reached:
            stack.append(nxt)
    return reached, rst08, notes


def spans(reached):
    """Merge {addr: (len,...)} into [lo, hi] byte spans."""
    iv = sorted((a, a + v[0] - 1) for a, v in reached.items())
    out = []
    for lo, hi in iv:
        if out and lo <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


if __name__ == "__main__":
    for spec in sys.argv[1:]:
        bank, addrs = spec.split(":")
        bank = int(bank)
        seeds = [int(a, 16) for a in addrs.split(",")]
        reached, rst08, notes = walk(bank, seeds)
        print(f"=== bank {bank} seeds {[f'${s:04x}' for s in seeds]}: "
              f"{len(reached)} instrs, {len(rst08)} rst $08 sites")
        for lo, hi in spans(reached):
            print(f"    ${lo:04x}-${hi:04x} ({hi - lo + 1} bytes)")
        for addr, tbl in sorted(rst08.items()):
            print(f"    rst $08 at ${addr:04x}: {len(tbl)} entries "
                  f"-> {[f'${w:04x}' for w in tbl[:16]]}"
                  f"{' ...' if len(tbl) > 16 else ''}")
        for n in notes[:12]:
            print(f"    NOTE: {n}")
