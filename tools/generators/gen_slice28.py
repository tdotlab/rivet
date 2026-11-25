#!/usr/bin/env python3
"""Slice-28 generator: bank 16 $5fd3-$7dbd pockets + bank-0 raw regions.

CORRECTION to the slice-27 task premise: bank-0 $0fd9 is NOT raw -- it has
been carved in src/main.asm since slice 1 (DispatchViaRST8). What slice 27
actually found is the `call $0fd9` INLINE-TABLE idiom: $0fd9 pops the
return address (= the address just after the call), adds A*2, and jumps to
the dw stored there. So the bytes after `call $0fd9` are a dw jump table,
not code -- the same family as rst $08 tables, but entered via call. The
table-entry routines `ret` to whatever the caller pushed (or to the call's
return address when nothing was pushed). gb_rd's walk does NOT know this:
it falls through the call into the table bytes and decodes garbage. This
generator therefore walks ONLY from table-entry targets (never from a
dispatch head), emits each inline table with emit_dw, and decodes dispatch
heads linearly (decode_head) stopping at the `call $0fd9`.

BANK 16 $5fd3-$7dbd (7,659 B; slice 26 emitted this whole span as db, which
is why the curated count does not move for bank 16 -- the bytes were already
counted; this slice replaces the db with real code/tables/data):
  $5fd3-$617b data (no reader pinned; $5fd3-$605d zeros; the $6118 words
    look like $61xx pointers but their targets decode as data noise --
    `ld [$0808],sp` x4 -- so the whole span is data).
  $617c-$619b code (seed $617c; bank-0 $09cc call, bank 16 mapped).
  $619c dw table, 2 entries ($61a0, $61a6). Reader $6194 (ld hl,$619c;
    add hl,bc; index [$c213]*2).
  $61a0-$61b1 code (seeds $61a0, $61a6; $61ac by fall-through from $61a6).
  $61b2 head: call $0fd9 (bank-0 $28e5/$321f call, A=B).
  $61b5 dw table, 6 entries ($61c1, $622b, $633c, $63d7, $63d8, $649d).
  $61c1-$6484 code (seeds = the 6 entries minus $649d; db $6335-$633b).
  $6485-$649c data (24 B, record-looking bytes, no reader pinned).
  $649d 1-byte ret (entry 5 of the $61b5 table -- a no-op entry).
  $649e head: call $0fd9 (bank-0 $0af7 call, A=B).
  $64a1 dw table, 8 entries ($64b1, $661a, $67bc, $692a, $69ba, $6a3c,
    $6b30, $6b31; entries 6/7 are 1-byte rets).
  $64b1-$6b31 code (seeds = the 8 entries; one continuous span, 1029
    instrs, 0 uncovered).
  $6b32 head: ld hl,$72e4; push hl; call $0fd9 (bank-0 $0aaf/$2904 call,
    A=B). The pushed $72e4 is the continuation the table routines ret to
    (via $6d52/$6db7).
  $6b39 dw table, 6 entries ($6b45, $6b57, $6b69, $6b6f, $6b70, $6b84;
    entry 5 is a 1-byte ret).
  $6b45-$6b84 code (seeds = the 6 entries).
  $6b85 head: ld hl,$72e4; push hl; call $0fd9 (bank-0 $0b0f call, A=B).
  $6b8c dw table, 8 entries ($6b9c, $6bae, $6cfc, $6d14, $6d2c, $6d3e,
    $6d50, $6d51; entries 6/7 are 1-byte rets).
  $6b9c-$6bce code (seeds $6b9c, $6bae; includes $6bc9's nested dispatch
    head ld a,[$c213]; call $0fd9).
  $6bcf dw table, 4 entries ($6bd7, $6bfe, $6c2a, $6ce5). Reader $6bc9
    (index [$c213]).
  $6bd7-$6d51 code (seeds = nested entries + $6b8c entries 2-7).
  $6d52 head: ld de,$c161; ld a,[de]; res 0,a; ld [de],a; push hl;
    ld e,[hl]; inc hl; ld d,[hl]; ld c,l; ld b,h; ld a,[de];
    ld hl,$6db7; push hl; call $0fd9.
  $6d67 dw table, 40 entries -- ONE table, not two: entries 0-20
    ($6dbf-$6fe9) and 21-39 ($6ff5-$72c5) are contiguous ($6d67+2k,
    k=0..39); the "$6d91 table" is entries 21-39 of the same table.
    Index A = [$c161] & ~1, so A ranges 0..78. No separate reader exists
    (no `ld hl,$6d91` anywhere in the ROM); the reader is $6d52 itself.
  $6db7-$6dbe continuation: pop hl; ld a,[$c161]; rra; jr nc,$6d59
    (loop back into $6d52 while bit 0 clear); ret.
  $6dbf-$7280 code (seeds = table entries 0-35).
  $7281-$7290 data (16 B; $7281 is a data base, ld hl,$7281 at $7274).
  $7291-$72e3 code (seeds = entries 36-38; includes the $72dd shared
    tail: add a,l; ld l,a; inc de; ld [hl],e; inc hl; ld [hl],d; ret).
  $72e4-$733a code (seed $72e4; the record-scan routine, reads the $7b86
    pointer table; called from $617c and pushed as the $6b32/$6b85
    continuation).
  $733b-$7dbd data (labels $7343 = signed-offset table read at $6ee3,
    $735d read at $718b, $7b86 = pointer table read at $72f8; the
    post-ret walk over this span decodes as data noise -- `ld a,e;
    ret z` x10, `ld bc,$0b02`, `jp nz,$0380` -- so it is data, and the
    $7b86 entries point at data records, not code).

BANK 0 (609 B; these are the last INCBINs in src/main.asm -- after this
slice bank 0's only INCBIN is the $3947-$3fff $ff tail in src/banks.asm):
  $0674-$067f code (seeds $0674, $067b; $0674-$067a is the tail of
    STAT_0673: ldh [$ff45],a; ld a,$35; jp $03e9; $067b called from
    $04fc: ld hl,$ce1d; jr $0683).
  $0df4-$0f08 code (seeds $0df4, $0e29, $0e64, $0ea9, $0ecd; $0df4 jp'd
    from bank-7 $7e52/$7e64/$7e76 + called from bank-1 $50ef / bank-12
    $564e; $0e29 jp'd from $0bcd/$0bdb + bank-16 $7e00, called from
    bank-16 $481a; $0e64 called from bank-1 $4e0c / $074a; $0ea9 called
    from bank-1 $4142; $0ecd called from $3548).
  $0f74-$0f94 code (seed $0f74; 3x memcpy via $106e, ends jp $106e).
  $0fa1-$0fc0 data (labels $0fa1 -- ld de,$0fa1 at $0c9c, source for a
    $169c transfer -- and $0fae -- ld hl,$0fae at $07f1; the "code"
    decode is noise: daa; sbc h; ld bc,$a707...).
  $1075-$10aa code (seeds $1075, $1092, $1097; $1075 = 16-bit division
    helper, $1092 = 5-byte add-HL-A helper, $1097 = $c220 record scan).
  $1e6b-$1e85 code (seed $1e6b; called from bank-1 $411e/$5148).
  $3689-$3736 data (labels $370f -- ld de/hl,$370f at $338f/$33a7/$33c3
    -- and $3723 = PutNumberTiles digit table; bytes are ASCII digit /
    tile data, "//////02468:<>@B13579;=?AC" at $3723).

Survey: tools/surveys/survey28_b16.py, tools/surveys/survey28_bank0.py.
NOTE on post_ret seeds: TRUE GB ret opcodes only {C9,C0,C8,D0,D8}.
Earlier survey scripts also listed E0/E8/F0/F8, which are LDH/ADD-SP/
LDH/LD-HL-SP, NOT rets -- that seeds garbage decodes overlapping real
instructions (e.g. the spurious "$0e6c: adc a" over $0e6b's ldh).

Run: python3 tools/generators/gen_slice28.py
Outputs: src/banks/bank16slice28.asm, src/banks/bank0slice28.asm (checked in, not
generated at build time). Then hand-edit: delete the $5fd3-$7dbd db block
(lines 1722-EOF) from src/banks/bank16slice26.asm, delete the 7 INCBIN sections
from src/main.asm, add both INCLUDEs to src/main.asm.
"""
import re
import sys

