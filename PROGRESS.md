# Progress — Donkey Kong '94 disassembly

Started 2026-11-21. Target ROM SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`.

**Move (2026-11-21):** project moved from `~/workspace/donkey-kong-decomp/` into
the monorepo staging tree at `~/workspace/mike-monorepo/donkey-kong-decomp/`
(T's call, so git history follows if it moves later). Old path is a symlink
to the new location. After the move: clean `make` rebuilds byte-identical
(SHA-1 `397ad2ff…`, `cmp` clean) and Nacre framebuffers match slice 1
exactly at 60/180/600 frames. One stale absolute path fixed
(`docs/BANKMAP.md`). Pushable set (excluding `roms/` + `build/`, both
git-ignored): `.gitignore`, `Makefile`, `PROGRESS.md`, `README.md`,
`docs/BANKMAP.md`, `src/banks.asm`, `src/constants.asm`, `src/hardware.inc`,
`src/main.asm`, `src/sgb.asm`, `tools/analyze_rom.py`, `tools/gb_headless`,
`tools/gb_headless.c`, `tools/gen_banks.py` — no `.gb`/`.sav` in it.
NOT pushed in this run (snapshot-sync push needs T's go-ahead). Note:
`tools/gb_headless` is a compiled binary in the tree with no documented
rebuild command in README/PROGRESS yet — decide before pushing whether
to exclude it and document the build, or keep it.

## Slice 1 — DONE, byte-matching (2026-11-21)

**Build:** `make` → `build/game.gb`, SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`,
`cmp` against the original: clean, zero differing bytes.

**Nacre test** (`tools/gb_headless`, Nacre GB core, no buttons pressed):
framebuffer SHA-256 identical original vs rebuilt at 60, 180, and 600 frames:

| frames | fb SHA-256 (both ROMs) | nonzero px |
|---|---|---|
| 60 | `cb763066498a7d6598cec1873516419866bb245261aada5176cd596eaca85569` | 22762/23040 |
| 180 | `4957685e8610c7a2fd08a559695bb7757c8accdf54d0417d679b5885611f2bf1` | 22762/23040 |
| 600 | `1cf926799cff7d9119d27ca6fde515c0da226eccb342eb0a823e8bbb79733c03` | 19633/23040 |

