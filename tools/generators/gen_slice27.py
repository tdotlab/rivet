#!/usr/bin/env python3
"""Slice-27 generator: bank 7 + bank 8 endgame gaps -> src/banks/bank7slice27.asm,
src/banks/bank8slice27.asm. After this slice, banks 7 and 8 are CLOSED except
$ff padding (bank 7 $7f90-$7fff; bank 8 none -- $781a-$7fff is data).

Survey: tools/survey27*.py (esp. survey27f/survey27g walks).

BANK 7 (3,267 B carved; $7f90-$7fff $ff stays INCBIN):
  $6581-$6584 dw table, 2 entries ($6585, $65cd). Reader $6572 (slice 5):
    ld a,[$dd1e]; add a; ld c,a; ld b,$00; ld hl,$6581; add hl,bc;
    ld a,[hl+]; ld h,[hl]; ld l,a; jp hl. 2-entry reading: the bytes
    at $6585+ decode as a coherent routine (ld a,[$0efa]; jp nz,$6f26;
    nop; add hl,hl x5; ...) flowing into the verified $65a3 span, and
    entry 0 ($6585) pointing into its own table would be self-
    referential under a 4-entry reading. [$dd1e] is a 0/1 dispatch.
    (Judgment call; byte-match arbitrates the bytes, the table extent
    is the interpretation.)
  $6585-$664d code, seeds [$6585, $65cd, $662a]. $662a REAL (9 same-bank
    jp z from carved $47xx-$58xx). $6585/$65cd are the table entries.
  $67a1-$67de code, seed $67a1 (bank-7 $4000 call $67a1).
  $67df-$67ee dw table, 8 entries ($67ef, $6b09, $68a5, $688e, $6b09,
    $67fd, $67fd, $67fd). Reader $67d6: ld hl,$67df; add hl,bc;
    ld a,[hl+]; ld h,[hl]; ld l,a; jp hl. Index byte from the $73xx
    data table (DE = $735e/$7364/$735b by record byte $10/$12/$04).
  $67ef-$68ac code, seeds [$67ef, $68a5, $688e, $67fd]. $67fa jp $768a
    and $68a2 jp $771e are real (ld e,c; ld d,b; jp ...). Boundary
    clean: $68ab inc [hl]; $68ac ret; carved $68ad starts ld a,[$dd1b].
  $68c4-$695a data, label $68c4 (table base, ld hl,$68c4 at $68b7).
  $6ed2-$6f05 code, seed $6ed2 (entry-unverified; carved $6ed1 ends
    jp $6f2e, no fall-through). Tail jumps into carved $6f2e-$6f3f.
  $7001-$701a dw table, 13 entries ($701b, $706c, $7068, $708f, $70c2,
    $70e4, $70f0, $701b, $70f0, $70f1, $7107, $7124, $7125). Reader
    $6fe8 (ld c,a; ld b,$00; ld hl,$7001) in the $6f62 dispatch area.
  $701b-$714b code, seeds = the 13 table entries. $706c-$708e calls
    $695b, jp $7128; $7128-$714b verified. $7034/$7065/$70e1/$7121
    jp $7128 are table bytes, not code.
  $71ba-$7509 data, labels at the ld-ptr targets from bank7slice13/
    bank7slice11. $7394 read by the $7169 stage-RAM clear (16-byte
    copy $7394->$dd59).
  $7610-$7688 data ($3f-fill with sparse $7f/$80-$88 markers; $7610 is
    a data base: ld bc,$7610 in bank7.asm $47d4, bank7slice13
    $4971/$56fc). $7689 is a 1-byte `ret` (entry via $6e54 Handler10,
    B=$2e -- $6e54 jp hl lands on it and it returns to the handler's
    caller).
  $768a-$77a8 code, seeds [$768a, $76c5, $771e], 0 uncovered. $768a
    from $67fa jp (VERIFIED). $76c5 record-builder family, entry
    UNVERIFIED (predecessor $76c4 ends jp $169c). $771e entry
    UNVERIFIED: the $7722/$773a/$773d/$7786 "jp z from carved" hits
    do NOT exist in carved bank-7 source (grep) -- they were ROM
    byte-search phantoms in data bytes. $771e's only entry is $68a2
    jp (inside this same gap). $7730 is a bank-10 target, NOT bank 7
    (mid-instruction of call $169c at $772f).
  $7abb-$7d5d code, seeds [$7abb, $7b14, $7b77, $7bda, $7c3d, $7ca0,
    $7d03, $7d15]. THE DOOR FINDING (see below): a family of
    record-builder routines, each ending with a [$c70b] save +
    timer 22. Entries via $6e54 (bank7slice10 handlers jp $6e54 with
    HL=blob; $6e54 ends pop hl; jp hl, so the blobs EXECUTE as code):
      $7b14 Handler02 (B=$10), $7bda Handler04 (B=$18),
      $7c3d Handler08 (B=$26), $7ca0 Handler09 (B=$2a).
    $7abb head and $7b77 entry UNVERIFIED (no cf target in bank 7 or
    bank 0; predecessor $7b74 jp $169c, no fall-through). $7d03 head
    ends ret z, falling through to the $7d15 body (one routine with a
    conditional early return). $7d15 body reads the $7f28 table.
  $7e18-$7ed2 code, seeds [$7e18, $7e43, $7e55, $7e67, $7e79, $7ecb].
    $7e18 record-builder, called from the $7e43/$7e55/$7e67 blobs
    (call $7e18 -- REAL, the blobs execute via $6e54). $7e43/$7e55/
    $7e67 are routines (ld h,d; ld l,e; ld a,$37/$38/$39;
    ld [$c82f],a; ld [$c835],a; call $7e18; ld a,$01/$02/$03;
    jp $0df4), entered via $6e54 (Handlers 14/15/16, B=$3e/$42/$46).
    $7e79 big routine via $6e54 (Handler13, B=$3a); writes [$c70c].
    $7e3f-$7e42 is the $7e18 routine's tail (pop de; jp $169c), NOT
    a separate head (earlier mis-index corrected by the walk).
    $7ecb entry UNVERIFIED (the $7e22/$7ecb "jp from carved" hits do
    NOT exist in carved bank-7 source -- ROM byte-search phantoms).
  $7ed3-$7edc data, label $7ed3 (read by bank7.asm and by the $76c5/
    $7abb/$7d03 record-builders: ld hl,$7ed3; ld d,$00; ld e,a;
    add hl,de; ld a,[$d99a]; add [hl]; ld [$c809],a).
  $7f0d-$7f8f data (dw-table-like pattern, no reader pinned).
    $7f90-$7fff all $ff stays INCBIN.

BANK 8 (6,395 B):
  $5809-$5904 data (252 B = 63 x 4-byte class records, continuing the
    $5409-$5808 class-record table; $5409 + 256*4 = $5809 exactly.
    No reader pinned for $5809+; plain db).
  $5905-$5e36 code, seeds [$5905, $5962, $59cb, $5a32, $5a5e, $5ab4,
    $5bec, $5c51, $5c9e, $5d07, $5d59, $5e1b]. The $5905 family:
    11 parallel position-math routines (ld hl,$dd98; xor a;
    ld [hl+],a x5; ...; ld [$c1f3]/[$c1f4]/[$c1f5]/[$c1f6],a),
    ending ldh a,[$ff8d]; jp $0fe5 (bank-switch return) or
    jp $5e1b (shared tail). 8 entries verified via the bank-0 $2a0a
    dispatch tail ($5a5e/$5ab4/$5905/$5962/$59cb/$5a32/$5c51/$5d07).
    $5bec/$5c9e/$5d59 entry UNVERIFIED (no $2a-tail/table/cf entry),
    but $5bec ends jp $5d59 (internal link) and all three decode as
    perfect family members.
  $611f-$612c dw table, 7 entries ($6473, $612d, $609d, $7310, $63b5,
    $6646, $63f0). Reader $6117 (ld c,a; ld b,$00; ld hl,$611f).
    $7310 is the shared sentinel (also $6283/$6a34 tables).
  $612d-$6273 code, seeds [$612d, $61dc]. $61dc-$6273 one span
    (ret $61ef; $61f0 calls the $2afd trampoline; $6221 ld hl,$77a6).
  $6283-$6290 dw table, 7 entries ($7310, $6291, $6360, $6386, $63b5,
    $7310, $63f0). Reader $627b. NOTE: the walk's "$6290: ld h,e" is
    a MISALIGNED decode of the $63f0 high byte; real code starts
    $6291 (call $2acd). Same for $612c (misaligned $63f0 high byte).
  $6291-$63b4 code, seed $6291.
  $6669-$67aa code, seeds [$6669, $66fd]; db $67ab-$67bc (18 B).
    $66fd countdown helper, targeted from $6670/$6675/$667a/$67a8.
    Entry into $6669 UNVERIFIED ($6668 is a 1-byte ret).
  $67cc-$68b7 code, seed $67cc (table base, ld hl,$67cc at $67c4).
  $68ef-$69ae code, seeds [$68ef, $6902]; db $68f6-$68fb (6 B).
    $6902 from same-bank $69ac jp (inside gap, circular).
  $69be-$6a24 code, seed $69be; db $6a02-$6a05 (4 B). Entry
    UNVERIFIED (ld-ptr $69be only; walk starts jp nz,$0269).
    $768e-$76e2 also reached from the $72cd call.
  $6a34-$6a3b dw table, 4 entries ($7310, $6a3c, $6a57, $6aa7).
    Reader $6a2c. $6a57-$6a58 is ld a,[$c0f8] (NOT a 3-byte gap:
    the walk's "$6a59: ret nz" was the misaligned low byte $c0).
  $6a3c-$6aba code, seeds [$6a3c, $6a57, $6a8b, $6aa7].
  $6aca-$6ad5 dw table, 6 entries ($6ad6, $6b7c, $6ba1, $6cc5, $6d16,
    $6d20). Reader $6ac2. $6ba1/$6d16 are TABLE ENTRIES (code starts
    there), not data pockets -- the earlier "uncovered" reading was
    the walk missing the table seeds.
  $6ad6-$6d89 code, seeds = the 6 table entries. $6b32/$6b85 entries
    are FALSE for bank 8 (bank-16 targets); the bank-8 bytes there
    decode as code reached by post-ret/jp only -- entry UNVERIFIED.
    $6b77 "entry" is DISPROVED: raw bytes $6b70-$6b80 are
    sub [hl]; ld a,$19; ld [$c0f9],a; ld a,$03; ld [$c10a],a; ret;
    $6b77 is the $03 operand byte, not an instruction.
  $7292-$730f code, seeds [$7292, $72a9, $72d3] (from $6a75/$6a7d/
    $6a80/$6bbf/$6bc7/$6bca -- inside the $6aca spans, circular).
  $74f4-$7525 code, seed $74f4 (from $6d13/$6d87 jp).
  $7588-$7601 code, seeds [$7588, $75e5]. $7588 VERIFIED (bank-0
    $08d2 call, bank 8 mapped). $75e5 routine entry UNVERIFIED;
    it contains a $75f6 self-loop trap (jr $75f6) when its inner
    scan exhausts E without finding a zero byte.
  $762a-$7684 code, seeds [$762a, $765d].
  $76b6-$76e2 code, seed $76b6 (from $68ad/$69fc calls).
  $781a-$7fff data (2,022 B). NO verified entries: every bank-0 hit
    is a phantom or an other-bank target ($78ba->bank 7, $7909/
    $790d phantoms, $7ae5/$7b6c/$7c57/$7c88/$7cb0->bank 10,
    $7e35 phantom, $7e44->bank 31; same-bank $7e09/$7ee5 phantoms
    straddling ld hl,$c200/$c220). Walks from those seeds are
    spurious. Plain db, no labels.

DOOR / CLEAR CHAIN -- THE HEADLINE:
  The $7abb-$7d5d carve adds FIVE [$c70b] writers (the [$c70b] list
  grows 6 -> 11). Each saves hStateTimer into [$c70b] and sets
  timer 22 ($16):
    $7b6e (in the $7b14 routine, entered via $6e54 Handler02),
    $7c34, $7c97, $7cfa (in the $7bda-$7d02 span, entered via $6e54
    Handlers 04/08/09 at $7bda/$7c3d/$7ca0),
    $7bcc (in the $7b77 routine, entry UNVERIFIED).
  These are the CLEAR-CHAIN ENTRIES slice 24 was missing: the
  $75ea interaction handlers (bank7slice10) invoke them through
  $6e54 when Mario interacts with a tile, and they set timer 22 --
  the clear-chain timer whose entry was the open question. The
  $7e79 routine writes [$c70c] (not $c70b) -- adjacent, same family.
  The $0859 gate (State16Table[6], bank-0 $0859) is a SEPARATE
  mechanism: it saves the timer and sets timer 41 when the player
  presses Select/Start (hJoypadNew & $0c) on a state-16/18 timer-6
  frame, with [$da4b]!=$21 and ($c712!=0 or $c711!=1). Live test
  (gb_pcwatch) is a separate step after the build; see PROGRESS.md.

Run: python3 tools/generators/gen_slice27.py
"""
import re
import sys