sys.path.insert(0, "tools")
sys.path.insert(0, "tools/generators")
import gen_slice26  # noqa: E402
from gb_rd import decode, file_off, walk  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
rom = open(ROM, "rb").read()
TRUE_RET = {0xC9, 0xC0, 0xC8, 0xD0, 0xD8}


def post_ret(bank, lo, hi):
    b = rom[bank * 0x4000:(bank + 1) * 0x4000] if bank else rom
    base = 0x4000 if bank else 0
    return [a + 1 for a in range(lo, hi - 1)
            if b[a - base] in TRUE_RET]


def walk_region(bank, lo, hi, seeds, drop_from=None, expect_db=()):
    """Walk with post-ret seeds first (processed last), verified seeds
    last (processed first). drop_from: drop reached instructions at or
    after this address (table bytes the walk fell into after a
    `call $0fd9`). Post-ret seeds inside an expected-db gap are NOT
    used: a ret-terminated code span followed by data would otherwise
    seed a garbage decode that "covers" the gap (e.g. $6335)."""
    expect = {x for a, b in expect_db for x in range(a, b + 1)}
    allseeds = [s for s in post_ret(bank, lo, hi) if s not in expect] + seeds
    reached, rst08, notes = walk(bank, allseeds)
    assert not rst08, f"bank {bank} ${lo:04x}: unexpected rst $08: {rst08}"
    if drop_from is not None:
        reached = {a: v for a, v in reached.items() if a < drop_from}
    cov = set()
    for a, (ln, _, _, _) in reached.items():
        cov.update(range(a, a + ln))
    uncov = []
    cur = None
    for x in range(lo, hi + 1):
        if x not in cov:
            cur = [x, x] if cur is None else [cur[0], x]
        elif cur:
            uncov.append(tuple(cur))
            cur = None
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
    out = [f"; Slice 28: {title} -- bank {bank} ${lo:04x}-${hi:04x}.",
           "; Generated by tools/generators/gen_slice28.py from the ROM bytes via",
           "; tools/gb_rd.py (recursive descent, not mgbdis' linear",
           "; sweep). Byte-match (`make`) arbitrates.",
           f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]'
           if bank else f'SECTION "{title}", ROM0[${lo:04x}]']
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
    out = [f"; Slice 28: {title} -- bank {bank} ${lo:04x}-${lo + 2 * len(entries) - 1:04x}.",
           "; Generated by tools/generators/gen_slice28.py. Byte-match arbitrates."]
    if comment:
        out.append(f"; {comment}")
    out.append(f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]'
               if bank else f'SECTION "{title}", ROM0[${lo:04x}]')
    for i, e in enumerate(entries):
        out.append(f"    dw ${e:04x}                                    ; ${lo + 2 * i:04x}")
    return "\n".join(out) + "\n"


