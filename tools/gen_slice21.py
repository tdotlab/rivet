#!/usr/bin/env python3
"""Slice-21 generator: close bank 9 (all gaps except the $ff tail).

Bank 9's $4000 dispatch table is 197 entries (slice 21 corrects slice
9's 16-entry read -- see tools/gen_slice9_bank9.py): entries 0-196,
A = record byte1 - $30. This generator carves every handler the table
points at in $4691-$63f3, plus the helpers and the routine tails the
slice-17 walk left short:

  * $4691-$48df: entries 45 ($4691), 24/35 ($46dc), 7 ($46a4 -- entry
    7's routine was never emitted by slice 9: its span ended at
    $4691, and $46a4 sits past that boundary).
  * $492e-$49a0: entry 42. $49d7-$4b4d: entries 64/65.
    $4b52-$5a02: entries 74, 76, 103/185, 104-109, 112, 114.
    $5a04-$63f2: entries 117-120, 178-181, 187-191, 196, plus the
    $264a pocket ($6182/$61f4/$6266/$62cd/$6308/$636f -- bank-0 $264a
    jp's to them on [$c725]; entry mechanism RESOLVED, not unverified).
  * Data pockets (ld-hl referenced, never code): $48e0-$492d (read by
    $4823), $49a1-$49d6 (read by $4972), $4b4e-$4b51 (read by $4b6c),
    $6e63-$6e69 (read by $6e41), $6d59-$6d5a + $6d6b-$6d6c (00 00
    padding), $64cb-$6573 (169-byte opaque blob, no reference found).
  * Helpers: $6402 (HL = $c200 + [$c70d]*16, the $c200 analogue of
    $63f3 -- no caller found, entry UNVERIFIED), $6412 (push-bc
    pointer/bit routine, entry UNVERIFIED), $643e (clear one byte at
    $c0a6+idx, entry UNVERIFIED), $644b (jp'd to from $5a46/$5a8b/
    $5ad0/$5b15/$6063/$60a8/$60ed), $6485 (inc [$da4a] x2; called from
    $61e3/$6255), $648b (inc [$da46]; jp'd to from the pocket tails).
  * $2b48-entry-89 region tails the slice-17 walk left short:
    $6962-$696a, $699a-$69ab, $6a08-$6a10, $6a40-$6a52, $6a7d-$6a9b,
    $6ac8-$6ae6, $6b43-$6b4b, $6b7b-$6b8c, $6be9-$6bf1, $6c21-$6c33,
    $6c5f-$6c7d, $6caa-$6cb6 (all routine continuations, walk-covered).
  * $6d6d-$6d8a (the $6d47 word's routine -- entry UNVERIFIED; the
    $6d33 table is 10 entries, so $6d6d is not entry 10),
    $6e94-$6eb0 (c=$08 variant), $6ed9-$6f0b (c=$03 variant),
    $6f0c-$6f33 (c=$07 variant, falls through to $6f34),
    $6f65-$6f9a (position-check helper) -- all four decode cleanly
    and belong to the $6eb1 family, but no call/jp to any of them
    exists anywhere in the ROM, so all four are entry-UNVERIFIED.
  * $5a03: 1-byte ret ($c9), entry UNVERIFIED (same class as $6f9b).

Door / clear chain: NONE of the carved code writes hStateTimer
($ff90) or [$c105] -- verified by grep over the walk (see
tools/survey21_coverage.py). No new door lead; no completion attempt
(same NO-GO as slices 15-20).

Bank 9 after this slice: CARVED covers $4000-$6fab except the $ff
padding tail $6fac-$8000 (4,180 bytes, stays INCBIN -- the bank's last
non-$ff byte is at $6fa7).

Regenerate with: python3 tools/gen_slice21.py
Outputs: src/bank9slice21.asm (new file).
Also update tools/gen_banks.py CARVED (bank 9) and regenerate
src/banks.asm; add INCLUDE "bank9slice21.asm" to src/main.asm.
The outputs are CHECKED IN; rerun after changing the config.
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"

# (bank, lo, hi, section title, outfile) -- hi inclusive.
CARVES = [
    (9, 0x4691, 0x48DF, "Bank 9 $4691-$48df $4000-table entries 45/24/35/7",
     "src/bank9slice21.asm"),
    (9, 0x492E, 0x49A0, "Bank 9 $492e-$49a0 $4000-table entry 42",
     "src/bank9slice21.asm"),
    (9, 0x49D7, 0x4B4D, "Bank 9 $49d7-$4b4d $4000-table entries 64/65",
     "src/bank9slice21.asm"),
    (9, 0x4B52, 0x5A02, "Bank 9 $4b52-$5a02 $4000-table entries "
     "74/76/103/104/105/106/107/108/109/112/114",
     "src/bank9slice21.asm"),
    (9, 0x5A04, 0x63F2, "Bank 9 $5a04-$63f2 $4000-table entries "
     "117/118/119/120/178/179/180/181/187/188/189/190/191/196 + "
     "$264a pocket", "src/bank9slice21.asm"),
    (9, 0x6402, 0x6411, "Bank 9 $6402-$6411 $c200-pointer helper",
     "src/bank9slice21.asm"),
    (9, 0x6412, 0x643D, "Bank 9 $6412-$643d pointer/bit helper",
     "src/bank9slice21.asm"),
    (9, 0x643E, 0x644A, "Bank 9 $643e-$644a $c0a6-clear helper",
     "src/bank9slice21.asm"),
    (9, 0x644B, 0x647F, "Bank 9 $644b-$647f helper",
     "src/bank9slice21.asm"),
    (9, 0x6485, 0x648A, "Bank 9 $6485-$648a inc [$da4a] x2",
     "src/bank9slice21.asm"),
    (9, 0x648B, 0x648F, "Bank 9 $648b-$648f inc [$da46]",
     "src/bank9slice21.asm"),
    (9, 0x6962, 0x696A, "Bank 9 $6962-$696a table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x699A, 0x69AB, "Bank 9 $699a-$69ab table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6A08, 0x6A10, "Bank 9 $6a08-$6a10 table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6A40, 0x6A52, "Bank 9 $6a40-$6a52 table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6A7D, 0x6A9B, "Bank 9 $6a7d-$6a9b table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6AC8, 0x6AE6, "Bank 9 $6ac8-$6ae6 table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6B43, 0x6B4B, "Bank 9 $6b43-$6b4b table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6B7B, 0x6B8C, "Bank 9 $6b7b-$6b8c table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6BE9, 0x6BF1, "Bank 9 $6be9-$6bf1 table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6C21, 0x6C33, "Bank 9 $6c21-$6c33 table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6C5F, 0x6C7D, "Bank 9 $6c5f-$6c7d table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6CAA, 0x6CB6, "Bank 9 $6caa-$6cb6 table-routine tail",
     "src/bank9slice21.asm"),
    (9, 0x6D6D, 0x6D8A, "Bank 9 $6d6d-$6d8a $6d47-word routine",
     "src/bank9slice21.asm"),
    (9, 0x6E94, 0x6EB0, "Bank 9 $6e94-$6eb0 c=$08 scan variant",
     "src/bank9slice21.asm"),
    (9, 0x6ED9, 0x6F0B, "Bank 9 $6ed9-$6f0b c=$03 scan variant",
     "src/bank9slice21.asm"),
    (9, 0x6F0C, 0x6F33, "Bank 9 $6f0c-$6f33 c=$07 scan variant",
     "src/bank9slice21.asm"),
    (9, 0x6F65, 0x6F9A, "Bank 9 $6f65-$6f9a position-check helper",
     "src/bank9slice21.asm"),
]

# Meaningful entry labels: (bank, addr) -> name.
LABELS = {}
for _a in (0x4691, 0x46A4, 0x46DC, 0x4784, 0x47C2, 0x492E, 0x4955,
           0x49D7, 0x4A92, 0x4B52, 0x4F15, 0x4FBD, 0x5044, 0x5174,
           0x5251, 0x533C, 0x541D, 0x5507, 0x55E8, 0x582E, 0x5A04,
           0x5A49, 0x5A8E, 0x5AD3, 0x5B18, 0x5BF3, 0x5CCE, 0x5EA1,
           0x6021, 0x6066, 0x60AB, 0x60F0, 0x6139, 0x63B1, 0x6182,
           0x61E9, 0x61F4, 0x625B, 0x6266, 0x62CD, 0x6308, 0x636F,
           0x6402, 0x6412, 0x643E, 0x644B, 0x6485, 0x648B, 0x6D6D,
           0x6E94, 0x6ED9, 0x6F0C, 0x6F65, 0x5A03):
    LABELS[(9, _a)] = f"Bank9_{_a:04X}"


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


def emit_carve(rom, bank, lo, hi, title, instrs):
    section = "ROM0" if bank == 0 else "ROMX"
    bankarg = f", BANK[{bank}]" if bank != 0 else ""
    out = [f"; Slice 21: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/gen_slice21.py from the ROM bytes via",
           "; tools/gb_rd.py (recursive descent, not mgbdis' linear",
           "; sweep). Byte-match (`make`) arbitrates.",
           f'SECTION "{title}", {section}[${lo:04x}]{bankarg}']
    jr_targets = jr_targets_in(instrs, lo, hi)
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind in ("call", "jump", "jr") and isinstance(tgt, int) \
                and lo <= tgt <= hi and tgt not in instrs:
            print(f"ERROR: bank {bank} ${addr:04x} {text} targets "
                  f"${tgt:04x}, not a decoded instruction",
                  file=sys.stderr)
            sys.exit(1)
    addr = lo
    while addr <= hi:
        if addr in instrs:
            ln, text, kind, tgt = instrs[addr]
            out.append(fmt_instr(bank, addr, text, kind, tgt,
                                 lo, hi, jr_targets))
            addr += ln
        else:
            # Uncovered bytes inside the carve: honest data.
            run = []
            while addr <= hi and addr not in instrs:
                run.append(rom[file_off(bank, addr)])
                addr += 1
            label = LABELS.get((bank, addr - len(run)))
            if label:
                out.append(f"{label}::")
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def emit_db(rom, bank, lo, hi, title, note=None):
    """A raw-byte range, 8 bytes per db line, with a section header."""
    label = LABELS.get((bank, lo))
    out = [f"; Slice 21: {title} -- bank {bank} ${lo:04x}-${hi:04x}."]
    if note:
        out.append(f"; {note}")
    out.append("; Generated by tools/gen_slice21.py; bytes read straight "
               "from the ROM.")
    out.append(f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]')
    if label:
        out.append(f"{label}::")
    addr = lo
    while addr <= hi:
        chunk = [rom[file_off(bank, a)] for a in
                 range(addr, min(addr + 8, hi + 1))]
        out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
        addr += len(chunk)
    return "\n".join(out) + "\n"


def emit_ret1(rom, bank, addr, title, note=None):
    """A 1-byte `ret` ($c9), verified against the ROM."""
    assert rom[file_off(bank, addr)] == 0xC9, \
        f"bank {bank} ${addr:04x} is not $c9"
    label = LABELS.get((bank, addr))
    out = [f"; Slice 21: {title} -- bank {bank} ${addr:04x} 1-byte ret."]
    if note:
        out.append(f"; {note}")
    out.append("; Verified byte $c9.")
    out.append(f'SECTION "{title}", ROMX[${addr:04x}], BANK[{bank}]')
    if label:
        out.append(f"{label}::")
    out.append(f"    ret                                              ; ${addr:04x}")
    return "\n".join(out) + "\n"


def main():
    rom = open(ROM, "rb").read()
    # 50 non-noop targets of the $4001 dispatch table (197 entries).
    table_targets = set()
    for a in range(0x4001, 0x418B, 2):
        w = rom[file_off(9, a)] | (rom[file_off(9, a + 1)] << 8)
        if w != 0x1D29:
            table_targets.add(w)
    # $264a (bank 0) jp targets -- the $6182 pocket.
    pocket = [0x6182, 0x61F4, 0x6266, 0x62CD, 0x6308, 0x636F]
    # Helpers / small routines / tails, incl. entry-UNVERIFIED hand seeds.
    extra = [0x6402, 0x6412, 0x643E, 0x644B, 0x6485, 0x648B, 0x6D6D,
             0x6E94, 0x6ED9, 0x6F0C, 0x6F65, 0x6574, 0x6CCE, 0x6D8B]
    seeds = sorted(table_targets | set(pocket) | set(extra))
    reached, rst08, notes = walk(9, seeds)
    for n in notes:
        if "outside window" not in n:
            print("note:", n, file=sys.stderr)
    print(f"walk bank 9: {len(reached)} instrs from {len(seeds)} seeds; "
          f"{len(rst08)} rst $08 sites", file=sys.stderr)
    assert not rst08, f"unexpected rst $08: {rst08}"
    for _v in table_targets | set(pocket):
        assert _v in reached, f"seed ${_v:04x} not decoded"
    by_file = {}
    for bank, lo, hi, title, outfile in CARVES:
        instrs = {a: v for a, v in reached.items() if lo <= a <= hi}
        covered = set()
        for a, (ln, *_r) in instrs.items():
            covered.update(range(a, a + ln))
        assert covered == set(range(lo, hi + 1)), \
            f"bank {bank} ${lo:04x}-${hi:04x}: uncovered bytes " \
            f"{sorted(set(range(lo, hi + 1)) - covered)[:8]}"
        by_file.setdefault(outfile, []).append(
            (bank, lo, hi, title, instrs))

    # ---- bank 9 data carves ----
    b9_data = []
    b9_data.append(emit_db(
        rom, 9, 0x48E0, 0x492D, "Bank 9 $48e0-$492d data table",
        note="Read by $4823 (`ld hl,$48e0`) inside the $4691 handler; "
             "4-byte records ($60 01 60 04, $40 01 40 04, ...). "
             "Internal structure unresolved -- plain db."))
    b9_data.append(emit_db(
        rom, 9, 0x49A1, 0x49D6, "Bank 9 $49a1-$49d6 data table",
        note="Read by $4972 (`ld hl,$49a1`) inside the $492e handler; "
             "repeating ($08 $10 / $08 $01) pairs, then "
             "$00 $02 $04 $06 $06 $06 $06 $04 $02 $00 $1e $3c $3d $78. "
             "Internal structure unresolved -- plain db."))
    b9_data.append(emit_db(
        rom, 9, 0x4B4E, 0x4B51, "Bank 9 $4b4e-$4b51 data table",
        note="Read by $4b6c (`ld hl,$4b4e`) inside the $4b52 handler; "
             "4 bytes ($f0 $f0 $96 $96). Meaning unresolved."))
    b9_data.append(emit_ret1(
        rom, 9, 0x5A03, "Bank 9 $5a03 1-byte ret",
        note="Entry UNVERIFIED (same class as $6f9b): no call/jp to "
             "$5a03 anywhere in the ROM; it sits between the $4b52 "
             "routine's end ($5a02) and entry 117 ($5a04)."))
    b9_data.append(emit_db(
        rom, 9, 0x64CB, 0x6573, "Bank 9 $64cb-$6573 data blob",
        note="169 bytes, no `ld hl,$64cb` (or any $64cb-$6573 pointer) "
             "anywhere in the ROM. Opens with ($06 $00 $8a $ff $86 "
             "$ff $8a $ff) then 7-byte groups, then ($xx $82) pairs "
             "($0f $82, $10 $82, ...). Internal structure unresolved "
             "-- plain db."))
    b9_data.append(emit_db(
        rom, 9, 0x6D59, 0x6D5A, "Bank 9 $6d59-$6d5a padding",
        note="Two $00 bytes between the $6d49 and $6d5b "
             "signed-offset tables."))
    b9_data.append(emit_db(
        rom, 9, 0x6D6B, 0x6D6C, "Bank 9 $6d6b-$6d6c padding",
        note="Two $00 bytes before the $6d6d routine."))
    b9_data.append(emit_db(
        rom, 9, 0x6E63, 0x6E69, "Bank 9 $6e63-$6e69 data blob",
        note="Read by $6e41 (`ld hl,$6e63`) inside the $6de0 routine "
             "-- a data pointer, not a code entry (slice-17 lesson). "
             "7 bytes ($a8 $f8 $a8 $f8 $a8 $a8 $f8). Meaning "
             "unresolved."))
    by_file.setdefault("src/bank9slice21.asm", []).extend(b9_data)

    for outfile, parts in by_file.items():
        rendered = []
        for part in parts:
            if isinstance(part, str):
                rendered.append(part)
            else:
                bank, lo, hi, title, instrs = part
                rendered.append(emit_carve(rom, bank, lo, hi, title,
                                           instrs))
        with open(outfile, "w") as f:
            f.write("\n".join(rendered))
        print(f"wrote {outfile} ({sum(len(p) for p in rendered)} bytes)")


if __name__ == "__main__":
    main()
