# Donkey Kong '94 — Game Boy disassembly (fresh, from scratch)

A byte-matching disassembly of **Donkey Kong (World) (Rev 1) (SGB Enhanced)**
for the original Game Boy, built with RGBDS. This is T's first decompilation
project, done fresh in this repo — not a copy of an existing disassembly.

## The ROM (bring your own)

This repo contains **no ROM**. You need your own dump of the game:

- File: `Donkey Kong (World) (Rev 1) (SGB Enhanced).gb`
- Size: 512 KiB (0x80000), 32 banks × 16 KiB
- SHA-1: `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`
- MD5: `4859ec2b18c4fabf489eb570c1d7d326`
- Title: `DONKEY KONG`, SGB flag `0x03`, cart type `0x03` (MBC1+RAM+BATTERY),
  ROM size code `0x04`, RAM size code `0x02` (8 KiB), version `0x01` (Rev 1)
- Header checksum `0x2d` and global checksum `0x4f8c`, both verified

Place it at `roms/Donkey_Kong_World_Rev1_SGB.gb` (git-ignored). The build
reads it at build time for the parts not yet curated (INCBIN) and compares
the rebuilt ROM's SHA-1 against the original. Never upload, push, or
distribute the ROM or the rebuilt ROM — the disassembly source is the
shareable artefact, the game data is not.

## Status