def emit_data(rom, bank, lo, hi, title, labels, comment=""):
    out = [f"; Slice 28: {title} -- bank {bank} ${lo:04x}-${hi:04x}."]
    if comment:
        out.append(f"; {comment}")
    out.append("; Generated by tools/generators/gen_slice28.py. Byte-match arbitrates.")
    out.append(f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]'
               if bank else f'SECTION "{title}", ROM0[${lo:04x}]')
    lines = []
    n = gen_slice26.emit_db(lines, rom, bank, lo, hi + 1, labels)
    assert n == hi - lo + 1, f"db ${lo:04x} emitted {n}"
    out.extend(lines)
    return "\n".join(out) + "\n"


def code_region(out, rom, bank, lo, hi, title, seeds, labels,
                expect_db=(), drop_from=None):
    instrs, uncov = walk_region(bank, lo, hi, seeds, drop_from,
                                expect_db)
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


def decode_head(bank, lo, label, title):
    """Linear-decode a dispatch head ending in `call $0fd9`. Returns the
    emitted section text and the address just past the call (= table)."""
    addr = lo
    lines = [f"; Slice 28: {title} -- bank {bank} ${lo:04x}.",
             "; Generated by tools/generators/gen_slice28.py (linear decode: the",
             "; head ends in `call $0fd9`, whose inline table follows).",
             f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]'
             if bank else f'SECTION "{title}", ROM0[${lo:04x}]',
             f"{label}::"]
    while True:
        ln, text, kind, tgt = decode(rom, file_off(bank, addr), addr)
        assert kind != "data", f"${addr:04x} decodes as data in head"
        lines.append(f"    {text:<48} ; ${addr:04x}")
        addr += ln
        if text == "call $0fd9":
            break
        assert addr < lo + 32, f"head at ${lo:04x} runs past 32 bytes"
    return "\n".join(lines) + "\n", addr


