#!/usr/bin/env python3
"""Slice-26 generator: bank 3 ($03) gaps $43b0-$45a9, $4943-$76ea,
$78b0-$798f (12,417 bytes). Bank 3 is then CLOSED except the $ff
padding ($400c-$4010, $7990-$7fff), which stays INCBIN.

Survey: tools/surveys/survey26_bank3.py.

$43b0-$445a: 86-entry dw offset table (reader: stream-op $4098 at
  $40b0, `ld hl,$43b0; add hl,de`, DE = stream byte & $fe). Values
  strictly increasing $0000-$07f1; the sequence breaks at $445c
  ($08ff, then $8000 -- not monotonic), and $445c is the explicit
  base of the $4102 branch's table (`ld hl,$445c`, 4-byte stride,
  entry (E-1)). Byte-identical in bank 2 (0 differing bytes over
  $43b0-$45a9); bank 2's copy is NOT carved here.
$445c-$45a8: stream-command data (524 bytes). The $4102 branch takes
  the ADDRESS of entry (E-1) at $445c+4*(E-1) and stores it as a
  stream pointer; the dispatcher at $4730 reads the bytes as
  commands ($00/$01/$ca/$eb/$ed/$f0/$f1/$f2/$f3/$f4/$f5/$ff and
  <$ca). No entry count is claimed; emitted as plain db. Song-table
  entry 40 points at $454b inside this span (its header bytes
  `02 04 08 10 20 40 06 0c 18 30 ...` read as song data by the tick).
$4943-$76ea: song data (11,688 bytes). The slice-12 song table
  ($48f1, 41 dw entries) points into it; the tick at $45f2 loads
  DE = table[index] (index = [$c837], gated < $29) and copies 10
  header bytes (2 -> $df07/$df08, 8 -> $df12-$df19), then $46e5
  treats the $df12 words as 4 channel-stream pointers (high byte
  0 = channel off; $ff in the note byte = follow-pointer jump at
  $4726). Songs share phrase data: entries are unsorted, $4941
  (x7) is the all-zero-channel "silent" song whose first 2 bytes
  are the table's own last dw ($454b), and $49b8/$4ac3 are 11 bytes
  apart. No per-song extents are claimed -- the whole span is one
  db section with a label at each unique entry (first table index
  wins). No call/jp/jr target into this span exists in any carved
  code (bank-3 files + all bank-0 files checked); gb_rd from
  $4943 derails in 10 instructions, from $4ac3 in 6. The $454b
  walk (158 instrs) is spurious data-decoding: it reaches carved
  tick code only through jump-shaped data bytes, and the tick
  never jumps to DE -- it reads [DE] bytes sequentially.
$78b0-$798f: wave/volume-table-like data (224 bytes, last non-$ff
  at $798f; $7990-$7fff is all $ff, stays INCBIN). Sub-block starts
  $78b0/$78d2/$78e8/$7942 are labelled; $78d2 and $7942 share the
  15-byte prefix `0f 0d 08 04 02 42 86 ca fd c8 84 42 02 48`. NO
  reader pinned (honest gap): the wave-RAM copy at $781e reads via
  a pointer from $df05/$df0c, which is only read -- never written
  -- in carved bank-3 code; gb_rd from $78b0 derails in 40 instrs.

Door / clear chain: this carve is all data; nothing here writes
hStateTimer ($ff90), hGameState ($ff8e), or [$c105].

Bank 2 ($02) gaps $43b0-$45a9, $48ea-$6211, $6492-$7566 (11,254
bytes). Bank 2 is then CLOSED except the $ff padding
($4000-$4003, $4009-$4010, $7567-$7fff), which stays INCBIN.
Survey: tools/surveys/survey26_bank2.py.

$43b0-$45a9: byte-identical to bank 3 (0 differing bytes) -- the
  same 86-entry dw offset table + $445c stream-command data, read
  by bank 2's own stream-op $4098 (`ld hl,$43b0`, bank2.asm:155)
  and $4102 branch (`ld hl,$445c`, bank2.asm:226). Carved with
  bank-2 labels.
$48ea-$6211: SFX data (6,440 bytes). The slice-12 sound table
  ($47fc, 119 dw entries) points here: all 119 entries in
  $4904-$6196, 118 unique. The tick at $4694 reads each entry as
  an 8-byte header of 4 channel pointers (stored to $df1a/$df35/
  $df50/$df6b with [$df0e]/[$df0f]/[$df10]/[$df11] priority
  checks; high byte 0 = channel off) -- verified: all 119x4
  channel pointers are $0000 or in $48ea-$6211. No per-SFX
  extents are claimed (streams share phrase data via $ff-jumps,
  as in bank 3) -- one db section with a label at each unique
  entry (first table index wins). No call/jp/jr target into this
  span exists in carved bank-2 code; gb_rd from $48ea derails in
  32 instructions, from $5000 in 0, from $6000 in 2. The $7000
  walk (688 instrs) is spurious data-decoding reaching carved
  engine code through jump-shaped bytes, as in bank 3.
$6492-$64c1: 24-entry dw song table (songs 41-64). Reader: the
  bank-2 restart at $6257 (`ld hl,$6492`, index = [$c837]-41,
  gated [$c837] >= $29). All 24 entries point into $64c2-$7566;
  entry 24 would read $452c -- the first song's own header word
  at $64c2 (partition break, same pattern as slice 25's bank-23
  table). $64c2 (7 entries) is the all-zero-channel silent song
  (`2c 45 00...`), like bank 3's $4941.
$64c2-$7566: song data, songs 41-64 (4,261 bytes, last non-$ff
  at $7566; $7567-$7fff is all $ff, stays INCBIN). Each song is a
  10-byte header (2 -> $df07/$df08, 8 -> $df12-$df19, read at
  $6263) + channel streams; verified: every unique entry's 4
  channel pointers are $0000 or in $64c2-$7566. One db section
  with a label at each unique entry (first index wins).

Regenerate with: python3 tools/generators/gen_slice26.py
Byte-match (`make`) arbitrates.
"""
import sys

