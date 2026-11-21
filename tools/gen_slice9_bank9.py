#!/usr/bin/env python3
"""Slice 9 generator: bank 9 ($09) object dispatch + handlers.

The $db15 object table: 32 records, STRIDE 16 (slice 8 said 15 -- wrong;
the addend is $0f but the loop consumes byte 0 first, so records are 16
bytes apart: $db15-$dd14). Proof: bank-9 helper $63f3 computes
HL = $db15 + [$c70d]*16 (add a, four times). Record layout (from the two
bank-0 scans + handler prologues):
  [+0] active flag (0 = skip)
  [+1] type/state byte; handlers fire when >= $30
  [+2] per-frame counter (inc'd by both scans)
  [+3..+15] handler data (13 bytes; handlers read [+3..] as pointers,
    positions, counters -- see the carved code)

Two bank-0 scans call bank-9 $4000 with A = byte1 - $30:
  $0bff (called from $0862, the per-frame object update in state-16
    timers 3/5/7/9): any byte1 >= $30 dispatches.
  $0a4f (called from state-16 timer 20, $0a0c): only byte1 in
    [$30,$34) or [$3c,$40) dispatches, i.e. A in {0,1,2,3,12,13,14,15}.
    Entry 7 (A=7, byte1=$37) fires ONLY from the $0bff scan.
Bank-9 $4000 is `rst $08` with a 16-entry table:
  0 $418b, 1 $41f2, 2 $4259, 3 $4292, 4 $4657, 5 $42cb,
  6 $1d29, 7 $46a4, 8-11 $1d29 (bank-0 `ret` -- a no-op; entry 7 is the
    only live handler in 6-11),
  12 $432b, 13 $439c, 14 $440d, 15 $444d.
gb_rd's rst-$08 reader stops at entry 6 (it rejects ROM0 addresses), so
the $4000 span is emitted by hand from the ROM bytes (16 dw entries);
the generator asserts the table bytes match.

Spans carved (walk seeds = the 10 live table entries + 4 hand-seeded
routines $448d/$44ed/$4592/$4635, same handler family -- `call $63f3`
prologue -- but with NO direct caller found anywhere in the ROM, so
their entry mechanism is unverified; they may be reached via a computed
jump or a second dispatch table not yet found):
  $4000-$4021 (rst $08 + 16-entry table)
  $418b-$4691 (all handlers, one contiguous span)
  $63f3-$6402 ($63f3 = record-pointer helper, HL = $db15 + idx*16)
  $6480-$6485 ($6480 = dec [$da4a]; ret)
Gap $4021-$418a decodes as garbage (repeating add hl,hl / dec e) --
data, stays INCBIN.

Outputs: src/bank9.asm. Regenerate with:
  python3 tools/gen_slice9_bank9.py
then update tools/gen_banks.py CARVED (add 9: [...]), regenerate
src/banks.asm, add INCLUDE "bank9.asm" to src/main.asm, and rebuild
(byte-match arbitrates).
"""
import re
import sys

sys.path.insert(0, "tools")
from gb_rd import walk, file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
BANK9 = 9
SEEDS9 = [0x418B, 0x41F2, 0x4259, 0x4292, 0x4657, 0x42CB,
          0x432B, 0x439C, 0x440D, 0x444D, 0x46A4,
          0x448D, 0x44ED, 0x4592, 0x4635]
SPANS9 = [(0x4000, 0x4021), (0x418B, 0x4691),
          (0x63F3, 0x6402), (0x6480, 0x6485)]
# The 16-entry rst-$08 table at $4001, read straight from the ROM.
TABLE9 = [0x418B, 0x41F2, 0x4259, 0x4292, 0x4657, 0x42CB,
          0x1D29, 0x46A4, 0x1D29, 0x1D29, 0x1D29, 0x1D29,
          0x432B, 0x439C, 0x440D, 0x444D]
LABELS9 = {
    0x4000: "Bank9_Dispatch4000",
    0x418B: "Bank9_Obj0_418B",    # table entry 0
    0x41F2: "Bank9_Obj1_41F2",    # table entry 1
    0x4259: "Bank9_Obj2_4259",    # table entry 2
    0x4292: "Bank9_Obj3_4292",    # table entry 3
    0x4657: "Bank9_Obj4_4657",    # table entry 4
    0x42CB: "Bank9_Obj5_42CB",    # table entry 5
    0x46A4: "Bank9_Obj7_46A4",    # table entry 7 (only live entry in 6-11)
    0x432B: "Bank9_Obj12_432B",   # table entry 12
    0x439C: "Bank9_Obj13_439C",   # table entry 13
    0x440D: "Bank9_Obj14_440D",   # table entry 14
    0x444D: "Bank9_Obj15_444D",   # table entry 15
    0x448D: "Bank9_448D",         # entry mechanism unverified
    0x44ED: "Bank9_44ED",         # entry mechanism unverified
    0x4592: "Bank9_4592",         # entry mechanism unverified
    0x4635: "Bank9_4635",         # entry mechanism unverified
    0x63F3: "Bank9_RecordPtr",    # HL = $db15 + [$c70d]*16
    0x6480: "Bank9_DecDa4a",      # dec [$da4a]; ret
}