sys.path.insert(0, "tools")
sys.path.insert(0, "tools/generators")
import gen_slice26  # noqa: E402
from gb_rd import file_off, walk  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()
RET_OPS = {0xC9, 0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8}


def post_ret(bank, lo, hi):
    b = rom[bank * 0x4000:(bank + 1) * 0x4000]
    return [a + 1 for a in range(lo, hi - 1) if b[a - 0x4000] in RET_OPS]


def walk_region(bank, lo, hi, seeds):
    """Walk with post-ret seeds first (processed last), verified
    seeds last (processed first). Returns (instrs, uncovered list)."""
    allseeds = post_ret(bank, lo, hi) + seeds
    reached, rst08, notes = walk(bank, allseeds)
    assert not rst08, f"bank {bank} ${lo:04x}: unexpected rst $08: {rst08}"
    cov = set()
    for a, (ln, _, _, _) in reached.items():
        cov.update(range(a, a + ln))
    uncov = []
    cur = None
    for x in range(lo, hi + 1):
        if x not in cov:
            cur = [x, x] if cur is None else [cur[0], x]
        elif cur:
            uncov.append(tuple(cur)); cur = None
    if cur:
        uncov.append(tuple(cur))
    return reached, uncov


def jr_targets_in(instrs, lo, hi):
    out = set()
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
            out.add(tgt)
    return out