def L(bank, addrs):
    return {a: f"Bank{bank}_{a:04X}" for a in addrs}


# $6d67 40-entry table (entries 0-20 then 21-39, contiguous).
T6D67 = [0x6DBF, 0x6DC5, 0x6DD1, 0x6DE4, 0x6DF1, 0x6DFE, 0x6E10, 0x6E34,
         0x6E42, 0x6E50, 0x6E60, 0x6E70, 0x6E80, 0x6EA8, 0x6F06, 0x6F2E,
         0x6F60, 0x6F7E, 0x6FD1, 0x6FDC, 0x6FE9, 0x6FF5, 0x7000, 0x7014,
         0x7028, 0x703C, 0x706E, 0x70BB, 0x70D3, 0x70DF, 0x70EC, 0x70F9,
         0x711D, 0x7132, 0x7145, 0x715C, 0x7262, 0x7291, 0x72A1, 0x72C5]


def build_bank16():
    out = ["; Slice 28: Bank 16 $5fd3-$7dbd pockets (7,659 bytes) -- the",
           "; slice-26 db span replaced with real code, inline tables,",
           "; and data. Generated by tools/generators/gen_slice28.py (survey:",
           "; tools/surveys/survey28_b16.py). Byte-match (`make`) arbitrates.",
           "; Bank 16 is now CLOSED for real (only the $7e03-$7fff $ff",
           "; tail stays INCBIN)."]
    total = 0
    # $5fd3-$617b data
    out.append("")
    out.append(emit_data(rom, 16, 0x5FD3, 0x617B,
                         "Bank 16 $5fd3-$617b data", {},
                         "$5fd3-$605d zeros; the $6118 words look like "
                         "$61xx pointers but their targets decode as data "
                         "noise, so the whole span is data. No reader "
                         "pinned.").rstrip("\n"))
    total += 0x617C - 0x5FD3
    # $617c-$619b code
    total += code_region(out, rom, 16, 0x617C, 0x619B,
                         "Bank 16 $617c-$619b routine",
                         [0x617C], L(16, [0x617C]))
    # $619c dw table, 2 entries
    out.append("")
    out.append(emit_dw(16, 0x619C, [0x61A0, 0x61A6],
                       "Bank 16 $619c jump table",
                       "Reader $6194: ld hl,$619c; add hl,bc; ld a,[hl+]; "
                       "ld h,[hl]; ld l,a; jp hl. Index [$c213]*2.")
               .rstrip("\n"))
    total += 4
    # $61a0-$61b1 code
    total += code_region(out, rom, 16, 0x61A0, 0x61B1,
                         "Bank 16 $61a0-$61b1 routines",
                         [0x61A0, 0x61A6], L(16, [0x61A0, 0x61A6]))
    # $61b2 head
    out.append("")
    head, nxt = decode_head(16, 0x61B2, "Bank16_61B2",
                            "Bank 16 $61b2 dispatch head")
    assert nxt == 0x61B5, f"$61b2 head ends ${nxt:04x}, not $61b5"
    out.append(head.rstrip("\n"))
    total += 0x61B5 - 0x61B2
    # $61b5 dw table, 6 entries
    out.append("")
    out.append(emit_dw(16, 0x61B5, [0x61C1, 0x622B, 0x633C, 0x63D7,
                                    0x63D8, 0x649D],
                       "Bank 16 $61b5 jump table",
                       "Inline table after `call $0fd9` at $61b2 (A=B, "
                       "bank-0 $28e5/$321f call). Entry 5 ($649d) is a "
                       "1-byte ret.").rstrip("\n"))
    total += 12
    # $61c1-$6484 code + db $6335-$633b
    total += code_region(out, rom, 16, 0x61C1, 0x6484,
                         "Bank 16 $61c1-$6484 routines",
                         [0x61C1, 0x622B, 0x633C, 0x63D7, 0x63D8],
                         L(16, [0x61C1, 0x622B, 0x633C, 0x63D7, 0x63D8]),
                         expect_db=[(0x6335, 0x633B)])
    # $6485-$649c data
    out.append("")
    out.append(emit_data(rom, 16, 0x6485, 0x649C,
                         "Bank 16 $6485-$649c data", {},
                         "Record-looking bytes between the $61c1 family "
                         "and the $649d ret; no reader pinned.").rstrip("\n"))
    total += 0x649D - 0x6485
    # $649d ret
    out.append("")
    out.append("; Slice 28: Bank 16 $649d -- 1-byte ret, entry 5 of the "
               "$61b5 table (a no-op entry).")
    out.append('SECTION "Bank 16 $649d ret", ROMX[$649d], BANK[16]')
    out.append("Bank16_649D::")
    out.append("    ret                                              ; $649d")
    total += 1
    # $649e head
    out.append("")
    head, nxt = decode_head(16, 0x649E, "Bank16_649E",
                            "Bank 16 $649e dispatch head")
    assert nxt == 0x64A1, f"$649e head ends ${nxt:04x}, not $64a1"
    out.append(head.rstrip("\n"))
    total += 0x64A1 - 0x649E
    # $64a1 dw table, 8 entries
    out.append("")
    out.append(emit_dw(16, 0x64A1, [0x64B1, 0x661A, 0x67BC, 0x692A,
                                    0x69BA, 0x6A3C, 0x6B30, 0x6B31],
                       "Bank 16 $64a1 jump table",
                       "Inline table after `call $0fd9` at $649e (A=B, "
                       "bank-0 $0af7 call). Entries 6/7 are 1-byte rets.")
               .rstrip("\n"))
    total += 16
    # $64b1-$6b31 code
    total += code_region(out, rom, 16, 0x64B1, 0x6B31,
                         "Bank 16 $64b1-$6b31 routines",
                         [0x64B1, 0x661A, 0x67BC, 0x692A, 0x69BA, 0x6A3C,
                          0x6B30, 0x6B31],
                         L(16, [0x64B1, 0x661A, 0x67BC, 0x692A, 0x69BA,
                                0x6A3C, 0x6B30, 0x6B31]))
    # $6b32 head
    out.append("")
    head, nxt = decode_head(16, 0x6B32, "Bank16_6B32",
                            "Bank 16 $6b32 dispatch head")
    assert nxt == 0x6B39, f"$6b32 head ends ${nxt:04x}, not $6b39"
    out.append(head.rstrip("\n"))
    total += 0x6B39 - 0x6B32
    # $6b39 dw table, 6 entries
    out.append("")
    out.append(emit_dw(16, 0x6B39, [0x6B45, 0x6B57, 0x6B69, 0x6B6F,
                                    0x6B70, 0x6B84],
                       "Bank 16 $6b39 jump table",
                       "Inline table after `call $0fd9` at $6b36 (A=B, "
                       "bank-0 $0aaf/$2904 call). Entry 5 ($6b84) is a "
                       "1-byte ret.").rstrip("\n"))
    total += 12
    # $6b45-$6b84 code
    total += code_region(out, rom, 16, 0x6B45, 0x6B84,
                         "Bank 16 $6b45-$6b84 routines",
                         [0x6B45, 0x6B57, 0x6B69, 0x6B6F, 0x6B70, 0x6B84],
                         L(16, [0x6B45, 0x6B57, 0x6B69, 0x6B6F, 0x6B70,
                                0x6B84]))
    # $6b85 head
    out.append("")
    head, nxt = decode_head(16, 0x6B85, "Bank16_6B85",
                            "Bank 16 $6b85 dispatch head")
    assert nxt == 0x6B8C, f"$6b85 head ends ${nxt:04x}, not $6b8c"
    out.append(head.rstrip("\n"))
    total += 0x6B8C - 0x6B85
    # $6b8c dw table, 8 entries
    out.append("")
    out.append(emit_dw(16, 0x6B8C, [0x6B9C, 0x6BAE, 0x6CFC, 0x6D14,
                                    0x6D2C, 0x6D3E, 0x6D50, 0x6D51],
                       "Bank 16 $6b8c jump table",
                       "Inline table after `call $0fd9` at $6b89 (A=B, "
                       "bank-0 $0b0f call). Entries 6/7 are 1-byte rets.")
               .rstrip("\n"))
    total += 16
    # $6b9c-$6bce code (drop the walk's fall-through into the $6bcf table)
    total += code_region(out, rom, 16, 0x6B9C, 0x6BCE,
                         "Bank 16 $6b9c-$6bce routines",
                         [0x6B9C, 0x6BAE], L(16, [0x6B9C, 0x6BAE, 0x6BC9]),
                         drop_from=0x6BCF)
    # $6bcf dw table, 4 entries
    out.append("")
    out.append(emit_dw(16, 0x6BCF, [0x6BD7, 0x6BFE, 0x6C2A, 0x6CE5],
                       "Bank 16 $6bcf jump table",
                       "Inline table after `call $0fd9` at $6bcc (nested "
                       "dispatch in $6bc9; index [$c213]).").rstrip("\n"))
    total += 8
    # $6bd7-$6d51 code
    total += code_region(out, rom, 16, 0x6BD7, 0x6D51,
                         "Bank 16 $6bd7-$6d51 routines",
                         [0x6BD7, 0x6BFE, 0x6C2A, 0x6CE5, 0x6CFC, 0x6D14,
                          0x6D2C, 0x6D3E, 0x6D50, 0x6D51],
                         L(16, [0x6BD7, 0x6BFE, 0x6C2A, 0x6CE5, 0x6CFC,
                                0x6D14, 0x6D2C, 0x6D3E, 0x6D50, 0x6D51]))
    # $6d52 head
    out.append("")
    head, nxt = decode_head(16, 0x6D52, "Bank16_6D52",
                            "Bank 16 $6d52 dispatch head")
    assert nxt == 0x6D67, f"$6d52 head ends ${nxt:04x}, not $6d67"
    out.append(head.rstrip("\n"))
    total += 0x6D67 - 0x6D52
    # $6d67 dw table, 40 entries
    out.append("")
    out.append(emit_dw(16, 0x6D67, T6D67,
                       "Bank 16 $6d67 jump table",
                       "Inline table after `call $0fd9` at $6d64; ONE "
                       "40-entry table (index [$c161] & ~1, A=0..78), "
                       "not two tables -- entries 21-39 sit at $6d91+. "
                       "The reader is $6d52 itself.").rstrip("\n"))
    total += 80
    # $6db7-$6dbe continuation
    total += code_region(out, rom, 16, 0x6DB7, 0x6DBE,
                         "Bank 16 $6db7-$6dbe dispatch continuation",
                         [0x6DB7], L(16, [0x6DB7]))
    # $6dbf-$7280 code (entries 0-36; $7262's routine ends at $7280)
    total += code_region(out, rom, 16, 0x6DBF, 0x7280,
                         "Bank 16 $6dbf-$7280 routines",
                         T6D67[:37], L(16, T6D67[:37]))
    # $7281-$7290 data
    out.append("")
    out.append(emit_data(rom, 16, 0x7281, 0x7290,
                         "Bank 16 $7281-$7290 data",
                         {0x7281: "Bank16_7281"},
                         "Data base (ld hl,$7281 at $7274).").rstrip("\n"))
    total += 0x7291 - 0x7281
    # $7291-$72e3 code (entries 37-39 + shared tail)
    total += code_region(out, rom, 16, 0x7291, 0x72E3,
                         "Bank 16 $7291-$72e3 routines",
                         T6D67[37:], L(16, T6D67[37:] + [0x72DD]))
    # $72e4-$733a code
    total += code_region(out, rom, 16, 0x72E4, 0x733A,
                         "Bank 16 $72e4-$733a record-scan routine",
                         [0x72E4], L(16, [0x72E4]))
    # $733b-$7dbd data
    out.append("")
    out.append(emit_data(rom, 16, 0x733B, 0x7DBD,
                         "Bank 16 $733b-$7dbd data",
                         {0x7343: "Bank16_7343", 0x735D: "Bank16_735D",
                          0x7B86: "Bank16_7B86"},
                         "$7343 is a signed-offset table (read at $6ee3); "
                         "$735d read at $718b; $7b86 is a pointer table "
                         "read at $72f8. Post-ret walks decode as data "
                         "noise, so the whole span is data.").rstrip("\n"))
    total += 0x7DBE - 0x733B
    assert total == 7659, f"bank 16 total {total} != 7659"
    print(f"bank 16 slice 28: {total} bytes")
    with open("src/banks/bank16slice28.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print("wrote src/banks/bank16slice28.asm")


def build_bank0():
    out = ["; Slice 28: Bank 0 raw regions (609 bytes) -- the last INCBINs",
           "; in src/main.asm. Generated by tools/generators/gen_slice28.py (survey:",
           "; tools/surveys/survey28_bank0.py). Byte-match (`make`) arbitrates.",
           "; After this slice bank 0's only INCBIN is the $3947-$3fff",
           "; $ff tail in src/banks.asm."]
    total = 0
    # $0674-$067f code
    total += code_region(out, rom, 0, 0x0674, 0x067F,
                         "Bank 0 $0674-$067f STAT tail + palette entry",
                         [0x0674, 0x067B], L(0, [0x067B]))
    # $0df4-$0f08 code
    total += code_region(out, rom, 0, 0x0DF4, 0x0F08,
                         "Bank 0 $0df4-$0f08 score routines",
                         [0x0DF4, 0x0E29, 0x0E64, 0x0EA9, 0x0ECD],
                         L(0, [0x0DF4, 0x0E29, 0x0E64, 0x0EA9, 0x0ECD]))
    # $0f74-$0f94 code
    total += code_region(out, rom, 0, 0x0F74, 0x0F94,
                         "Bank 0 $0f74-$0f94 memcpy routine",
                         [0x0F74], L(0, [0x0F74]))
    # $0fa1-$0fc0 data
    out.append("")
    out.append(emit_data(rom, 0, 0x0FA1, 0x0FC0,
                         "Bank 0 $0fa1-$0fc0 data",
                         {0x0FA1: "Bank0_0FA1", 0x0FAE: "Bank0_0FAE"},
                         "$0fa1 is a transfer source (ld de,$0fa1 at "
                         "$0c9c, then call $169c); $0fae is read as "
                         "ld hl,$0fae at $07f1.").rstrip("\n"))
    total += 0x0FC1 - 0x0FA1
    # $1075-$10aa code
    total += code_region(out, rom, 0, 0x1075, 0x10AA,
                         "Bank 0 $1075-$10aa division + record-scan helpers",
                         [0x1075, 0x1092, 0x1097],
                         L(0, [0x1075, 0x1092, 0x1097]))
    # $1e6b-$1e85 code
    total += code_region(out, rom, 0, 0x1E6B, 0x1E85,
                         "Bank 0 $1e6b-$1e85 timer routine",
                         [0x1E6B], L(0, [0x1E6B]))
    # $3689-$3736 data
    out.append("")
    out.append(emit_data(rom, 0, 0x3689, 0x3736,
                         "Bank 0 $3689-$3736 data",
                         {0x370F: "Bank0_370F", 0x3723: "Bank0_3723"},
                         "ASCII digit / tile data; $3723 is the "
                         "PutNumberTiles digit table (ld hl,$3723 at "
                         "$3557); $370f is read at $338f/$33a7/$33c3.")
               .rstrip("\n"))
    total += 0x3737 - 0x3689
    assert total == 609, f"bank 0 total {total} != 609"
    print(f"bank 0 slice 28: {total} bytes")
    with open("src/banks/bank0slice28.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print("wrote src/banks/bank0slice28.asm")


if __name__ == "__main__":
    build_bank16()
    build_bank0()