def jr_label9(tgt):
    return f"jr_009_{tgt:04x}"


def jr_targets9(instrs, lo, hi):
    out = set()
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
            out.add(tgt)
    return out


def fmt_instr9(addr, text, kind, tgt, lo, hi, jr_targets):
    if addr in LABELS9:
        label = f"{LABELS9[addr]}::"
    elif addr in jr_targets:
        label = f"{jr_label9(addr)}:"
    else:
        label = None
    if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
        tgt_label = LABELS9.get(tgt, jr_label9(tgt))
        text = re.sub(r"\$[0-9a-f]{4}$", tgt_label, text)
    line = f"    {text:<48} ; ${addr:04x}"
    return (label + "\n" + line) if label else line


def emit_bank9(rom):
    instrs, rst08, notes = walk(BANK9, SEEDS9)
    # Validate: every in-span control-flow target must be a decoded
    # instruction, and every rst-$08 entry must be decoded (except the
    # $1d29 no-op entries, which live in bank 0).
    for lo, hi in SPANS9:
        for addr, (ln, text, kind, tgt) in instrs.items():
            if kind in ("call", "jump", "jr") and isinstance(tgt, int) \
                    and lo <= tgt < hi and tgt not in instrs:
                print(f"ERROR: ${addr:04x} {text} targets ${tgt:04x}, "
                      f"not a decoded instruction", file=sys.stderr)
                sys.exit(1)
    # Assert the hand-emitted table matches the ROM bytes.
    off = file_off(BANK9, 0x4001)
    for i, w in enumerate(TABLE9):
        got = rom[off + 2 * i] | (rom[off + 2 * i + 1] << 8)
        assert got == w, f"table entry {i}: ROM ${got:04x} != ${w:04x}"
    assert rom[file_off(BANK9, 0x4000)] == 0xCF, "$4000 is not rst $08"
    out = ["; Slice 9: Bank $09 -- the $db15 object dispatch + handlers.",
           "; $4000 is rst $08 with a 16-entry table (entries 6, 8-11 are",
           "; $1d29, the bank-0 `ret` -- a no-op; entry 7 is $46a4).",
           "; Callers: bank-0 $0bff",
           "; (per-frame, state-16 timers 3/5/7/9 via $0862) and $0a4f",
           "; (state-16 timer 20, filtered to A in {0..3,12..15}).",
           "; $63f3 computes HL = $db15 + [$c70d]*16, proving the record",
           "; stride is 16 (slice 8's 'stride 15' was the loop addend).",
           "; $448d/$44ed/$4592/$4635 share the handler prologue but have",
           "; no direct caller in the ROM -- entry mechanism unverified.",
           "; Generated by tools/gen_slice9_bank9.py via tools/gb_rd.py.",
           "; Byte-match (`make`) arbitrates."]
    # Span 1: the dispatch table, emitted by hand (gb_rd stops at 6
    # entries because $1d29 is a ROM0 address).
    out.append('SECTION "Bank $09 $4000-$4020 dispatch", ROMX[$4000], BANK[9]')
    out.append("Bank9_Dispatch4000::")
    out.append(f"    {'rst $08':<48} ; $4000")
    for i, w in enumerate(TABLE9):
        note = " ; no-op ($1d29 = bank-0 ret)" if w == 0x1D29 else ""
        out.append(f"    {'dw $%04x' % w:<48} ; entry {i}{note}")
    for lo, hi in SPANS9[1:]:
        out.append(f'SECTION "Bank $09 ${lo:04x}-${hi - 1:04x}", '
                   f'ROMX[${lo:04x}], BANK[{BANK9}]')
        jr_targets = jr_targets9(instrs, lo, hi)
        addr = lo
        while addr < hi:
            if addr in instrs:
                ln, text, kind, tgt = instrs[addr]
                if kind == "rst08":
                    tbl = rst08[addr]
                    out.append(f"    {'rst $08':<48} ; ${addr:04x}")
                    for i, w in enumerate(tbl):
                        out.append(f"    {'dw $%04x' % w:<48} ; entry {i}")
                    addr += 1 + 2 * len(tbl)
                    continue
                out.append(fmt_instr9(addr, text, kind, tgt, lo, hi, jr_targets))
                addr += ln
            else:
                run = []
                while addr < hi and addr not in instrs \
                        and not any(s < addr < s + 1 + 2 * len(t)
                                    for s, t in rst08.items()):
                    run.append(rom[file_off(BANK9, addr)])
                    addr += 1
                if not run:
                    print(f"ERROR: ${addr:04x}: fell into an rst-$08 table "
                          f"outside the rst08 branch", file=sys.stderr)
                    sys.exit(1)
                for j in range(0, len(run), 8):
                    chunk = run[j:j + 8]
                    out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def main():
    rom = open(ROM, "rb").read()
    header = ("; DO NOT HAND-EDIT the code bodies in this file -- regenerate with\n"
              ";   python3 tools/gen_slice9_bank9.py\n"
              "; after changing the generator config. Entry labels and comments\n"
              "; may be added by hand above a generated block, not inside it.\n\n")
    with open("src/bank9.asm", "w") as f:
        f.write(header + emit_bank9(rom))
    print("wrote src/bank9.asm")


if __name__ == "__main__":
    main()