def fmt_instr(addr, text, kind, tgt, lo, hi, jr_targets, labels, bank):
    if addr in labels:
        label = f"{labels[addr]}::"
    elif addr in jr_targets:
        label = f"jr_{bank:03x}_{addr:04x}:"
    else:
        label = None
    if kind == "jr" and isinstance(tgt, int) and lo <= tgt <= hi:
        tgt_label = labels.get(tgt, f"jr_{bank:03x}_{tgt:04x}")
        text = re.sub(r"\$[0-9a-f]{4}$", tgt_label, text)
    line = f"    {text:<48} ; ${addr:04x}"
    return (label + "\n" + line) if label else line


def emit_carve(rom, bank, lo, hi, title, instrs, labels, expect_db=()):
    """Emit a code region; uncovered bytes become db, but ONLY at the
    expected addresses (anything else is a generator error)."""
    jr_targets = jr_targets_in(instrs, lo, hi)
    for addr, (ln, text, kind, tgt) in instrs.items():
        if kind in ("call", "jump", "jr") and isinstance(tgt, int) \
                and lo <= tgt <= hi and tgt not in instrs:
            print(f"ERROR: bank {bank} ${addr:04x} {text} targets "
                  f"${tgt:04x}, not a decoded instruction", file=sys.stderr)
            sys.exit(1)
    out = [f"; Slice 27: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/generators/gen_slice27.py from the ROM bytes via",
           "; tools/gb_rd.py (recursive descent, not mgbdis' linear",
           "; sweep). Byte-match (`make`) arbitrates.",
           f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]']
    db_addrs = set()
    addr = lo
    while addr <= hi:
        if addr in instrs:
            ln, text, kind, tgt = instrs[addr]
            out.append(fmt_instr(addr, text, kind, tgt, lo, hi,
                                 jr_targets, labels, bank))
            addr += ln
        else:
            run = []
            while addr <= hi and addr not in instrs:
                run.append(rom[file_off(bank, addr)])
                db_addrs.add(addr)
                addr += 1
            for j in range(0, len(run), 8):
                chunk = run[j:j + 8]
                out.append("    db " + ", ".join(f"${b:02x}" for b in chunk))
    expect = {x for a, b in expect_db for x in range(a, b + 1)}
    assert db_addrs == expect, (
        f"bank {bank} ${lo:04x}-${hi:04x}: db bytes "
        f"{sorted(db_addrs - expect)} unexpected, "
        f"{sorted(expect - db_addrs)} missing")
    return "\n".join(out) + "\n"


