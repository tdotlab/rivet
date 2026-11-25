#!/usr/bin/env python3
"""Slice-26 generator (part 3): bank 16 ($10, hex) gaps $4000-$4030,
$4044-$4992, $4eb2-$51c7, $59f1-$5a10, $5fd3-$7e02 (10,982 bytes).
Bank 16 is then CLOSED except the $ff padding ($7e03-$7fff), which
stays INCBIN. ($4031-$4043 is already carved in src/banks/bank10.asm as
Bank10_4031 -- this carve skips it.)

Survey: tools/surveys/survey26_bank16.py.

$4000-$4030 + $4044-$413d: entry stub + dispatcher. $4000: jp $4044;
  $4003-$4011 is the fall-through chain `call $43d7; call $45e5;
  call $46a8; call $48c4; call $4928` (then `ld c,$02; call $4993`
  and the $4017-$4043 tail, whose $4031-$4043 part is already
  carved). $4044 reads hStateTimer ($ff90): ==$11 (17) -> $4003
  chain; [$c0a4]==0 -> $4345; [$dd1a]==4 -> $4003; else the
  [$c133]/[$c141] checks -> $409f -> $40b0, which ends in `jp hl`
  through the dw table at $4ebf (index [$dd18]*2). $40bf reads the
  [$ddaa] record pointer (+$0b==$0a, +$10 in {3,4}), sets [$ff91]
  bits, then $40f0 clears $c205 records / $dd72 slots, sets
  hStateTimer=$19 (25), and dispatches again through the $4eb2
  byte table + $413e dw table.
$413e-$4143: 3-entry dw table ($4144, $41db, $41de), read at $4136
  (index = $4eb2[[DE]]*2). $41db/$41de are mid-routine entries
  into the $4144 routine.
$4144-$4353: $413e-table routines. $4144 sets sound-queue bytes
  ([$c856]->[$c836], $03->[$c82d]/[$c835]); $4342 is `jp $4003`;
  $4345 is the second dispatcher ([$c0a5]*2 -> dw table $4354).
$4354-$435b: 4-entry dw table ($435c, $4381, $4394, $43c9), read at
  $434c (index [$c0a5]*2).
$435c-$4449: $4354-table routines, incl. $43d7 (ends reading the
  $444a table at $4442: index from a byte table at $4edd/$4fdd/
  $4fe5, chosen at $442a/$442f/$4434).
$444a-$445b: 9-entry dw table ($4aef, $4460, $4498, $44b7, $44cf,
  $44f3, $4526, $456a, $459f), read at $4442. $445c-$445f are 4
  unaccounted bytes (plain db, honest gap).
$4460-$459d: $444a-table routines. $459e is a lone `ret` ($c9).
$459f-$46b6: $444a entry 9 ($459f) + $45e5 + $46a8 (the [$c21f]
  dispatcher: [$c21f]*2 -> dw table $46b7 at $46af).
$46b7-$46c2: 6-entry dw table ($4aef, $4721, $47ce, $47e0, $482d,
  $484d), read at $46af (index [$c21f]*2).
$46c3-$4720: 94 bytes of small-value data after the $46b7 table;
  no reader pinned (honest gap).
$4721-$4992: $46b7-table routines, incl. $48c4/$4928 ($4003-chain
  targets) and $4889 `call $7dbe`. Ends at $4992; $4993+ is already
  carved (Bank16_4993).
$4eb2-$51c7: byte/dw tables, plain db with labels at the known
  bases: $4eb2 (13-byte table for the $413e dispatch, read at
  $412d), $4ebf (11-entry dw table, $40bf/$4342 only -- index
  [$dd18] 0-10, matching the $0a scan-gate value), $4edd/$4fdd/
  $4fe5 (byte-table bases for the $444a dispatch, read at $4437).
  $4ed5-$4edc (8 bytes) is unaccounted inside the span.
$59f1-$5a10: 32 bytes, ASCII-coincident (`(TeU(TISISeU...`);
  gb_rd from $59f1 walks spuriously into carved code -- data,
  no reader pinned.
$5fd3-$7dbd: 7,659 bytes of dense varied data (242 distinct byte
  values, no 16-byte structure); walks from $5fd3/$6000/$7000/
  $7800 are spurious data-decoding. No reader pinned (honest
  gap). $5fd3-$605d is 139 zero bytes.
$7dbe-$7e02: record-write helper, called from $4889 (`call
  $7dbe`); writes $42/$7b markers, `call $33a7`, builds a record
  at $c7f7, `call $169c`, ends `jp $0e29` (bank-0). $7e02 is the
  last non-$ff byte in the bank; $7e03-$7fff is all $ff (INCBIN).

Door / clear chain: five hStateTimer writes, ALL `ld a,$19` (timer
  25): $4126 (the $40bf routine) and $437c/$438f/$43ae/$43cb (the
  four $4354-table handlers). No write to timer 33 ($21) or 42
  ($2a), no write to hStateTimer from any other value, no write
  to hGameState ($ff8e) or [$c105] anywhere in this carve
  (grep-verified). Timer 25 is State16Table[25] = $09c6 (the
  state-16 queue-advance area), i.e. transition machinery -- the
  bank-16 $4000 entry runs from state-16 call sites -- not a
  stage-clear entry. No live Nacre watch was run: there is no
  33/42 lead to chase.

Regenerate with: python3 tools/generators/gen_slice26_bank16.py
Byte-match (`make`) arbitrates.
"""
import re
import sys

