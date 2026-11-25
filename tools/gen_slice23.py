#!/usr/bin/env python3
"""Slice-23 generator: bank 15 ($0f) is transfer data, not code.

Survey (see tools/survey23_bank15.py for the reproducible numbers):
  * Bank 15 has exactly ONE entry point in the whole ROM: bank-0
    $1d82 TransferTable0F (slice 2) is the only `ld a,$0f; rst $10`
    site anywhere. It maps bank $0f, reads the $4000 table at
    A*2, follows the block pointer, and for each of the block's
    count sub-pointers calls $16c2 FrameCopy16c2 (bank 0, already
    carved). No call/jp/jr/table target into bank 15 exists
    anywhere else, so no bank-15 byte can ever execute.
  * The $4000 table is 74 entries (dw, $4000-$4093). Entry 74
    would read $4094, which is block 8/15/31's start (count byte
    $01, then dw $4097) -- the partition test: the table ends
    exactly where the blocks begin, same pattern as slice 21's
    bank-9 $418b boundary.
  * 58 distinct blocks: [count][count x dw sub-pointer]. 105
    distinct sub-specs: 6-byte FrameCopy16c2 headers [dst lo,
    dst hi, B=rows, C=cols, src lo, src hi] -- B rows x C bytes
    copied from src, dst advancing $20 per row (VRAM tilemap
    stride); D==0 would be an incrementing fill, but no spec
    uses it (0 fill specs). Two specs copy FROM VRAM instead of
    ROM: $48c4 (dst $9b80, src $9a20) and $56bb (dst $9a40,
    src $98a0) -- tilemap-to-tilemap copies, no ROM data span.
  * Union of table + blocks + headers + src data spans covers
    $4000-$6fc4 with ZERO gaps (12,229 bytes). Shared blocks
    (e.g. $40c8 for entries 1-7,9) and shared data spans are the
    same bytes, never conflicting owners. Last non-$ff byte is
    at $6fc4; $6fc5-$7fff is all $ff padding (stays INCBIN).
  * Opcode-density counts that made bank 15 look code-like
    (whole-bank ret 22 / call 18 / jp (hl) 19) are data bytes:
    the $4000-$5fff 4K windows hold all of them, $6000-$6fff
    holds none at all, and a gb_rd walk from the sub-targets
    "succeeds" only by decoding tilemap data as instructions.
  * Known literal TransferTable0F indices (ld a,imm before
    call $1d82): $09/$0a/$0b/$0c/$0d/$0e/$1d/$1e/$20/$21/$23/
    $3f in bank 0/1/12; other callers pass A from a register.
    All < 74, inside the table.

So the carve emits $4000-$6fc4 as structured db/dw: the table as
dw lines (symbolic, one label per distinct block), each block as
a count byte + dw lines (symbolic, one label per distinct spec),
each spec header as a 6-byte db line with its dst/rows/cols/src
decoded in a comment, and the src data as plain db lines. No code
is claimed anywhere in the bank.

Door / clear chain: bank 15 has no code, so it writes no timer
($ff90) and no [$c105]; no new door lead, no completion attempt
(same NO-GO as slices 15-22).

Regenerate with: python3 tools/gen_slice23.py
Outputs: src/bank15.asm, src/bank13.asm, src/bank14.asm (new files).
Also update tools/gen_banks.py CARVED (banks 13/14/15) and regenerate
src/banks.asm; add INCLUDEs to src/main.asm.
The outputs are CHECKED IN; rerun after changing the config.

Banks 13/14 (fill for the slice -- bank 15 closed on the first build):
surveyed by tools/survey23_banks1314.py. Each has exactly ONE
`ld a,$xx; rst $10` site in the whole ROM, both inside bank-0
$2470 (the stream routine): bank 13 at $24a2 (B in [$80,$af),
decompressor input via $257f), bank 14 at $2477 (H >= $7e, the
$7e00 record table). Opcode counts at noise level; gb_rd walks
from $4000 derail in 11 (bank 13) / 7 (bank 14) instructions.
Bank 13: $4000-$630e stream data, $630f-$7fff $ff padding.
Bank 14: $4000-$7dff stream data (same 16-byte opening as bank
13, otherwise different bytes) + $7e00-$7fa3 a 140-entry table of
3-byte records [bank, ptr lo, ptr hi], all 140 plausible at
alignment $7e00 and zero at $7e01/$7e02 -- the table $2470 reads
(bank bytes {$13,$14,$15,$16,$18}, ptrs $4000-$7c7c). No reader
was found for bank 14's $4000-$7dff region (the only bank-14
mapping is the transient $2470 one, gated on H >= $7e); it is
carved as plain db and that gap is stated honestly, not papered
over. $7fa4-$7fff is $ff padding (stays INCBIN).
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
BANK = 15
LO, HI = 0x4000, 0x6FC5  # HI exclusive; last non-$ff byte at $6fc4


def main():
    rom = open(ROM, "rb").read()

    def byte(a):
        return rom[file_off(BANK, a)]

    def rdw(a):
        return byte(a) | (byte(a + 1) << 8)

    # --- parse the table, blocks, specs -------------------------------
    entries = [rdw(0x4000 + 2 * i) for i in range(74)]
    assert rdw(0x4094) == 0x9701 or True  # $4094 is block data, not a ptr
    # First entry index per distinct block -> label name.
    block_first = {}
    for i, p in enumerate(entries):
        block_first.setdefault(p, i)
    blocks = {}  # block addr -> (count, [sub addrs])
    for p in block_first:
        cnt = byte(p)
        assert 1 <= cnt <= 16, f"block ${p:04x} count {cnt}"
        subs = [rdw(p + 1 + 2 * k) for k in range(cnt)]
        for s in subs:
            assert 0x4000 <= s <= 0x7FFF, f"sub ${s:04x} out of bank"
        blocks[p] = (cnt, subs)
    specs = {}  # spec addr -> (dst, B, C, src)
    for p, (cnt, subs) in blocks.items():
        for s in subs:
            dst = rdw(s)
            specs[s] = (dst, byte(s + 2), byte(s + 3), rdw(s + 4))
    # Spec users (which table entries reach each spec) for comments.
    spec_entries = {}
    for i, p in enumerate(entries):
        for s in blocks[p][1]:
            spec_entries.setdefault(s, []).append(i)

    # --- structural map for the linear sweep --------------------------
    # addr -> ("block", first_entry) | ("spec",) ; data is default.
    struct = {}
    for p, first in block_first.items():
        struct[p] = ("block", first)
    for s in specs:
        assert s not in struct, f"spec ${s:04x} collides with a block"
        struct[s] = ("spec",)
    # No structural start may lie inside another struct's span, or
    # the sweep would skip past it and its label would never emit.
    for p, (cnt, _subs) in blocks.items():
        for k in range(1, 1 + 2 * cnt):
            assert p + k not in struct, \
                f"struct ${p + k:04x} inside block ${p:04x}"
    for s in specs:
        for k in range(1, 6):
            assert s + k not in struct, \
                f"struct ${s + k:04x} inside spec ${s:04x}"

    out = []
    out.append("; Slice 23: bank 15 ($0f) transfer data $4000-$6fc4.")
    out.append("; Read by bank-0 $1d82 TransferTable0F: the $4000 table")
    out.append("; (74 dw entries) -> block [count][count x dw] -> 6-byte")
    out.append("; FrameCopy16c2 ($16c2) spec headers [dst lo, dst hi,")
    out.append("; rows, cols, src lo, src hi] + inline src data. No code")
    out.append("; anywhere in the bank: the only `ld a,$0f; rst $10`")
    out.append("; site in the ROM is inside TransferTable0F itself.")
    out.append("; Generated by tools/gen_slice23.py from the ROM bytes.")
    out.append("; Byte-match (`make`) arbitrates.")
    out.append("")
    out.append('SECTION "Bank 15 transfer table $4000-$4093", '
               "ROMX[$4000], BANK[15]")
    out.append("Bank15_Table::")
    for i, p in enumerate(entries):
        out.append(f"    dw Bank15_Block_{block_first[p]:02d}"
                   f"  ; entry {i} -> block ${p:04x}")
    out.append("")
    out.append('SECTION "Bank 15 transfer data $4094-$6fc4", '
               "ROMX[$4094], BANK[15]")

    emitted = 0x94  # table bytes already emitted
    a = 0x4094
    while a < HI:
        if a in struct:
            kind = struct[a]
            if kind[0] == "block":
                first = kind[1]
                cnt, subs = blocks[a]
                users = [i for i, p in enumerate(entries) if p == a]
                out.append(f"Bank15_Block_{first:02d}::  ; entries {users}")
                out.append(f"    db ${cnt:02x}  ; {cnt} spec(s)")
                emitted += 1
                for s in subs:
                    out.append(f"    dw Bank15_Spec_{s:04X}")
                    emitted += 2
                a += 1 + 2 * cnt
                continue
            # spec header: 6 bytes, decoded in the comment.
            dst, b, c, src = specs[a]
            users = spec_entries[a]
            src_note = (f"src ${src:04x} (VRAM copy)"
                        if 0x8000 <= src <= 0x9FFF else f"src ${src:04x}")
            out.append(f"Bank15_Spec_{a:04X}::  ; entries {users} "
                       f"dst ${dst:04x} rows {b} cols {c} {src_note}")
            hdr = [byte(a + k) for k in range(6)]
            out.append("    db " + ", ".join(f"${x:02x}" for x in hdr))
            emitted += 6
            a += 6
            continue
        # Plain data run: up to the next structural boundary or 16 bytes.
        nxt = HI
        for s in sorted(struct):
            if s > a:
                nxt = min(nxt, s)
        chunk = min(16, nxt - a)
        vals = [byte(a + k) for k in range(chunk)]
        out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
        emitted += chunk
        a += chunk

    assert emitted == HI - LO, f"emitted {emitted} != {HI - LO}"
    assert a == HI
    # Every byte $4000-$6fc4 emitted exactly once (sweep is linear,
    # structural starts consume exactly their span; blocks/specs
    # cannot overlap: asserted above for spec/block, and block spans
    # are disjoint by construction -- same block emitted once).
    with open("src/bank15.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/bank15.asm: {len(out)} lines, {emitted} bytes "
          f"${LO:04x}-${HI - 1:04x}, {len(blocks)} blocks, "
          f"{len(specs)} specs")
    emit_bank13(rom)
    emit_bank14(rom)


def emit_db_bank(rom, bank, lo, hi, title, fname):
    """Emit [lo, hi) as db, 16 bytes per line, one SECTION."""
    out = [f"; Slice 23: {title} -- bank {bank} ${lo:04x}-${hi - 1:04x}.",
           "; Stream data, emitted as db. Generated by",
           "; tools/gen_slice23.py from the ROM bytes.",
           "; Byte-match (`make`) arbitrates.",
           "",
           f'SECTION "{title}", ROMX[${lo:04x}], BANK[{bank}]']
    a = lo
    while a < hi:
        chunk = min(16, hi - a)
        vals = [rom[file_off(bank, a + k)] for k in range(chunk)]
        out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
        a += chunk
    with open(fname, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"{fname}: {len(out)} lines, {hi - lo} bytes "
          f"${lo:04x}-${hi - 1:04x}")


def emit_bank13(rom):
    # $4000-$630e stream data (decompressor input, read via $257f
    # with bank 13 mapped by bank-0 $24a2); $630f+ is $ff padding.
    emit_db_bank(rom, 13, 0x4000, 0x630F,
                 "Bank 13 stream data $4000-$630e", "src/bank13.asm")


def emit_bank14(rom):
    # $4000-$7dff stream data as plain db (no reader found for this
    # region -- see header), then the $7e00-$7fa3 record table as
    # structured [bank][dw ptr] lines (140 records, all plausible).
    emit_db_bank(rom, 14, 0x4000, 0x7E00,
                 "Bank 14 stream data $4000-$7dff", "src/bank14.asm")
    out = []
    with open("src/bank14.asm") as f:
        out = f.read().rstrip("\n").split("\n")
    out.append("")
    out.append("; $7e00-$7fa3: 140-entry pointer table read by bank-0")
    out.append("; $2470 (H >= $7e): each record is [bank][ptr lo]")
    out.append("; [ptr hi]; the bank byte is stored to [$c810] and")
    out.append("; mapped before the pointer is followed (bank-12")
    out.append("; $4a3e runs first). Record banks seen:")
    out.append("; {$13,$14,$15,$16,$18}; ptrs $4000-$7c7c.")
    out.append('SECTION "Bank 14 pointer table $7e00-$7fa3", '
               "ROMX[$7e00], BANK[14]")
    out.append("Bank14_PtrTable::")
    for i in range(140):
        a = 0x7E00 + 3 * i
        bk = rom[file_off(14, a)]
        ptr = rom[file_off(14, a + 1)] | (rom[file_off(14, a + 2)] << 8)
        assert bk <= 0x1F and 0x4000 <= ptr <= 0x7FFF
        out.append(f"    db ${bk:02x}  ; record {i}, bank ${bk:02x}")
        out.append(f"    dw ${ptr:04x}")
    with open("src/bank14.asm", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"src/bank14.asm: table added, {len(out)} lines total, "
          f"140 records")


if __name__ == "__main__":
    main()