sys.path.insert(0, "tools")
from gb_rd import file_off  # noqa: E402

ROM = "roms/Donkey_Kong_World_Rev1_SGB.gb"
OUT = "src/banks/bank3slice26.asm"


def byte_at(rom, bank, addr):
    return rom[file_off(bank, addr)]


def rdw(rom, bank, addr):
    return byte_at(rom, bank, addr) | (byte_at(rom, bank, addr + 1) << 8)


def emit_db(out, rom, bank, lo, hi, labels=None):
    """Plain db lines, 16 bytes each, for [lo, hi). `labels` maps an
    address to a label name; lines break at label addresses so the
    label lands exactly. Returns byte count."""
    labels = labels or {}
    n = 0
    a = lo
    while a < hi:
        if a in labels:
            out.append(f"{labels[a]}::")
        nxt = min([hi] + [x for x in labels if a < x < hi])
        chunk = min(16, nxt - a, hi - a)
        vals = [byte_at(rom, bank, a + k) for k in range(chunk)]
        out.append("    db " + ", ".join(f"${x:02x}" for x in vals))
        n += chunk
        a += chunk
    return n


def emit_bank3(rom):
    out = []
    out.append("; Slice 26: Bank 3 $43b0-$45a9, $4943-$76ea, $78b0-$798f.")
    out.append("; Generated by tools/generators/gen_slice26.py from the ROM bytes")
    out.append("; (survey: tools/surveys/survey26_bank3.py). Byte-match (`make`)")
    out.append("; arbitrates.")
    total = 0

    # --- $43b0-$445a: 86-entry dw offset table ---
    tbl = [rdw(rom, 3, 0x43B0 + 2 * i) for i in range(86)]
    assert tbl[0] == 0x0000 and tbl[-1] == 0x07F1, \
        f"offset table ends {tbl[0]:#x}..{tbl[-1]:#x}"
    assert all(tbl[i + 1] > tbl[i] for i in range(85)), \
        "offset table not strictly increasing"
    assert rdw(rom, 3, 0x445C) == 0x08FF, "partition break moved"
    out.append("")
    out.append('SECTION "Bank 3 $43b0 offset table (86)", ROMX[$43b0], BANK[3]')
    out.append("Bank3_OffsetTable::")
    for i, w in enumerate(tbl):
        out.append(f"    dw ${w:04x}                                         ; ${0x43B0 + 2 * i:04x}")
    total += 2 * len(tbl)

    # --- $445c-$45a8: stream-command data (song 40 entry at $454b) ---
    out.append("")
    out.append('SECTION "Bank 3 $445c stream data", ROMX[$445c], BANK[3]')
    out.append("Bank3_StreamData445C::")
    labels = {0x454B: "Bank3_Song40"}
    n = emit_db(out, rom, 3, 0x445C, 0x45A9, labels)
    assert n == 0x45A9 - 0x445C, f"stream data emitted {n}"
    total += n

    # --- $4943-$76ea: song data, labels at unique table entries ---
    entries = [rdw(rom, 3, 0x48F1 + 2 * i) for i in range(41)]
    assert len(entries) == 41 and min(entries) == 0x454B \
        and max(entries) == 0x764F, "song table changed"
    first_idx = {}
    for i, e in enumerate(entries):
        first_idx.setdefault(e, i)
    song_labels = {}
    for e, i in first_idx.items():
        if e >= 0x4943:  # $454b lives in the $445c section; $4941's
            # first 2 bytes are the song table's own last dw
            song_labels[e] = f"Bank3_Song{i:02d}"
    assert len(song_labels) == 32, f"expected 32 in-span labels, got {len(song_labels)}"
    out.append("")
    out.append('SECTION "Bank 3 song data $4943-$76ea", ROMX[$4943], BANK[3]')
    out.append("; Song-table entries (first index wins); $4941 (idx 29,"
               " x7) is the silent song -- its first 2 bytes are the")
    out.append("; table's last dw at $4941-$4942, the rest is the zero")
    out.append("; run starting here. Duplicates: $4ac3 idx 0/35.")
    n = emit_db(out, rom, 3, 0x4943, 0x76EB, song_labels)
    assert n == 0x76EB - 0x4943, f"song data emitted {n}"
    total += n

    # --- $78b0-$798f: wave/table data ---
    assert set(byte_at(rom, 3, a) for a in range(0x7990, 0x8000)) == {0xFF}, \
        "$7990-$7fff not all $ff"
    out.append("")
    out.append('SECTION "Bank 3 $78b0 tables", ROMX[$78b0], BANK[3]')
    out.append("; No reader pinned (honest gap): wave-RAM copy at $781e")
    out.append("; reads via $df05/$df0c pointers, written nowhere in")
    out.append("; carved bank-3 code. $78d2/$7942 share a 15-byte prefix.")
    labels = {0x78B0: "Bank3_WaveTable78B0", 0x78D2: "Bank3_WaveTable78D2",
              0x78E8: "Bank3_WaveTable78E8", 0x7942: "Bank3_WaveTable7942"}
    n = emit_db(out, rom, 3, 0x78B0, 0x7990, labels)
    assert n == 0x7990 - 0x78B0, f"tables emitted {n}"
    total += n

    assert total == (0x45A9 - 0x43B0) + (0x76EB - 0x4943) + (0x7990 - 0x78B0), \
        f"total {total} != 12417"
    print(f"bank 3 slice 26: {total} bytes "
          f"($43b0-$45a9: {0x45A9 - 0x43B0}, "
          f"$4943-$76ea: {0x76EB - 0x4943}, "
          f"$78b0-$798f: {0x7990 - 0x78B0})")
    return "\n".join(out) + "\n"


