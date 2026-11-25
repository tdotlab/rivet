#!/usr/bin/env python3
"""Slice-5 generator: carve bank 7 $6f62 dispatch + scattered spans and
bank 23 $7722 dispatch + handlers, with rst-$08 table support.

New in slice 5 (vs gen_slice4.py, which errored on any rst $08):
  * tools/gb_rd.py's walk() already decoded rst-$08 tables (it reads
    the dw entries after the rst and walks each target); the cap on
    table entries was raised 64 -> 128, because bank 23's table at
    $7723 has 74 entries. The table ends at the first word that is
    not a plausible address ($01ee after bank 7's 4-entry table,
    $013e after bank 23's 74-entry table).
  * emit_carve() now EMITS rst-$08 tables: `rst $08` followed by
    `dw` lines, one per entry. The bytes after the table are code
    again (bank 23: $77b7, itself table entry 56).
  * Bank 7's $6f74 table OVERLAPS its return code, and needs a
    hand-written emission (emit_bank7_6f62): the dispatch pushes
    $6f79 as the return address, and the bytes at $6f79-$6f80
    (`ld hl, $dd41; ld a, [hl]; xor $01; ld [hl], a; ret`) are
    exactly the table's entries 2-3 ($4121 = bytes 21 41, $7edd =
    bytes dd 7e). So entries 0-1 are emitted as `dw` and entries
    2-3 as the return-code instructions that produce the same
    bytes. The generator asserts the ROM bytes match.
  * Bank 7's $4016-$41dc span has three sub-spans ($4085-$4120,
    $4133-$4156, $41aa-$41c8) the $6f62 walk alone does not reach:
    they decode as clean code that merges exactly with the $4121
    entry's walk (341 instructions, no data notes, $408d jumps to
    $41aa, $41aa's code jumps back to $408f), so they are seeded
    by hand. They are most likely `jp hl` continuations -- the
    spans $4016-$41dc, $480e-$4826, $6572-$6580, $68ad-$68c3,
    $6b0a-$6b54, $6f81-$7000, $7edd-$7f0c all end in `jp hl`
    (computed return) -- but the exact entry mechanism is
    unverified; the seeds are recorded here, not hidden.

What slice 5 carves (see PROGRESS.md):
  * bank 7: $4016-$41dc (the $4121 dispatch entry's code, incl. the
    three hand-seeded sub-spans), $480e-$4826, $6572-$6580,
    $68ad-$68c3, $6b0a-$6b54, $6f62-$6f80 (prologue + 4-entry
    rst-$08 table + overlapping return code), $6f81-$7000 (entries
    0-1 code, incl. $6fad, the bit-7-set branch from $6f66),
    $7edd-$7f0c (entry 3 code).
  * bank 23: $7717-$7e11 (prologue $7717-$7722, 74-entry rst-$08
    table $7723-$77b6, handlers $77b7-$7e11, one contiguous span).

Regenerate with: python3 tools/generators/gen_slice5.py
Outputs: src/banks/bank7slice5.asm src/banks/bank23slice5.asm (new files, so
gen_slice3/gen_slice4 outputs are untouched); regenerates
src/banks.asm via tools/generators/gen_banks.py after updating its CARVED map.
The outputs are CHECKED IN; rerun after changing the config.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, decode, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# (bank, lo, hi, section title, outfile, seeds, align_bank)
CARVES = [
    (7, 0x4016, 0x41DC, "Bank 7 $4121 dispatch entry + $4016 code",
     "src/banks/bank7slice5.asm", [0x6F62, 0x4085, 0x4133, 0x41AA], 7),
    (7, 0x480E, 0x4826, "Bank 7 $480e routine",
     "src/banks/bank7slice5.asm", [0x6F62, 0x4085, 0x4133, 0x41AA], 7),
    (7, 0x6572, 0x6580, "Bank 7 $6572 routine",
     "src/banks/bank7slice5.asm", [0x6F62, 0x4085, 0x4133, 0x41AA], 7),
    (7, 0x68AD, 0x68C3, "Bank 7 $68ad routine",
     "src/banks/bank7slice5.asm", [0x6F62, 0x4085, 0x4133, 0x41AA], 7),
    (7, 0x6B0A, 0x6B54, "Bank 7 $6b0a routine",
     "src/banks/bank7slice5.asm", [0x6F62, 0x4085, 0x4133, 0x41AA], 7),
    (7, 0x6F81, 0x7000, "Bank 7 $6f81/$6f96 dispatch entries",
     "src/banks/bank7slice5.asm", [0x6F62, 0x4085, 0x4133, 0x41AA], 7),
    (7, 0x7EDD, 0x7F0C, "Bank 7 $7edd dispatch entry",
     "src/banks/bank7slice5.asm", [0x6F62, 0x4085, 0x4133, 0x41AA], 7),
    (23, 0x7717, 0x7E11, "Bank 23 $7722 dispatch + handlers",
     "src/banks/bank23slice5.asm", [0x7722], 23),
]

# Meaningful entry labels: (bank, addr) -> name. Roles are from the
# code (call sites / the instructions themselves); none of these are
# more than address-derived + a one-line note.
LABELS = {
    (7, 0x4016): "Bank7_4016",    # jp z target from $41cd (in $4121 code)
    (7, 0x4121): "Bank7_4121",    # rst-$08 table entry 2 of $6f74
    (7, 0x480E): "Bank7_480E",    # called from $401f
    (7, 0x6572): "Bank7_6572",    # called (cond) from $4815
    (7, 0x68AD): "Bank7_68AD",    # called from $4016
    (7, 0x6B0A): "Bank7_6B0A",    # called from $4022
    (7, 0x6F62): "Bank7_6F62",    # countdown on [$dd40], 4-way dispatch
                                  # on [$dd41]; called from state-16
                                  # step 18 ($08ee, bank 0)
    (7, 0x6F81): "Bank7_6F81",    # rst-$08 table entry 0 of $6f74
    (7, 0x6F96): "Bank7_6F96",    # rst-$08 table entry 1 of $6f74
    (7, 0x6FAD): "Bank7_6FAD",    # jr c target from $6f66 ([$dd41] bit 7)
    (7, 0x7EDD): "Bank7_7EDD",    # rst-$08 table entry 3 of $6f74
    (23, 0x7717): "Bank23_7717",  # called from $7707 (bank-23 $76f1 loop);
                                  # stores HL to $ca6a/$ca6b, dispatches
                                  # on A=[HL] via rst $08 at $7722
}


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
    out = [f"; Slice 5: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/generators/gen_slice5.py from the ROM bytes via",
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
                # Inside an rst-$08 table the generic loop should never
                # land here (the rst08 branch skips the table); if it
                # does, the table bookkeeping is wrong -- fail loudly.
                print(f"ERROR: bank {bank} ${addr:04x}: fell into an "
                      f"rst-$08 table outside the rst08 branch",
                      file=sys.stderr)
                sys.exit(1)
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def emit_bank7_6f62(rom, instrs):
    """Bank 7 $6f62-$6f80: prologue + 4-entry rst-$08 table + return code.

    The table OVERLAPS the return code: the dispatch pushes $6f79 as
    the return address, and the bytes at $6f79-$6f80 are both table
    entries 2-3 ($4121 = 21 41, $7edd = dd 7e) and the return code
    (`ld hl, $dd41; ld a, [hl]; xor $01; ld [hl], a; ret`). Entries
    0-1 are emitted as `dw`; entries 2-3 as the return-code
    instructions that produce the same bytes. Asserted below.
    """
    base = file_off(7, 0x6F79)
    assert rom[base:base + 8] == bytes(
        [0x21, 0x41, 0xDD, 0x7E, 0xEE, 0x01, 0x77, 0xC9]), \
        "bank 7 $6f79-$6f80 is not the expected return code"
    out = ["; Slice 5: Bank 7 $6f62 dispatch (rst $08) -- bank 7 "
           "$6f62-$6f80.",
           "; Generated by tools/generators/gen_slice5.py (hand-written emission,",
           "; see the module docstring for why: the rst-$08 table at",
           "; $6f75 OVERLAPS the return code at $6f79). Byte-match",
           "; (`make`) arbitrates.",
           'SECTION "Bank 7 $6f62 dispatch (rst $08)", ROMX[$6f62], '
           'BANK[7]']
    addr = 0x6F62
    while addr <= 0x6F74:
        ln, text, kind, tgt = instrs[addr]
        if addr == 0x6F6D:
            # `ld hl, $6f79` -- the pushed return address; use the label.
            text = "ld hl, Bank7_6F62Return"
        if (7, addr) in LABELS:
            out.append(f"{LABELS[(7, addr)]}::")
        out.append(f"    {text:<48} ; ${addr:04x}")
        addr += ln
    out += ["    dw $6f81"
            f"{'':<40} ; entry 0",
            "    dw $6f96"
            f"{'':<40} ; entry 1",
            "    ; entries 2 ($4121) and 3 ($7edd) share bytes with the",
            "    ; return code below -- same bytes, emitted once.",
            "Bank7_6F62Return::",
            "    ld hl, $dd41"
            f"{'':<36} ; $6f79",
            "    ld a, [hl]"
            f"{'':<38} ; $6f7c",
            "    xor $01"
            f"{'':<41} ; $6f7d",
            "    ld [hl], a"
            f"{'':<38} ; $6f7f",
            "    ret"
            f"{'':<45} ; $6f80"]
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
    outputs = {}
    for bank, lo, hi, title, outfile, seeds, align in CARVES:
        instrs, rst08 = walks[(align, tuple(seeds))]
        # Every byte of the carve must be covered by a reached
        # instruction or an rst-$08 table entry (gaps are emitted as
        # db, but for slice 5 the carves were chosen to be fully
        # covered -- report otherwise).
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
        outputs.setdefault(outfile, []).append(text)
        print(f"carve bank {bank} ${lo:04x}-${hi:04x} -> {outfile}")
    # The $6f62 dispatch needs its own emitter (overlapping table).
    instrs, _rst08 = walks[(7, (0x6F62, 0x4085, 0x4133, 0x41AA))]
    outputs.setdefault("src/banks/bank7slice5.asm", []).append(
        emit_bank7_6f62(rom, instrs))
    print("carve bank 7 $6f62-$6f80 (custom rst-$08 overlap emission)")
    header = ("; DO NOT HAND-EDIT the code bodies in this file -- regenerate with\n"
              ";   python3 tools/generators/gen_slice5.py\n"
              "; after changing the generator config. Entry labels and comments\n"
              "; may be added by hand above a generated block, not inside it.\n\n")
    for outfile, chunks in outputs.items():
        # The $6f62 section must come first in bank7slice5.asm (it is
        # the dispatch; the other sections are its targets).
        if outfile == "src/banks/bank7slice5.asm":
            chunks = [chunks[-1]] + chunks[:-1]
        with open(outfile, "w") as f:
            f.write(header + "\n".join(chunks))
        print(f"wrote {outfile}")


if __name__ == "__main__":
    main()