At 60 frames the screen is the brick-wall title background with
"©1994 Nintendo"; at 600 frames it is the full title screen
("GAME BOY / DONKEY KONG / PUSH START", DK's face, "©1994 Nintendo").
Screenshots: `build/nacre-test/orig-60.png`, `orig-600.png`
(rebuilt PNGs are byte-identical to the originals and were not duplicated).

**Curated in slice 1** (hand-labelled, hand-checked against the ROM bytes;
~1,080 lines of RGBDS source in `src/main.asm` + `src/sgb.asm`):

- Header, RSTs, interrupt vectors, entry point `$0150`, main loop `$0175`.
- `SetupTimerAndSTAT` `$0193`, `DispatchState` `$01a9` + 32-entry jump table,
  `CheckSoftReset` `$01ec` (A+B+Select+Start, state ≥ 3, state ≠ $1a),
  `ClearRAMAndInit` `$0226`.
- VBlank `$0275`, STAT `$02b0`, Timer `$02c7` handlers; `STATDispatch`
  `$02ec` + 16-entry table (targets listed as raw addresses, not yet named).
- `CopyDMARoutine` `$0fc1` + DMA routine `$0fcf`, `DispatchViaRST8` `$0fd9`
  (the jump-table engine), bank-switch tail `$0fe5`, LCD helpers
  `$0feb-$1021`, `ReadJoypad` `$1022`, memory helpers `$1057-$1074`,
  `ClearTilemaps` `$10ab`, `InitStatePtrs`/`AdvanceState`/`IncStateTimer`
  `$1d07-$1d2e`, `LoadPalette` `$1e4f`.
- All of `DetectSGB` `$3737-$3854` + `$391b-$392a`: SGB probe, border
  tilemap fill, VRAM transfers, packet sender `$388e`, gated variant
  `$3891`, bit-banger `$38bf`, delays `$3857/$385e/$3860/$3885`,
  `SaveIEWaitVBlankLCDOff` `$386a`, `ReadJoypadRaw` `$38f4`.

**Still raw INCBIN** (not curated): bank 0 `$030f-$0fc0`, `$1075-$10aa`,
`$10c2-$1d06`, `$1d2f-$1e4e`, `$1e6b-$3736`, `$3947-$3fff`, and all of
banks 1–31. That is the overwhelming majority of the ROM by bytes.

### Findings (verified, not guessed)

- Entry is `nop; jp $0150` at `$0100`; the boot ROM is skipped by Nacre,
  so `$0150` is where execution starts. Entry sets SP `$fffe`, bank 1,
  sends SGB packet `$5d`, clears RAM, copies the DMA routine to HRAM,
  loads palette 3, detects the SGB, sets up timer/STAT, enables IE `$07`.
- The game has **two** `rst $08` jump-table dispatches: the main state
  machine (`hGameState` at `$ff8e`, table at `$01ac`, 32 entries) and
  the STAT handler (`hSTATState` at `$ff8f`, table at `$02ef`, 16 entries).
  The bytes after an `rst $08` are a table of 16-bit addresses, not code.
- `rst $10` is the bank switch: A = bank, stored to `hCurrentBank`
  (`$ff8c`) and to MBC1 register `$2000`.
- `rst $08` handler `$0fd9`: pops the return address (= table start),
  `HL += A*2`, jumps to the address stored there.
- State 12's table entry points at `$c1fe` (WRAM). No code is copied
  there anywhere we have looked, and state 12 is never written in
  bank 0. **Unverified**: it may be a dead entry. Do not call it a handler.
- State 24's entry points at `$4000` (start of the banked window): the
  handler lives in whatever bank is mapped at dispatch time.
- `CheckSoftReset` is a soft reset, not a cheat: all four buttons held,
  state ≥ 3, state ≠ `$1a`, then reset to state 2.
- On a plain Game Boy / in Nacre (DMG-only), `DetectSGB` returns early:
  both joypad reads come back `$ff`, flag bit 7 of `wSGBFlag` stays
  clear, `wSGBMode` = `$cc`. The border transfer only runs on real SGB.
- The DKGBDisasm reference builds a *different revision* (Rev 0,
  SHA-1 `6ed661bd…`), so it cannot be used as a byte oracle for this ROM.

### Mistakes caught by the byte-match check (kept here so they are not repeated)

1. Three call sites use the **gated** SGB sender `$3891`, not `$388e`:
   `$01fd`, `$0fed`, `$100d`. The first build called `$388e` there and
   mismatched at `$01fe`, `$0fee`, `$100e`. The ungated `$388e` is only
   correct during detection (`$0159`, `$373e`, `$3752`), when the SGB
   flag is not set yet.
2. Carving `ClearTilemaps` (`$10ab-$10c1`) out of raw gap B left
   `$1075-$10aa` uncovered (rgblink fills gaps with `$00`); it needed
   its own INCBIN section.
3. Bank 0 tail size is `$6b9` (`$4000-$3947`), not `$b9` — the first
   build left `$3a00-$3fff` as zeros.
4. RGBDS 1.0.4 requires `DEF NAME EQU …`; bare `EQU` fails.
5. An early draft of `tools/analyze_rom.py` had a wrong Nintendo logo
   table from memory; the correct bytes are Nacre's
   `src/gb/gb_cart.c` table, and the ROM's logo verifies against it.
6. mgbdis (raw scaffold) mis-disassembles the region after `rst $08`
   at `$01ab` as code: `$01ac-$01eb` is the state jump table, and the
   bytes at `$01c4` (`fe c1`, entry 12 → `$c1fe`) are a table entry,
   not `cp $c1`. Any future slice must treat `rst $08` sites as
   table boundaries, never as linear code.

### Tool versions (verified on this box, 2026-11-21)

- RGBDS **1.0.4** — `~/workspace/tools/rgbds-1.0.4/` (release tarball).
- mgbdis **3.0** — `~/workspace/tools/mgbdis/` (single Python script, MIT).
- Nacre GB core — `~/workspace/nacre/repo/` (unmodified; harness only).
- Python 3.12.3, GCC 13.3.0 (Ubuntu 24.04).

## Next slices (priority order)

1. **State handlers for states 0–31** (table at `$01ac`): name and
   curate the handlers at `$340e`, `$359a`, `$28a8`, `$3657`, `$06bd`,
   `$34df`, `$0692`, `$266c`, `$3582`, `$3663`, `$3679`, `$3471`,
   `$290a` (bank 0) and the banked entry at `$4000` (state 24).
   Resolve state 12 (`$c1fe`) first — find whether anything ever
   writes state 12 or copies code to `$c1fe`; if dead, say so.
   This is the core of the game: title screen, file select, gameplay.
2. **The `$257f` transfer/decompressor** (called by `DetectSGB` and
   used all over bank 0): curate it, then the palette table at `$1e86`
   and the SGB packet table in bank `$1e` at `$4000`. These unlock
   reading the SGB data properly.
3. **STAT dispatch targets** (`$0367-$0447`, 16 entries): curate them
   and the scanline-effect code they drive; then the per-frame update
   at `$16f9` / `$1663` called from VBlank. After that, gameplay code
   in banks 1–31, starting with whichever bank state 2's handler
   (`$340e`) calls into.

## Not done / blocked

- Nothing is blocked. No GitHub push has been made (needs T's say-so).
- Ghidra was not needed: mgbdis + hand-checking against the bytes
  covered slice 1. It may still be useful for banked code later.
- Input beyond boot was not tested: the harness presses no buttons,
  so gameplay past the title screen ("PUSH START") is unverified.
  A next step is driving Start in the harness and screenshotting
  the file-select / first stage.
- Save RAM (battery) behaviour was not exercised.