**Slices 1, 2, 3 and 4 are done and byte-matching.** `make` rebuilds a ROM whose
SHA-1 is exactly `397ad2ff…`, and the rebuilt ROM boots to the title screen
in Nacre (T's Game Boy emulator) with framebuffers identical to the original
at 60, 180, and 600 frames — and, with Start/A driven by the harness,
past the title screen through file select, the intro, and into gameplay
states, with framebuffers and state traces identical to the original at
900 and 3600 frames. Slice 3 adds banks 1, 12, 23, the bank-0 state-16
chain + C-dispatch, and the bank-`$1e` SGB packet table (~13,180 new
source lines, 16,398 total), resolves state 12 (dead by mechanism),
the timer-29 oddity, and the `$01fb` entries — and drives the rebuilt
ROM as far as the file-management screen (state 28) with a 12000-frame
run identical to the original. Slice 4 adds banks 2, 3, 5 and 7 (stream
command engine, 106-entry stage pointer table, stage-RAM clear and
stream index setup), the 331-entry state-16 queue table as `db` pairs
(19,865 lines total), a recursive-descent disassembler
(`tools/gb_rd.py`), and drives the game further live: state 8
(file-select confirmation) reached and returned from, a save written
via file 1 and reloaded (validates), and the first stage reached past
state 20 — all with framebuffers, state traces and SRAM dumps identical
to the original. See [PROGRESS.md](PROGRESS.md) for what
is curated, what is still raw INCBIN, and the exact verification numbers.

## Build

```sh
make        # builds build/game.gb and checks its SHA-1 against the original
make clean  # remove build artefacts (the ROM in roms/ is untouched)
```

Tools, all recorded in `tools/`:

- RGBDS **1.0.4** (`rgbasm`/`rgblink`/`rgbfix`), portable install at
  `~/workspace/tools/rgbds-1.0.4/` (release tarball from gbdev/rgbds).
  Note: RGBDS 1.0 requires `DEF NAME EQU …` — bare `EQU` no longer works.
- **mgbdis 3.0** (Matt Currie, MIT) at `~/workspace/tools/mgbdis/`, used
  once to generate the machine raw disassembly in `build/raw-mgbdis/`
  (a scratch scaffold, not the curated source) and to cross-check the
  hand-written slice. Its raw output also reassembles byte-identical,
  which is how we know the tooling chain is sound.
- **Nacre** (`~/workspace/nacre/repo/`, T's own GB emulator core) as the
  test harness: `tools/gb_headless.c` links Nacre's `src/gb/` core, runs
  a ROM for N frames headlessly, and dumps the framebuffer as PPM with
  a SHA-256, so original vs rebuilt can be compared exactly. It also
  takes an optional input schedule (`BTN:START:END` windows, e.g.
  `"start:620:632,a:1000:1012"`) and an optional trace file that logs
  `hGameState`/`hStateTimer`/bank/`hSTATState` changes per frame.
  Build it with:

  ```sh
  cc -I ~/workspace/nacre/repo/include -I ~/workspace/nacre/repo/src/gb -O2 \
    -o tools/gb_headless tools/gb_headless.c \
    ~/workspace/nacre/repo/src/gb/gb.c ~/workspace/nacre/repo/src/gb/gb_cpu.c \
    ~/workspace/nacre/repo/src/gb/gb_ppu.c ~/workspace/nacre/repo/src/gb/gb_cart.c \
    ~/workspace/nacre/repo/src/gb/gb_apu.c
  ```

  Usage: `tools/gb_headless <rom.gb> <frames> <out.ppm> [press_spec] [trace_file] [save_in.sav] [save_out.sav]`.
  The optional save files exercise the battery SRAM (load at start, dump
  at end; the run always prints `save_dirty`). Nacre itself is not modified.

## How the disassembly is organised

- `src/main.asm` — header, RST/interrupt vectors, entry point, main loop,
  soft reset, RAM clear, interrupt handlers, the two `rst $08` jump-table
  dispatches (state table now named; STAT table now 60 entries), joypad/
  memory helpers, palette loader.
- `src/stat.asm` — the 60 STAT dispatch targets (`$0367-$0673`) plus
  `RestorePaletteFromShadow`.
- `src/transfer.asm` — RNG step, transfer tables (banks `$0f`/`$1e`),
  sprite-table builder, window helpers, palette table, SRAM save routines.
- `src/decomp.asm` — the bitstream-LZ decompressor (`$257b-$266b`) and RLE
  expander.
- `src/frame.asm` — per-frame routines `$1643-$17ea` called from VBlank.
- `src/states.asm` — state handlers 2, 3, 4, 8, 16, 17, 18, 20, 21, 22,
  26, 28, 30 (prologues, sub-dispatch tables, bank-0 sub-steps).
- `src/bank1.asm`, `src/bank12.asm`, `src/bank23.asm` — slice-3 carves
  (bank 1 file-select/state-28 code + `$48cb-$48f3` data, bank 12
  queue table + stream code, bank 23).
- `src/bank2.asm`, `src/bank3.asm` — slice-4 carves (stream command
  engine, stream tick/restart, sound init + tick).
- `src/bank5.asm` — the 106-entry stage pointer table.
- `src/bank7.asm` — stage-RAM clear, `$4794` routine, stream index setup.
- `tools/gb_rd.py` — recursive-descent disassembler (slice 4); `tools/gen_slice4.py`
  regenerates the slice-4 carves from the ROM bytes.
- `src/sgb.asm` — Super Game Boy detection, border transfer, and the
  joypad-port packet sender.
- `src/hardware.inc`, `src/constants.asm` — IO registers and RAM variables.
- `src/banks.asm` — generated by `tools/gen_banks.py`: INCBIN lines for
  every part of the ROM not yet curated. Curating a region means deleting
  its INCBIN here and writing the code in `src/`.
- `tools/analyze_rom.py` — header/bank-map analysis, computed from the
  ROM bytes (output saved in `docs/BANKMAP.md`).
- `tools/gb_headless.c` — Nacre-based headless test harness (see above).

Method, in short: map the ROM from its bytes first, hand-disassemble one
slice at a time, label everything from evidence in the code, and never
claim byte-matching until `sha1sum` proves it. The two idioms that shape
the whole game are `ld a,N / rst $10` (bank switch) and `rst $08` (jump
through an inline table of 16-bit addresses) — the bytes after an
`rst $08` are a table, not code, and any tool that linear-sweeps past
one will mis-disassemble the table as instructions. See PROGRESS.md.

## References (reference only — not copied)

- **CelestialAmber/DKGBDisasm** (28 stars, dormant since 2022-03-16):
  an earlier disassembly, but of the *non-Rev-1* ROM
  (`Donkey Kong (Japan, USA) (SGB Enhanced).gb`,
  SHA-1 `6ed661bd1d6d8cdd48e1c10f8ca4e8dcba49128e`). Different revision,
  so its code cannot be assumed to match this ROM byte for byte.
  Consulted only to check our work; nothing was copied from it.
- **gnome41/DK94-SGB — DK94 Recomp, v1.3.0 (2026-10-27)**: a static
  recompilation of this exact ROM (it checks for SHA-1 `397ad2ff…`).
  Its README independently confirms the game's dispatch idioms
  (`rst 08h` inline jump tables, `ld a,N / rst 10h` bank switching).
  Consulted only as a cross-check.
- **mgbdis** (see Tools above) and **RGBDS** (gbdev/rgbds).

## Legal

Donkey Kong and Game Boy are trademarks of Nintendo. This is a
clean-room-style disassembly for study: the source here is our own
labelling and commentary on the game's behaviour, and it only builds
into a playable ROM when combined with a copy of the game you own.
Do not distribute the ROM, the rebuilt ROM, or game assets.