sys.path.insert(0, "tools")
sys.path.insert(0, "tools/generators")
from gb_rd import walk, file_off  # noqa: E402
import gen_slice26  # noqa: E402  (emit_db, byte_at, rdw)

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
OUT = "src/banks/bank16slice26.asm"
BANK = 16

LABELS16 = {
    0x4000: "Bank16_4000", 0x4003: "Bank16_4003", 0x4044: "Bank16_4044",
    0x40BF: "Bank16_40BF", 0x413E: "Bank16_413E", 0x4144: "Bank16_4144",
    0x41DB: "Bank16_41DB", 0x41DE: "Bank16_41DE", 0x4342: "Bank16_4342",
    0x4345: "Bank16_4345", 0x4354: "Bank16_4354", 0x435C: "Bank16_435C",
    0x4381: "Bank16_4381", 0x4394: "Bank16_4394", 0x43C9: "Bank16_43C9",
    0x43D7: "Bank16_43D7", 0x444A: "Bank16_444A", 0x4460: "Bank16_4460",
    0x4498: "Bank16_4498", 0x44B7: "Bank16_44B7", 0x44CF: "Bank16_44CF",
    0x44F3: "Bank16_44F3", 0x4526: "Bank16_4526", 0x456A: "Bank16_456A",
    0x459E: "Bank16_459E", 0x459F: "Bank16_459F", 0x45E5: "Bank16_45E5",
    0x46A8: "Bank16_46A8", 0x46B7: "Bank16_46B7", 0x4721: "Bank16_4721",
    0x47CE: "Bank16_47CE", 0x47E0: "Bank16_47E0", 0x482D: "Bank16_482D",
    0x484D: "Bank16_484D", 0x48C4: "Bank16_48C4", 0x4928: "Bank16_4928",
    0x4EB2: "Bank16_4EB2", 0x4EBF: "Bank16_4EBF", 0x4EDD: "Bank16_4EDD",
    0x4FDD: "Bank16_4FDD", 0x4FE5: "Bank16_4FE5", 0x7DBE: "Bank16_7DBE",
}