def emit_dw(bank, lo, entries, title, comment=""):
    out = [f"; Slice 27: {title} -- bank {bank} ${lo:04x}-${lo + 2 * len(entries) - 1:04x}.",
           "; Generated by tools/generators/gen_slice27.py. Byte-match arbitrates."]
    if comment:
        out.append(f"; {comment}")
    out.append(f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]')
    for i, e in enumerate(entries):
        out.append(f"    dw ${e:04x}                                    ; ${lo + 2 * i:04x}")
    return "\n".join(out) + "\n"


def emit_data(rom, bank, lo, hi, title, labels, comment=""):
    out = [f"; Slice 27: {title} -- bank {bank} ${lo:04x}-${hi:04x}."]
    if comment:
        out.append(f"; {comment}")
    out.append("; Generated by tools/generators/gen_slice27.py. Byte-match arbitrates.")
    out.append(f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]')
    lines = []
    n = gen_slice26.emit_db(lines, rom, bank, lo, hi + 1, labels)
    assert n == hi - lo + 1, f"db ${lo:04x} emitted {n}"
    out.extend(lines)
    return "\n".join(out) + "\n"


def code_region(out, rom, bank, lo, hi, title, seeds, labels, expect_db=()):
    instrs, uncov = walk_region(bank, lo, hi, seeds)
    expect = [(a, b) for a, b in expect_db]
    assert sorted(uncov) == sorted(expect), (
        f"bank {bank} ${lo:04x}-${hi:04x}: uncovered "
        f"{[(hex(a), hex(b)) for a, b in uncov]} != expected "
        f"{[(hex(a), hex(b)) for a, b in expect]}")
    print(f"  bank {bank} ${lo:04x}-${hi:04x}: {len(instrs)} instrs, "
          f"uncovered {uncov}")
    out.append("")
    out.append(emit_carve(rom, bank, lo, hi, title, instrs, labels,
                          expect_db).rstrip("\n"))
    return hi - lo + 1


