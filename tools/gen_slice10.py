#!/usr/bin/env python3
"""Slice-10 generator: carve bank 7's $75ea tile-interaction handlers
(the $6b0a dispatch's targets) + the $750a/$75ea tables.

Why this carve (see PROGRESS.md slice 10):
  * Bank 7 $6b0a (slice 5) scans the 8 $c117 tile-sample records for
    byte 0 == $0b; on a match (and hStateTimer != $10) it indexes the
    $750a byte map by the record's byte 1, then the $75ea dw table,
    and `jp hl` to the handler. The KEY pickup runs through here:
    gb_watch proved the $c560 (rec27 byte 0) 01->00 write at key
    collection is the instruction at bank 7 $6b8e, inside handler 0
    ($6b55). The door handler is one of the other 18 -- the table is
    carved whole so the next slice can tell them apart live.
  * The 19 handlers (indices 0-18):
      0 $6b55 key pickup -- deactivates a $c200 record (index B-$40),
        zeroes $0b tiles, [$dd3c]=$02d0, res 5 [$ff94], [$c210]=6,
        then $6bf2 (set 4 [$ff91], [$dd18]=$0a, [$dd21]=$11, then
        $63c4 unless [$c837] is 3/$24/2).
      1 $6ba6, 3 $6d83, 13 $6d51 -- jump to the shared $63c4 routine.
      2 $6c7a, 4 $6c8f, 8 $6ca4, 9 $6cb9, 10 $6cce -- [$c838]=$80,
        [$c82d]/[$c835]=3, table pointer + jp $6e54.
      5 $6b09, 12 $6d50 -- single `ret` (no-op slots).
      6 $6c44, 7 $6c6a, 14 $6d9f, 15 $6daf, 16 $6dbf, 17 $6dcf --
        [$c82f]/[$c835]=$1a, table pointer + jp $6e54 (6 jumps to
        $7d5e instead) or $7d5e-family.
      11 $6ce3 -- arms the $6f62 intro animator: [$dd45]=$0168,
        timer=$11 (17), [$dd3e]=5/[$dd3f]=1/[$dd40]=8, set 7 [$dd17].
      18 $6ddf -- record transform: zeroes $0b tiles, rewrites a
        $c200 record in place ($a5/$44), then $6f06.
    Shared tails: $63c4 (spawn/setup, from handlers 1/3/13 and the
    key tail), $6e54 (table-driven `jp hl`), $6e70 (tile-zero loop),
    $6f06 (record-list scan, from handler 18), $7d5e/$7e07 (handler
    6's chain). $6e8c/$6e9a are two small routines converging on
    $6f2e (slice 4's span); $6e9a-$6ed1 is already carved, so only
    $6e8c-$6ea8 is new here.
  * Tables: $750a-$75e9 is the byte-1 -> handler-index map (224
    bytes; it ends where the $75ea pointer table begins, so byte-1
    values >= 224 would read into the pointer table -- never
    observed). $75ea-$760f is the pointer table, 19 dw entries;
    the bytes after ($7610+) are $3f3f filler, left INCBIN.
  * $6b09 is a 1-byte section (a lone `ret`); $6f06-$6f2d stops
    before $6f2e (slice 4's span) -- the boundary is a clean
    instruction boundary ($6f2c `ld d,$01` is 2 bytes, $6f2e starts
    `ld l,b`).

Regenerate with: python3 tools/gen_slice10.py
Outputs: src/bank7slice10.asm (new file). Regenerates src/banks.asm
via tools/gen_banks.py after updating its CARVED map.
The outputs are CHECKED IN; rerun after changing the config.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, decode, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# (bank, lo, hi, section title, outfile, seeds, align_bank)
CARVES = [
    (7, 0x63C4, 0x63F3, "Bank 7 $63c4 shared interaction setup",
     "src/bank7slice10.asm", [0x63C4], 7),
    (7, 0x6B09, 0x6B09, "Bank 7 $6b09 no-op handler (table entry 5)",
     "src/bank7slice10.asm", [0x6B09], 7),
    (7, 0x6B55, 0x6E8B, "Bank 7 $75ea interaction handlers",
     "src/bank7slice10.asm", [0x6B55, 0x6BA6, 0x6C7A, 0x6D83, 0x6C8F,
                               0x6C44, 0x6C6A, 0x6CA4, 0x6CB9, 0x6CCE,
                               0x6CE3, 0x6D50, 0x6D51, 0x6D9F, 0x6DAF,
                               0x6DBF, 0x6DCF, 0x6DDF], 7),
    (7, 0x6E8C, 0x6EA8, "Bank 7 $6e8c routine",
     "src/bank7slice10.asm", [0x6E8C], 7),
    (7, 0x6F06, 0x6F2D, "Bank 7 $6f06 handler-18 continuation",
     "src/bank7slice10.asm", [0x6F06], 7),
    (7, 0x7D5E, 0x7D95, "Bank 7 $7d5e handler-6 chain",
     "src/bank7slice10.asm", [0x7D5E], 7),
    (7, 0x7E07, 0x7E17, "Bank 7 $7e07 routine",
     "src/bank7slice10.asm", [0x7E07], 7),
]

# Meaningful entry labels: (bank, addr) -> name. Roles are from the
# code (call sites / the instructions themselves) or from the live
# gb_watch proof for the key handler; none is more than that.
LABELS = {
    (7, 0x63C4): "Bank7_63C4",    # shared setup; jp target from $6c41
                                  # (key tail) and handlers 1/3/13
    (7, 0x6B09): "Bank7_6B09",    # $75ea entry 5: lone ret (no-op)
    (7, 0x6B55): "Bank7_KeyPickup",  # $75ea entry 0: key pickup --
                                  # $6b8e writes $c560 (rec27 off),
                                  # verified live with gb_watch
    (7, 0x6BA6): "Bank7_Handler01",  # $75ea entry 1 -> $63c4
    (7, 0x6BF2): "Bank7_KeyPickupTail",  # handler-0 continuation
    (7, 0x6C44): "Bank7_Handler06",  # $75ea entry 6 -> $7d5e
    (7, 0x6C6A): "Bank7_Handler07",  # $75ea entry 7 -> $6e54
    (7, 0x6C7A): "Bank7_Handler02",  # $75ea entry 2 -> $6e54
    (7, 0x6C8F): "Bank7_Handler04",  # $75ea entry 4 -> $6e54
    (7, 0x6CA4): "Bank7_Handler08",  # $75ea entry 8 -> $6e54
    (7, 0x6CB9): "Bank7_Handler09",  # $75ea entry 9 -> $6e54
    (7, 0x6CCE): "Bank7_Handler10",  # $75ea entry 10 -> $6e54
    (7, 0x6CE3): "Bank7_Handler11",  # $75ea entry 11: arms the $6f62
                                  # intro animator, timer=$11 (17)
    (7, 0x6D50): "Bank7_Handler12",  # $75ea entry 12: lone ret (no-op)
    (7, 0x6D51): "Bank7_Handler13",  # $75ea entry 13 -> $63c4
    (7, 0x6D83): "Bank7_Handler03",  # $75ea entry 3 -> $63c4
    (7, 0x6D9F): "Bank7_Handler14",  # $75ea entry 14 -> $6e54
    (7, 0x6DAF): "Bank7_Handler15",  # $75ea entry 15 -> $6e54
    (7, 0x6DBF): "Bank7_Handler16",  # $75ea entry 16 -> $6e54
    (7, 0x6DCF): "Bank7_Handler17",  # $75ea entry 17 -> $6e54
    (7, 0x6DDF): "Bank7_Handler18",  # $75ea entry 18: record transform
                                  # ($a5/$44), then $6f06
    (7, 0x6E54): "Bank7_6E54",    # shared table-driven jp hl
    (7, 0x6E70): "Bank7_6E70",    # tile-zero loop
    (7, 0x6E8C): "Bank7_6E8C",    # small routine -> jp $6f2e
    (7, 0x6F06): "Bank7_6F06",    # handler-18 continuation
    (7, 0x7D5E): "Bank7_7D5E",    # handler-6 chain (jp from $6c44)
    (7, 0x7E07): "Bank7_7E07",    # routine reached from $7d5e's walk
}

# $75ea pointer-table entries, in order (verified against the ROM).
HANDLER_TABLE = [0x6B55, 0x6BA6, 0x6C7A, 0x6D83, 0x6C8F, 0x6B09,
                 0x6C44, 0x6C6A, 0x6CA4, 0x6CB9, 0x6CCE, 0x6CE3,
                 0x6D50, 0x6D51, 0x6D9F, 0x6DAF, 0x6DBF, 0x6DCF,
                 0x6DDF]


def jr_targets_in(instrs, lo, hi):
    """Addresses in [lo, hi] targeted by a jr inside the carve."""
    out = set()
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
            out.add(tgt)
    return out


def fmt_instr(bank, addr, text, kind, tgt, lo, hi, jr_targets):
    """One instruction line, with jr targets inside the carve rewritten
    to the named label (or the jr_ label) instead of a raw address."""
    if (bank, addr) in LABELS:
        label = f"{LABELS[(bank, addr)]}::"
    elif addr in jr_targets:
        label = f"jr_{bank:03x}_{addr:04x}:"
    else:
        label = None
    if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
        if (bank, tgt) in LABELS:
            tgt_label = LABELS[(bank, tgt)]
        else:
            tgt_label = f"jr_{bank:03x}_{tgt:04x}"
        text = re.sub(r"\$[0-9a-f]{4}$", tgt_label, text)
    line = f"    {text:<48} ; ${addr:04x}"
    return (label + "\n" + line) if label else line


def emit_carve(rom, bank, lo, hi, title, instrs, rst08):
    out = [f"; Slice 10: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/gen_slice10.py from the ROM bytes via",
           "; tools/gb_rd.py (recursive descent, not mgbdis' linear",
           "; sweep). Byte-match (`make`) arbitrates.",
           f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]']
    jr_targets = jr_targets_in(instrs, lo, hi)
    # Every in-carve jump target must be a decoded instruction start;
    # anything else means the walk missed a path -- fail loudly.
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind in ("call", "jump", "jr") and isinstance(tgt, int) \
                and lo <= tgt <= hi and tgt not in instrs:
            print(f"ERROR: bank {bank} ${addr:04x} {text} targets "
                  f"${tgt:04x}, not a decoded instruction",
                  file=sys.stderr)
            sys.exit(1)
    # Every rst-$08 table entry inside the carve must be decoded code
    # (WRAM entries, which cannot be decoded, are the only exception).
    for site, tbl in rst08.items():
        if not (lo <= site <= hi):
            continue
        for i, w in enumerate(tbl):
            if 0x4000 <= w <= 0x7FFF and lo <= w <= hi and w not in instrs:
                print(f"ERROR: bank {bank} rst $08 at ${site:04x} entry "
                      f"{i} -> ${w:04x}, not decoded", file=sys.stderr)
                sys.exit(1)
    addr = lo
    while addr <= hi:
        if addr in instrs:
            ln, text, kind, tgt = instrs[addr]
            if kind == "rst08":
                tbl = rst08[addr]
                out.append(f"    {'rst $08':<48} ; ${addr:04x}")
                for i, w in enumerate(tbl):
                    out.append(f"    {'dw $%04x' % w:<48} ; entry {i}")
                addr += 1 + 2 * len(tbl)
                continue
            out.append(fmt_instr(bank, addr, text, kind, tgt,
                                 lo, hi, jr_targets))
            addr += ln
        else:
            # Uncovered bytes inside the carve: honest data.
            run = []
            while addr <= hi and addr not in instrs \
                    and not any(s < addr < s + 1 + 2 * len(t)
                                for s, t in rst08.items()):
                run.append(rom[file_off(bank, addr)])
                addr += 1
            if not run:
                print(f"ERROR: bank {bank} ${addr:04x}: fell into an "
                      f"rst-$08 table outside the rst08 branch",
                      file=sys.stderr)
                sys.exit(1)
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def emit_tables(rom):
    """The $750a byte map (224 db) and the $75ea pointer table (19 dw)."""
    base = file_off(7, 0x750A)
    assert rom[file_off(7, 0x75EA):file_off(7, 0x75EA) + 2 * len(HANDLER_TABLE)] == \
        b"".join(bytes([h & 0xFF, h >> 8]) for h in HANDLER_TABLE), \
        "bank 7 $75ea table is not the expected 19 handler pointers"
    out = ["; Slice 10: Bank 7 $750a byte map + $75ea handler-pointer table.",
           "; The $6b0a dispatcher indexes $750a by the $c117 record's",
           "; byte 1 to get a handler index, then $75ea[index] for the",
           "; handler address. $750a ends at $75e9 because $75ea is the",
           "; pointer table; byte-1 values >= 224 would read into it",
           "; (never observed). Bytes after entry 18 ($7610+) are $3f3f",
           "; filler and stay INCBIN.",
           'SECTION "Bank 7 $750a byte map", ROMX[$750a], BANK[7]',
           "Bank7_TileByteMap::"]
    for j in range(0x750A, 0x75EA, 16):
        chunk = rom[file_off(7, j):file_off(7, j) + 16]
        out.append("    db " + ", ".join(f"${b:02x}" for b in chunk)
                   + f"   ; ${j:04x}")
    out.append('SECTION "Bank 7 $75ea handler table", ROMX[$75ea], BANK[7]')
    out.append("Bank7_HandlerTable::")
    for i, h in enumerate(HANDLER_TABLE):
        name = LABELS.get((7, h), f"${h:04x}")
        out.append(f"    dw {name:<18} ; entry {i} -> ${h:04x}")
    return "\n".join(out) + "\n"


def main():
    rom = open(ROM, "rb").read()
    # One walk per (align_bank, seeds); reuse across carves.
    walks = {}
    for bank, lo, hi, _t, _o, seeds, align in CARVES:
        key = (align, tuple(seeds))
        if key not in walks:
            reached, rst08, notes = walk(align, seeds)
            for n in notes:
                if "outside window" not in n:
                    print(f"NOTE: {n}")
            walks[key] = (reached, rst08)
    outputs = []
    for bank, lo, hi, title, outfile, seeds, align in CARVES:
        instrs, rst08 = walks[(align, tuple(seeds))]
        covered = set()
        for s, (ln, _t, _k, _tg) in instrs.items():
            covered.update(range(s, s + ln))
        for site, tbl in rst08.items():
            covered.update(range(site, site + 1 + 2 * len(tbl)))
        uncovered = [a for a in range(lo, hi + 1) if a not in covered]
        if uncovered:
            print(f"NOTE: bank {bank} ${lo:04x}-${hi:04x}: "
                  f"{len(uncovered)} uncovered bytes "
                  f"(emitted as db), first ${uncovered[0]:04x}")
        text = emit_carve(rom, bank, lo, hi, title, instrs, rst08)
        outputs.append(text)
        print(f"carve bank {bank} ${lo:04x}-${hi:04x} -> {outfile}")
    outputs.append(emit_tables(rom))
    print("carve bank 7 $750a map + $75ea table -> src/bank7slice10.asm")
    header = ("; DO NOT HAND-EDIT the code bodies in this file -- regenerate with\n"
              ";   python3 tools/gen_slice10.py\n"
              "; after changing the generator config. Entry labels and comments\n"
              "; may be added by hand above a generated block, not inside it.\n\n")
    with open("src/bank7slice10.asm", "w") as f:
        f.write(header + "\n".join(outputs))
    print("wrote src/bank7slice10.asm")


if __name__ == "__main__":
    main()