# (lo, hi, title, seeds) -- hi inclusive.
CARVES = [
    (0x4000, 0x4030, "Bank 16 $4000-$4030 entry stub",
     [0x4000, 0x40BF]),
    (0x4044, 0x413D, "Bank 16 $4044-$413d dispatcher + $40bf routine",
     [0x4044, 0x40BF]),
    (0x4144, 0x4353, "Bank 16 $4144-$4353 $413e-table routines",
     [0x4144, 0x41DB, 0x41DE, 0x4342, 0x4345]),
    (0x435C, 0x4449, "Bank 16 $435c-$4449 $4354-table routines",
     [0x435C, 0x4381, 0x4394, 0x43C9, 0x43D7]),
    (0x4460, 0x459D, "Bank 16 $4460-$459d $444a-table routines",
     [0x4460, 0x4498, 0x44B7, 0x44CF, 0x44F3, 0x4526, 0x456A]),
    (0x459E, 0x459E, "Bank 16 $459e ret",
     [0x459E]),
    (0x459F, 0x46B6, "Bank 16 $459f-$46b6 $444a-entry-9 + dispatchers",
     [0x459F, 0x45E5, 0x46A8]),
    (0x4721, 0x4992, "Bank 16 $4721-$4992 $46b7-table routines",
     [0x4721, 0x47CE, 0x47E0, 0x482D, 0x484D, 0x48C4, 0x4928]),
    (0x7DBE, 0x7E02, "Bank 16 $7dbe-$7e02 record-write helper",
     [0x7DBE]),
]

# (lo, [expected values], title)
TABLES = [
    (0x413E, [0x4144, 0x41DB, 0x41DE], "Bank 16 $413e $4eb2-table dispatch"),
    (0x4354, [0x435C, 0x4381, 0x4394, 0x43C9], "Bank 16 $4354 [$c0a5] dispatch"),
    (0x444A, [0x4AEF, 0x4460, 0x4498, 0x44B7, 0x44CF, 0x44F3, 0x4526, 0x456A, 0x459F],
     "Bank 16 $444a dispatch"),
    (0x46B7, [0x4AEF, 0x4721, 0x47CE, 0x47E0, 0x482D, 0x484D],
     "Bank 16 $46b7 [$c21f] dispatch"),
]


def jr_targets_in(instrs, lo, hi):
    out = set()
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
            out.add(tgt)
    return out


def fmt_instr(addr, text, kind, tgt, lo, hi, jr_targets):
    if addr in LABELS16:
        label = f"{LABELS16[addr]}::"
    elif addr in jr_targets:
        label = f"jr_{BANK:03x}_{addr:04x}:"
    else:
        label = None
    if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
        tgt_label = LABELS16.get(tgt, f"jr_{BANK:03x}_{tgt:04x}")
        text = re.sub(r"\$[0-9a-f]{4}$", tgt_label, text)
    line = f"    {text:<48} ; ${addr:04x}"
    return (label + "\n" + line) if label else line


def emit_carve(rom, lo, hi, title, instrs):
    out = [f"; Slice 26: {title} -- bank {BANK} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/generators/gen_slice26_bank16.py from the ROM bytes via",
           "; tools/gb_rd.py (recursive descent, not mgbdis' linear",
           "; sweep). Byte-match (`make`) arbitrates.",
           f'SECTION "{title}", ROMX[${lo:04x}], BANK[{BANK}]']
    jr_targets = jr_targets_in(instrs, lo, hi)
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind in ("call", "jump", "jr") and isinstance(tgt, int) \
                and lo <= tgt <= hi and tgt not in instrs:
            print(f"ERROR: bank {BANK} ${addr:04x} {text} targets "
                  f"${tgt:04x}, not a decoded instruction", file=sys.stderr)
            sys.exit(1)
    addr = lo
    while addr <= hi:
        if addr in instrs:
            ln, text, kind, tgt = instrs[addr]
            out.append(fmt_instr(addr, text, kind, tgt, lo, hi, jr_targets))
            addr += ln
        else:
            run = []
            while addr <= hi and addr not in instrs:
                run.append(rom[file_off(BANK, addr)])
                addr += 1
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    return "\n".join(out) + "\n"