def L(bank, addrs):
    return {a: f"Bank{bank}_{a:04X}" for a in addrs}


def build_bank7():
    out = ["; Slice 27: Bank 7 endgame gaps (3,779 bytes).",
           "; Generated by tools/generators/gen_slice27.py (survey: tools/survey27*.py).",
           "; Byte-match (`make`) arbitrates."]
    total = 0
    # $6581-$6584 dw table
    out.append("")
    out.append(emit_dw(7, 0x6581, [0x6585, 0x65CD],
                       "Bank 7 $6581 jump table",
                       "Reader $6572: ld a,[$dd1e]; add a; ld c,a; ld b,$00; "
                       "ld hl,$6581; add hl,bc; ld a,[hl+]; ld h,[hl]; "
                       "ld l,a; jp hl. 2-entry reading (see gen header).").rstrip("\n"))
    total += 4
    # $6585-$664d code
    total += code_region(out, rom, 7, 0x6585, 0x664D,
                         "Bank 7 $6585-$664d routines",
                         [0x6585, 0x65CD, 0x662A],
                         L(7, [0x6585, 0x65CD, 0x662A]))
    # $67a1-$67de code
    total += code_region(out, rom, 7, 0x67A1, 0x67DE,
                         "Bank 7 $67a1-$67de routine",
                         [0x67A1], L(7, [0x67A1]))
    # $67df-$67ee dw table
    out.append("")
    out.append(emit_dw(7, 0x67DF, [0x67EF, 0x6B09, 0x68A5, 0x688E,
                                   0x6B09, 0x67FD, 0x67FD, 0x67FD],
                       "Bank 7 $67df jump table",
                       "Reader $67d6: ld hl,$67df; add hl,bc; ld a,[hl+]; "
                       "ld h,[hl]; ld l,a; jp hl. Index from the $73xx "
                       "data table.").rstrip("\n"))
    total += 16
    # $67ef-$68ac code
    total += code_region(out, rom, 7, 0x67EF, 0x68AC,
                         "Bank 7 $67ef-$68ac routines",
                         [0x67EF, 0x68A5, 0x688E, 0x67FD],
                         L(7, [0x67EF, 0x68A5, 0x688E, 0x67FD]))
    # $68c4-$695a data
    out.append("")
    out.append(emit_data(rom, 7, 0x68C4, 0x695A,
                         "Bank 7 $68c4-$695a data",
                         {0x68C4: "Bank7_68C4"},
                         "Table base (ld hl,$68c4 at $68b7: ld c,a; "
                         "ld b,$00).").rstrip("\n"))
    total += 0x695B - 0x68C4
    # $6ed2-$6f05 code
    total += code_region(out, rom, 7, 0x6ED2, 0x6F05,
                         "Bank 7 $6ed2-$6f05 routine",
                         [0x6ED2], L(7, [0x6ED2]))
    # $7001-$701a dw table
    out.append("")
    out.append(emit_dw(7, 0x7001, [0x701B, 0x706C, 0x7068, 0x708F, 0x70C2,
                                   0x70E4, 0x70F0, 0x701B, 0x70F0, 0x70F1,
                                   0x7107, 0x7124, 0x7125],
                       "Bank 7 $7001 jump table",
                       "Reader $6fe8 (ld c,a; ld b,$00; ld hl,$7001) in "
                       "the $6f62 dispatch area.").rstrip("\n"))
    total += 26
    # $701b-$714b code
    total += code_region(out, rom, 7, 0x701B, 0x714B,
                         "Bank 7 $701b-$714b routines",
                         [0x701B, 0x706C, 0x7068, 0x708F, 0x70C2, 0x70E4,
                          0x70F0, 0x70F1, 0x7107, 0x7124, 0x7125],
                         L(7, [0x701B, 0x706C, 0x7068, 0x708F, 0x70C2,
                               0x70E4, 0x70F0, 0x70F1, 0x7107, 0x7124,
                               0x7125]))
    # $71ba-$7509 data
    data71 = [0x71BA, 0x71C9, 0x71D8, 0x71DF, 0x71E7, 0x7223, 0x725F,
              0x7261, 0x7263, 0x733B, 0x733F, 0x7343, 0x734B, 0x7353,
              0x7357, 0x7394, 0x73B4, 0x73D4, 0x73E4, 0x73F4, 0x7404,
              0x7416, 0x7422, 0x742C, 0x7474, 0x74BC, 0x74C4, 0x74D4,
              0x74EC, 0x74EE, 0x74F2]
    out.append("")
    out.append(emit_data(rom, 7, 0x71BA, 0x7509,
                         "Bank 7 $71ba-$7509 data",
                         L(7, data71),
                         "$7394 read by the $7169 stage-RAM clear "
                         "(16-byte copy $7394->$dd59).").rstrip("\n"))
    total += 0x750A - 0x71BA
    # $7610-$7688 data
    out.append("")
    out.append(emit_data(rom, 7, 0x7610, 0x7688,
                         "Bank 7 $7610-$7688 data",
                         {0x7610: "Bank7_7610"},
                         "$3f-fill with sparse $7f/$80-$88 markers; "
                         "$7610 is a data base (ld bc,$7610).").rstrip("\n"))
    total += 0x7689 - 0x7610
    # $7689 ret
    out.append("")
    out.append("; Slice 27: Bank 7 $7689 -- 1-byte ret, entry via $6e54 "
               "Handler10 (B=$2e); $6e54 jp hl lands here and it returns "
               "to the handler's caller.")
    out.append('SECTION "Bank 7 $7689 ret", ROMX[$7689], BANK[7]')
    out.append("Bank7_7689::")
    out.append("    ret                                              ; $7689")
    total += 1
    # $768a-$77a8 code
    total += code_region(out, rom, 7, 0x768A, 0x77A8,
                         "Bank 7 $768a-$77a8 record builders",
                         [0x768A, 0x76C5, 0x771E],
                         L(7, [0x768A, 0x76C5, 0x771E]))
    # $7abb-$7d5d code (door: [$c70b] save + timer 22 family)
    total += code_region(out, rom, 7, 0x7ABB, 0x7D5D,
                         "Bank 7 $7abb-$7d5d record builders [$c70b] save + timer 22",
                         [0x7ABB, 0x7B14, 0x7B77, 0x7BDA, 0x7C3D, 0x7CA0,
                          0x7D03, 0x7D15],
                         L(7, [0x7ABB, 0x7B14, 0x7B77, 0x7BDA, 0x7C3D,
                               0x7CA0, 0x7D03, 0x7D15]))
    # $7e18-$7ed2 code
    total += code_region(out, rom, 7, 0x7E18, 0x7ED2,
                         "Bank 7 $7e18-$7ed2 record builders",
                         [0x7E18, 0x7E43, 0x7E55, 0x7E67, 0x7E79, 0x7ECB],
                         L(7, [0x7E18, 0x7E43, 0x7E55, 0x7E67, 0x7E79,
                               0x7ECB]))
    # $7ed3-$7edc data
    out.append("")
    out.append(emit_data(rom, 7, 0x7ED3, 0x7EDC,
                         "Bank 7 $7ed3-$7edc data",
                         {0x7ED3: "Bank7_7ED3"},
                         "Read by the $76c5/$7abb/$7d03 record-builders "
                         "(ld hl,$7ed3; ld d,$00; ld e,a; add hl,de; "
                         "ld a,[$d99a]; add [hl]; ld [$c809],a) and by "
                         "bank7.asm.").rstrip("\n"))
    total += 0x7EDD - 0x7ED3
    # $7f0d-$7f8f data
    out.append("")
    out.append(emit_data(rom, 7, 0x7F0D, 0x7F8F,
                         "Bank 7 $7f0d-$7f8f data",
                         {},
                         "dw-table-like pattern (dw $5210, $0011, $0000, "
                         "$5200, ... then $18xx then $15xx); no reader "
                         "pinned. $7f90-$7fff all $ff stays INCBIN.").rstrip("\n"))
    total += 0x7F90 - 0x7F0D
    assert total == 3267, f"bank 7 total {total} != 3267"
    print(f"bank 7 slice 27: {total} bytes")
    with open("src/banks/bank7slice27.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print("wrote src/banks/bank7slice27.asm")


def build_bank8():
    out = ["; Slice 27: Bank 8 endgame gaps (6,395 bytes).",
           "; Generated by tools/generators/gen_slice27.py (survey: tools/survey27*.py).",
           "; Byte-match (`make`) arbitrates."]
    total = 0
    # $5809-$5904 data
    out.append("")
    out.append(emit_data(rom, 8, 0x5809, 0x5904,
                         "Bank 8 $5809-$5904 data",
                         {},
                         "63 x 4-byte class records, continuing the "
                         "$5409-$5808 table ($5409 + 256*4 = $5809). No "
                         "reader pinned for $5809+.").rstrip("\n"))
    total += 0x5905 - 0x5809
    # $5905-$5e36 code
    total += code_region(out, rom, 8, 0x5905, 0x5E36,
                         "Bank 8 $5905-$5e36 position-math routines",
                         [0x5905, 0x5962, 0x59CB, 0x5A32, 0x5A5E, 0x5AB4,
                          0x5BEC, 0x5C51, 0x5C9E, 0x5D07, 0x5D59, 0x5E1B],
                         L(8, [0x5905, 0x5962, 0x59CB, 0x5A32, 0x5A5E,
                               0x5AB4, 0x5BEC, 0x5C51, 0x5C9E, 0x5D07,
                               0x5D59, 0x5E1B]))
    # $611f-$612c dw table
    out.append("")
    out.append(emit_dw(8, 0x611F, [0x6473, 0x612D, 0x609D, 0x7310, 0x63B5,
                                   0x6646, 0x63F0],
                       "Bank 8 $611f jump table",
                       "Reader $6117 (ld c,a; ld b,$00; ld hl,$611f). "
                       "$7310 is the shared sentinel.").rstrip("\n"))
    total += 14
    # $612d-$6273 code
    total += code_region(out, rom, 8, 0x612D, 0x6273,
                         "Bank 8 $612d-$6273 routines",
                         [0x612D, 0x61DC], L(8, [0x612D, 0x61DC]))
    # $6283-$6290 dw table
    out.append("")
    out.append(emit_dw(8, 0x6283, [0x7310, 0x6291, 0x6360, 0x6386, 0x63B5,
                                   0x7310, 0x63F0],
                       "Bank 8 $6283 jump table",
                       "Reader $627b. NOTE: the walk's \"$6290: ld h,e\" "
                       "is a misaligned decode of the $63f0 high byte; "
                       "real code starts $6291.").rstrip("\n"))
    total += 14
    # $6291-$63b4 code
    total += code_region(out, rom, 8, 0x6291, 0x63B4,
                         "Bank 8 $6291-$63b4 routines",
                         [0x6291], L(8, [0x6291]))
    # $6669-$67aa code + db $67ab-$67bc
    total += code_region(out, rom, 8, 0x6669, 0x67BC,
                         "Bank 8 $6669-$67bc routines",
                         [0x6669, 0x66FD],
                         L(8, [0x6669, 0x66FD]),
                         expect_db=[(0x67AB, 0x67BC)])
    # $67cc-$68b7 code
    total += code_region(out, rom, 8, 0x67CC, 0x68B7,
                         "Bank 8 $67cc-$68b7 routines",
                         [0x67CC], L(8, [0x67CC]))
    # $68ef-$69ae code + db $68f6-$68fb
    total += code_region(out, rom, 8, 0x68EF, 0x69AE,
                         "Bank 8 $68ef-$69ae routines",
                         [0x68EF, 0x6902],
                         L(8, [0x68EF, 0x6902]),
                         expect_db=[(0x68F6, 0x68FA)])
    # $69be-$6a24 code + db $6a02-$6a05
    total += code_region(out, rom, 8, 0x69BE, 0x6A24,
                         "Bank 8 $69be-$6a24 routines",
                         [0x69BE], L(8, [0x69BE]),
                         expect_db=[(0x6A02, 0x6A04)])
    # $6a34-$6a3b dw table
    out.append("")
    out.append(emit_dw(8, 0x6A34, [0x7310, 0x6A3C, 0x6A57, 0x6AA7],
                       "Bank 8 $6a34 jump table",
                       "Reader $6a2c. $6a57-$6a58 is ld a,[$c0f8] (the "
                       "walk's \"$6a59: ret nz\" was the misaligned "
                       "low byte $c0).").rstrip("\n"))
    total += 8
    # $6a3c-$6aba code
    total += code_region(out, rom, 8, 0x6A3C, 0x6ABA,
                         "Bank 8 $6a3c-$6aba routines",
                         [0x6A3C, 0x6A57, 0x6A8B, 0x6AA7],
                         L(8, [0x6A3C, 0x6A57, 0x6A8B, 0x6AA7]))
    # $6aca-$6ad5 dw table
    out.append("")
    out.append(emit_dw(8, 0x6ACA, [0x6AD6, 0x6B7C, 0x6BA1, 0x6CC5, 0x6D16,
                                   0x6D20],
                       "Bank 8 $6aca jump table",
                       "Reader $6ac2. $6ba1/$6d16 are table entries "
                       "(code starts there), not data pockets.").rstrip("\n"))
    total += 12
    # $6ad6-$6d89 code
    total += code_region(out, rom, 8, 0x6AD6, 0x6D89,
                         "Bank 8 $6ad6-$6d89 routines",
                         [0x6AD6, 0x6B7C, 0x6BA1, 0x6CC5, 0x6D16, 0x6D20],
                         L(8, [0x6AD6, 0x6B7C, 0x6BA1, 0x6CC5, 0x6D16,
                               0x6D20]))
    # $7292-$730f code
    total += code_region(out, rom, 8, 0x7292, 0x730F,
                         "Bank 8 $7292-$730f routines",
                         [0x7292, 0x72A9, 0x72D3],
                         L(8, [0x7292, 0x72A9, 0x72D3]))
    # $74f4-$7525 code
    total += code_region(out, rom, 8, 0x74F4, 0x7525,
                         "Bank 8 $74f4-$7525 routines",
                         [0x74F4], L(8, [0x74F4]))
    # $7588-$7601 code
    total += code_region(out, rom, 8, 0x7588, 0x7601,
                         "Bank 8 $7588-$7601 routines",
                         [0x7588, 0x75E5],
                         L(8, [0x7588, 0x75E5]))
    # $762a-$7684 code
    total += code_region(out, rom, 8, 0x762A, 0x7684,
                         "Bank 8 $762a-$7684 routines",
                         [0x762A, 0x765D],
                         L(8, [0x762A, 0x765D]))
    # $76b6-$76e2 code
    total += code_region(out, rom, 8, 0x76B6, 0x76E2,
                         "Bank 8 $76b6-$76e2 routines",
                         [0x76B6], L(8, [0x76B6]))
    # $781a-$7fff data
    out.append("")
    out.append(emit_data(rom, 8, 0x781A, 0x7FFF,
                         "Bank 8 $781a-$7fff data",
                         {},
                         "No verified entries (all bank-0 hits are "
                         "phantoms or other-bank targets; walks from "
                         "them are spurious). Plain db.").rstrip("\n"))
    total += 0x8000 - 0x781A
    assert total == 6395, f"bank 8 total {total} != 6395"
    print(f"bank 8 slice 27: {total} bytes")
    with open("src/banks/bank8slice27.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print("wrote src/banks/bank8slice27.asm")


if __name__ == "__main__":
    build_bank7()
    build_bank8()
    print("slice 27 total: 9662 bytes")