OUT2 = "src/banks/bank2slice26.asm"


def emit_bank2(rom):
    out = []
    out.append("; Slice 26: Bank 2 $43b0-$45a9, $48ea-$6211, $6492-$7566.")
    out.append("; Generated by tools/generators/gen_slice26.py from the ROM bytes")
    out.append("; (survey: tools/surveys/survey26_bank2.py). Byte-match (`make`)")
    out.append("; arbitrates.")
    total = 0
    b2 = rom[2 * 0x4000:3 * 0x4000]
    b3 = rom[3 * 0x4000:4 * 0x4000]

    # --- $43b0-$45a9: identical to bank 3 ---
    assert b2[0x43B0 - 0x4000:0x45A9 - 0x4000] == \
        b3[0x43B0 - 0x4000:0x45A9 - 0x4000], "bank2 $43b0 block != bank3"
    tbl = [rdw(rom, 2, 0x43B0 + 2 * i) for i in range(86)]
    assert tbl[0] == 0x0000 and tbl[-1] == 0x07F1
    assert all(tbl[i + 1] > tbl[i] for i in range(85))
    out.append("")
    out.append('SECTION "Bank 2 $43b0 offset table (86)", ROMX[$43b0], BANK[2]')
    out.append("Bank2_OffsetTable::")
    for i, w in enumerate(tbl):
        out.append(f"    dw ${w:04x}                                         ; ${0x43B0 + 2 * i:04x}")
    total += 2 * len(tbl)
    out.append("")
    out.append('SECTION "Bank 2 $445c stream data", ROMX[$445c], BANK[2]')
    out.append("Bank2_StreamData445C::")
    n = emit_db(out, rom, 2, 0x445C, 0x45A9)
    assert n == 0x45A9 - 0x445C
    total += n

    # --- $48ea-$6211: SFX data, labels at unique $47fc entries ---
    sfx = [rdw(rom, 2, 0x47FC + 2 * i) for i in range(119)]
    assert min(sfx) == 0x4904 and max(sfx) == 0x6196, "SFX table changed"
    assert len(set(sfx)) == 118
    for e in sfx:
        h = [byte_at(rom, 2, e + k) for k in range(8)]
        for j in range(4):
            w = h[2 * j] | (h[2 * j + 1] << 8)
            assert w == 0 or 0x48EA <= w <= 0x6211, \
                f"SFX ${e:04x} ch{j} ptr ${w:04x} out of range"
    first_idx = {}
    for i, e in enumerate(sfx):
        first_idx.setdefault(e, i)
    sfx_labels = {e: f"Bank2_SFX{i:03d}" for e, i in first_idx.items()}
    out.append("")
    out.append('SECTION "Bank 2 SFX data $48ea-$6211", ROMX[$48ea], BANK[2]')
    out.append("; $47fc entries (first index wins); $48ea-$4903 is the")
    out.append("; 26-byte run before the first entry. No per-SFX extents")
    out.append("; claimed -- streams share phrase data via $ff-jumps.")
    n = emit_db(out, rom, 2, 0x48EA, 0x6212, sfx_labels)
    assert n == 0x6212 - 0x48EA, f"SFX data emitted {n}"
    total += n

    # --- $6492-$64c1: 24-entry dw song table (songs 41-64) ---
    songs = [rdw(rom, 2, 0x6492 + 2 * i) for i in range(24)]
    assert all(0x64C2 <= t <= 0x7566 for t in songs), "song table changed"
    assert rdw(rom, 2, 0x64C2) == 0x452C, "partition break moved"
    out.append("")
    out.append('SECTION "Bank 2 $6492 song table (24)", ROMX[$6492], BANK[2]')
    out.append("Bank2_SongTable41::")
    for i, w in enumerate(songs):
        out.append(f"    dw ${w:04x}                                         ; ${0x6492 + 2 * i:04x} song {41 + i}")
    total += 2 * len(songs)

    # --- $64c2-$7566: song data, labels at unique entries ---
    first_idx = {}
    for i, e in enumerate(songs):
        first_idx.setdefault(e, i)
    for e in songs:
        h = [byte_at(rom, 2, e + k) for k in range(10)]
        for j in range(4):
            w = h[2 + 2 * j] | (h[3 + 2 * j] << 8)
            assert w == 0 or 0x64C2 <= w <= 0x7566, \
                f"song ${e:04x} ch{j} ptr ${w:04x} out of range"
    song_labels = {e: f"Bank2_Song{41 + i:02d}" for e, i in first_idx.items()}
    assert len(song_labels) == 17, f"expected 17 song labels, got {len(song_labels)}"
    assert set(byte_at(rom, 2, a) for a in range(0x7567, 0x8000)) == {0xFF}, \
        "$7567-$7fff not all $ff"
    out.append("")
    out.append('SECTION "Bank 2 song data $64c2-$7566", ROMX[$64c2], BANK[2]')
    out.append("; $6492 entries (first index wins); $64c2 (songs 46/52/")
    out.append("; 54/59/60/61/62) is the silent song, all-zero channels.")
    n = emit_db(out, rom, 2, 0x64C2, 0x7567, song_labels)
    assert n == 0x7567 - 0x64C2, f"song data emitted {n}"
    total += n

    assert total == (0x45A9 - 0x43B0) + (0x6212 - 0x48EA) \
        + (0x64C2 - 0x6492) + (0x7567 - 0x64C2), f"total {total} != 11302"
    print(f"bank 2 slice 26: {total} bytes "
          f"($43b0-$45a9: {0x45A9 - 0x43B0}, "
          f"$48ea-$6211: {0x6212 - 0x48EA}, "
          f"$6492-$64c1: {0x64C2 - 0x6492}, "
          f"$64c2-$7566: {0x7567 - 0x64C2})")
    return "\n".join(out) + "\n"


def main():
    rom = open(ROM, "rb").read()
    txt = emit_bank3(rom)
    with open(OUT, "w") as f:
        f.write(txt)
    print(f"wrote {OUT} ({len(txt.splitlines())} lines)")
    txt2 = emit_bank2(rom)
    with open(OUT2, "w") as f:
        f.write(txt2)
    print(f"wrote {OUT2} ({len(txt2.splitlines())} lines)")


if __name__ == "__main__":
    main()