def emit_dw_table(rom, lo, expected, title):
    label = LABELS16.get(lo)
    out = [f"; Slice 26: {title} -- bank {BANK} ${lo:04x}-"
           f"${lo + 2 * len(expected) - 1:04x}.",
           "; Generated by tools/generators/gen_slice26_bank16.py; values read straight "
           "from the ROM.",
           f'SECTION "{title}", ROMX[${lo:04x}], BANK[{BANK}]']
    if label:
        out.append(f"{label}::")
    for i, exp in enumerate(expected):
        val = gen_slice26.rdw(rom, BANK, lo + 2 * i)
        assert val == exp, \
            f"bank {BANK} ${lo + 2 * i:04x}: dw ${val:04x} != expected ${exp:04x}"
        out.append(f"    dw ${val:04x}                                         ; ${lo + 2 * i:04x}")
    return "\n".join(out) + "\n"


def main():
    rom = open(ROM, "rb").read()
    out = ["; Slice 26: Bank 16 $4000-$4030, $4044-$4992, $4eb2-$51c7,",
           "; $59f1-$5a10, $5fd3-$7e02. Generated by",
           "; tools/generators/gen_slice26_bank16.py (survey:",
           "; tools/surveys/survey26_bank16.py). Byte-match (`make`) arbitrates."]
    total = 0
    for lo, hi, title, seeds in CARVES:
        reached, rst08, notes = walk(BANK, seeds)
        assert not rst08, f"unexpected rst $08 in ${lo:04x}-${hi:04x}: {rst08}"
        txt = emit_carve(rom, lo, hi, title, reached)
        out.append("")
        out.append(txt.rstrip("\n"))
        total += hi - lo + 1
        print(f"  carve ${lo:04x}-${hi:04x}: {len(reached)} instrs walked")
    for lo, expected, title in TABLES:
        txt = emit_dw_table(rom, lo, expected, title)
        out.append("")
        out.append(txt.rstrip("\n"))
        total += 2 * len(expected)
    # $445c-$445f: 4 unaccounted bytes after the $444a table.
    out.append("")
    out.append("; Slice 26: Bank 16 $445c-$445f (4 bytes after the $444a table).")
    out.append('SECTION "Bank 16 $445c-$445f bytes", ROMX[$445c], BANK[16]')
    lines = []
    gen_slice26.emit_db(lines, rom, BANK, 0x445C, 0x4460)
    out.extend(lines)
    total += 4
    # db spans: (lo, hi, labels, note)
    db_spans = [
        (0x46C3, 0x4721, {}, "94 bytes after the $46b7 table; no reader pinned."),
        (0x4EB2, 0x51C8,
         {0x4EB2: "Bank16_4EB2", 0x4EBF: "Bank16_4EBF", 0x4EDD: "Bank16_4EDD",
          0x4FDD: "Bank16_4FDD", 0x4FE5: "Bank16_4FE5"},
         "$4eb2 byte table / $4ebf dw table / $4edd/$4fdd/$4fe5 byte-table bases."),
        (0x59F1, 0x5A11, {}, "32 bytes, ASCII-coincident; no reader pinned."),
        (0x5FD3, 0x7DBE, {}, "Dense data; no reader pinned. $5fd3-$605d is zeros."),
    ]
    for lo, hi, labels, note in db_spans:
        out.append("")
        out.append(f"; Slice 26: Bank 16 ${lo:04x}-${hi - 1:04x}. {note}")
        out.append(f'SECTION "Bank 16 ${lo:04x}-${hi - 1:04x} data", ROMX[${lo:04x}], BANK[{BANK}]')
        lines = []
        n = gen_slice26.emit_db(lines, rom, BANK, lo, hi, labels)
        assert n == hi - lo, f"db ${lo:04x} emitted {n} != {hi - lo}"
        out.extend(lines)
        total += n
    assert total == 10982, f"total {total} != 10982"
    print(f"bank 16 slice 26: {total} bytes")
    with open(OUT, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
