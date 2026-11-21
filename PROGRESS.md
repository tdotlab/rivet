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
  the STAT handler (`hSTATState` at `$ff8f`, table at `$02ef` — slice 1
  said 16 entries; slice 2 corrected this to **60 entries**, 0–59).
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

## Slice 2 — DONE, byte-matching (2026-11-21)

**Build:** `make` → `build/game.gb`, SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`,
`cmp` against the original: clean, zero differing bytes.

**Nacre test** (`tools/gb_headless`, now with an input schedule and a
state trace — see README for the build command). Framebuffer SHA-256
identical original vs rebuilt at every frame count, and the state traces
are byte-identical for the input runs:

| run | fb SHA-256 (both ROMs) | nonzero px |
|---|---|---|
| 60f, no input | `cb763066498a7d6598cec1873516419866bb245261aada5176cd596eaca85569` | 22762/23040 |
| 180f, no input | `4957685e8610c7a2fd08a559695bb7757c8accdf54d0417d679b5885611f2bf1` | 22762/23040 |
| 600f, no input | `1cf926799cff7d9119d27ca6fde515c0da226eccb342eb0a823e8bbb79733c03` | 19633/23040 |
| 900f, Start 620–632 | `39ffd5eeceadd3dd34a33f90e6c58d813124ce141959aac4a4b2b37ca7e11c49` | 20761/23040 |
| 3600f, Start 620–632 + A 1000–1012 | `88515f4ea0b61c47aac5b15c8d41887719521100f0ee8119676809120285318b` | 15903/23040 |

Screenshots: `build/nacre-test/orig-60.png`, `orig-600.png`,
`orig-start900.png`, `orig-startA3600.png` (rebuilt PNGs identical, not
duplicated). Traces: `build/nacre-test/trace-start900-orig.txt` /
`-reb.txt` (identical), `trace-startA3600-orig.txt` / `-reb.txt`
(identical).

**State flow observed** (from the traces; frame counts are approximate —
the trace logs only on change plus a 60-frame heartbeat, so the *sequence*
is the reliable part):

- Boot: state 0 (frames 0–9) → state 2 TitleScreen (frame 17). Title
  sub-steps: timer 0 (~16f), 1 (~28f), 2 (~10f), 3 (~308f), 4 (~23f),
  5 (1f), 6 (~145f in Start runs; ~985f idle), 7 (~75f, waits for Start).
- **Start pressed at 620–632 → state 3 at frame ~710** (reproduced 3/3
  in later runs; two early runs with the same press went down the idle
  path instead — cause not established, suspect uninitialized RAM in
  Nacre's fresh state, e.g. SRAM/save-data reads; recorded honestly,
  needs a look if it recurs).
- **State 3 + A at 1000–1012 → state 16 (1089) → state 4 (1090, ~900f)
  → state 16 → state 20 (1989) → state 16 → state 15 (timer 29, ~5f)
  → state 16 (timer 1, ~570f) → state 20 → … cycling 20↔16↔15.**
  States visited: `[0, 2, 3, 4, 15, 16, 20]`.
- **Idle (no input):** title → state 16 (1 frame, ~1475) → state 30
  AttractDemo (timer 0 ~25f, timer 1 ~4322f, bank 23) → state 2 again
  (~5835), looping. 7200f hash is the same title hash as slice 1.
  States visited idle: `[0, 2, 16, 30]`.
- **State 3 alone (Start only, no A):** timer 0 (~20f) then timer 1
  stuck for 2800+ frames waiting for input.
- **State 18** (from an earlier multi-press run): timer cycles 3–10
  repeatedly, 1 frame each (per-frame animation loop); transient state
  17 at timer 29 for 2 frames, then back to state 18 timer 1. The
  timer-29-in-state-17 mechanism is **not understood** (state 17's
  table has only 8 entries; timer 29 indexes past it, to bytes at
  `$351f` → target `$cdc8` in WRAM — whether code is copied there is
  unknown). Observed but unexplained; do not build on it.

**Curated in slice 2** (new files `src/stat.asm` 468 lines,
`src/transfer.asm` 420 lines, `src/decomp.asm` 181 lines,
`src/frame.asm` 345 lines, `src/states.asm` 509 lines; `src/main.asm`
now 806 lines, re-split; `src/hardware.inc` gained `rLYC`/`rWY`/`rWX`;
`src/constants.asm` gained `wDecompOutLen`/`wDecompDst`):

- **STAT table corrected: 60 entries (0–59), not 16.** Proof: entry 0's
  code sets `hSTATState=$39` (57); entries 16–59 live at `$030f-$0366`
  and all point at plausible code; the chain runs 57 (`$0397`) →
  58 (`$03a2`) → 59 (`$03ad`) → 1 (`$03ad` sets `hSTATState=1`).
  The 60-entry table is written into `src/main.asm` and verified
  byte-for-byte against the ROM. Shared tails: `$0379` `STAT_Next`
  (inc), `$03e9` `STAT_SetState`, `$0392` `STAT_Prev` (dec). The STAT
  targets `$0367-$0673` are short WX/LYC/BGP/LCDC setters chained by
  those tails. `$03a2`/`$03ad` were the "orphan blocks" slice 1 could
  not place — they are entries 58/59. `$0680`
  `RestorePaletteFromShadow` (reload BGP/OBP0/OBP1 from shadow
  `$da3d`), 5 unidentified bytes at `$068d` kept as `db`.
- **State handlers** (prologues + sub-dispatch tables + bank-0 sub-steps
  in `src/states.asm`): 2 `TitleScreen` (`$340e`, 11-entry table),
  3 `PostStart` (`$359a`, 37 entries), 4 `State04_Intro` (`$28a8`,
  4 entries), 8 `State08` (`$3657`, 3 entries, bank 1), 16
  `State16_Transition` (`$06bd`, **46** entries, not 30 as first
  miscounted), 17 `FileSelect` (`$34df`, 8 entries), 18
  `FileSelectLoop` (`$0692`), 20 `State20_Gameplay` (`$266c`, 27
  entries), 21 `State21` (`$3582`, 9 entries), 22 `State22` (`$3663`,
  8 entries, bank 12), 26 `State26` (`$3679`, 5 entries, bank 12),
  28 `State28` (`$3471`, 6 entries), 30 `State30_AttractDemo`
  (`$290a`, 8 entries, bank 23). Every handler with real work is
  itself a `rst $08` sub-dispatch on `hStateTimer` (`$ff90`); sub-steps
  usually end by calling `IncStateTimer` (`$1d2a`) or setting
  `hGameState` directly. `DispatchState` in `src/main.asm` now uses
  the named labels. Banked sub-step bodies (bank 1 `$49xx-$56xx`,
  bank 12 `$55xx-$59xx`, bank 23 `$73xx-$76xx`) are NOT curated yet.
- **Transfer/decompressor** (`src/transfer.asm`, `src/decomp.asm`):
  `$1d2f` `SeedMul` (seed at `$defe`/`$deff` advanced by `*15625-1`
  mod 65536, 15625 = 5^6 — multiplier verified by hand from the
  add/shift sequence; RNG role inferred, 89 call sites),
  `$1d82` `TransferTable0F` (bank `$0f` table at `$4000`),
  `$1da7` `TransferTable1E` (bank `$1e` table at `$74e5`; 7-byte
  entries, bit 7 of the last byte selects the decompressor),
  `$1df8`/`$1dfd` sprite-table builder (bank `$1b` table at `$7918`),
  `$1e3e` `ResetWindowPos`, `$1e46` `HideWindow`, palette table
  `$1e86` (17 entries × 3 bytes; 16 is the largest index loaded
  directly by any `call LoadPalette`), 5 unidentified bytes at
  `$1eb9` kept as `db`, save routines `$1ebe-$1f99`
  (`EnableSRAM`/`DisableSRAM` via MBC `$0000`, `ValidateSave` —
  save-clear/write at `$1f9a+` NOT curated yet).
  Decompressor `$257b-$266b`: `$257f` `Decompress` (bitstream LZ —
  bit set → literal, bit clear → 2-byte back-reference, length =
  low nibble + 3; ends when DE == BC), `$257b`
  `DecompressPrefixed` (reads the 2-byte length prefix),
  `$25f4` `ExpandRLE`, `$2611` `SwitchBankByE`,
  `$2620` `LookupStreamEntry`, `$263e`/`$264a` bank-9 level dispatch.
- **Per-frame routines** (`src/frame.asm`): `$1643-$17ea`
  (`FrameCopy16f9`, `Frame1663`, `Frame1643`, `FrameCopy16c2`,
  `FrameRetStub`) — transcribed and byte-verified; exact roles beyond
  the call graph are TODO.
- **State names adopted** (trace-verified where stated): 2
  `TitleScreen`, 3 `PostStart`, 4 `State04_Intro`, 16
  `State16_Transition`, 17 `FileSelect`, 18 `FileSelectLoop`
  (inferred), 20 `State20_Gameplay` (inferred: reached after file
  select; exact role unverified), 30 `State30_AttractDemo`.
  States 21/22/26/28 were never visited in any trace; roles unknown.

### State 12 verdict — UNRESOLVED (not proven dead, not proven live)

Searched the whole ROM (all banks) by byte pattern:

- **No direct write of 12 to `hGameState` (`$ff8e`) anywhere.** All
  `ldh [hGameState],a` (`e0 8e`, 23 sites) write values `{1, 2, 3, 4,
  8, $10, $14, $18, $1a, $1c, $1e}` plus variable-A writes at bank 1
  `$597e`, bank 14 `$5e9d`, bank 21 `$78d2`, bank 25 `$45ef`, bank 27
  `$70d6` (values not traced). No `ld a,$0c` is followed by a write to
  `hGameState`. No `ld [hl],a` to `$ff8e` writes 12 (`$09fe` writes
  `$15`=21; `$1d22` is `AdvanceState`).
- **No code is copied to `$c1fe`.** No `ld hl/de,$c1fe`, no
  `ld [$c1fe],a`, no `ld a,[$c1fe]` anywhere. The only `ld bc,$c1fe`
  is at bank 25 `$409e`, inside what decodes as data. Other `fe c1`
  byte pairs (banks 22, 25, 26, 27, 28) are in graphics/data regions.
- **Two plausible reachability paths exist, neither closed:**
  (a) `AdvanceState` increments from 11: states 9, 10, 11 are
  `AdvanceState` in the main table, so reaching state 9 would walk
  9→10→11→12. State 8 is the only known entry to that chain (set
  directly from bank 1 `$4de7`: timer=0, state=8), but state 8's exit
  path is now understood — see below — and whether it ever sets state
  9 is not traced.
  (b) `dec hGameState` from 13: routine `$0d07` (`ld hl,$ff8e;
  dec [hl]`, then bank 12 `call $4b71` + `call $30b8`) and bank-1
  `$4e14` (same decrement). `$0d07` is reached via `$0d1a` and
  `$0d5c`, which are entries 0, 5, 7, 9, 17 of the **C-dispatch table
  at `$0d8c`** (entered via `$0d8a`: `ld a,c; rst $08`; 24 entries
  including state 20 `$0d23`, state 4 `$0d2c`, state 30 `$0d6f`,
  state 26 `$0d81`, soft-reset `$0d6c` = `jp $01fb`). `$0d8a` itself
  is referenced as a table entry in bank 19 (`$5671, $56f7, $5abe,
  $5b31, $5b46, $5bc9, $5c0f`) and via `$0d04` (`jp $0d8a`, called
  only from `$0d56`). Which C values bank-19 callers use, and what
  `hGameState` is then, is **not traced**. Whether any decrement runs
  while state==13 is unknown.
- **Other state writers found:** `$09f0` (called from `$071c`, state
  16 step 0): if `[$c858]==0` and `[$c860]!=0`, sets state 21 (`$15`),
  and increments to 22 if `[$c711]` bit 0. `$0d23` sets state `$14`=20;
  `$0d2c` sets state 4 or 20 by branch; `$0d6f` sets state `$1e`=30;
  `$0d81` sets state `$1a`=26; `$0d76` sets state `$1e`=30.
  `$09eb` sets `hStateTimer=$21` (33) when C==4. `$0c85` sets
  `hStateTimer=$0c` (12).
- **Conclusion:** state 12 is suspected-dead but **not proven**; keep
  it labelled unverified, do not call it a handler. Next slice should
  trace the `$0d8a` C-dispatch callers in bank 19 and whether state
  8's step 2 ever emits state 9.

### State 8, corrected (slice-2 draft had this wrong)

The first slice-2 draft said state 8 switches to bank 12 and its table
entries point into bank-12 data (credits text at `$59a0`) — **wrong**,
caught by the byte-match check: the prologue at `$3657` is
`ld a,$01` (bank 1), not `$0c`. Its table entries `$58f3/$593c/$5977`
are bank-1 code: step 0 is a setup (InitStatePtrs, SGB packet 1, LCD
off, `$1643`, TransferTable1E `$0e`, ClearTilemap9C00, TransferTable0F
`$1e`, then `$5986`); step 1 reads `hJoypadNew`, waits for input
(`ret z`), sets `[$c82f]/[$c835]` = 5 or `$30`, then `IncStateTimer`;
step 2 (`$5977`) loads the next (timer, state) pair from WRAM
`$c80f/$c810` and jumps there — a generic state-transition step, and
how state 8 exits. So state 8 is an input-driven selection screen
(bank 1), role otherwise unknown; it was never visited in traces. The
credits text at bank-12 `$59a0` belongs to states 22/26's bank, not
this one. The `$01fb` entries (states 17 and 28, last/near-last table
entries) are likewise unresolved: `$01fb` is inside `CheckSoftReset`'s
body; whether any timer ever reaches those entries is unverified.

### Mistakes caught by the byte-match check (slice 2)

1. **STAT table is 60 entries, not 58** (and not slice 1's 16):
   bytes `$0363-$0366` (`a2 03 ad 03`) are entries 58 (`$03a2`) and
   59 (`$03ad`) — the two orphan blocks slice 1 could not place.
2. **State 8 switches to bank 1, not bank 12** (see above) — the
   "credits" inference was based on reading the wrong bank's bytes.
3. **mgbdis misaligns by 1 byte after the `$3477` table** (it reads
   `$3483` as part of `ld bc,$b9cd`), so `State28Step0` was generated
   shifted — the real code starts `call SetupNextScreen` at `$3483`.
   Hand-decoded from the ROM bytes and byte-verified. Any region right
   after an `rst $08` table must be re-checked by hand, not trusted
   from the linear sweep.
4. **Raw INCBIN fragments must end exactly at the next section:**
   `Raw bank 0 A2` was 1 byte short (`$889` not `$88a`), leaving `$0fc0`
   (`$b4`) as zeros.
5. The generator script that produced `src/stat.asm` etc. lives in
   `/tmp/gen_slice2.py` — **ephemeral** (`/tmp` may be wiped); the
   durable output is the `src/*.asm` files themselves. The generator
   is deterministic and regenerates all five slice-2 files from
   `build/raw-mgbdis/` + hand-written tables, with the hand fixes
   (state-28 step 0, state 8) patched into it.

## Next slices (priority order)

1. **Banked sub-step bodies** — the bank-0 prologues/tables from slice 2
   call into bank 1 (`$4998-$4b2a` title, `$5131-$56f1` post-Start,
   `$4c1b-$4e90` file-select, `$43f9-$4807` gameplay), bank 12
   (`$55xx-$59xx` states 8/22/26, `$58f3` tilemap loop), bank 23
   (`$73xx-$76xx` attract demo). Carving `banks.asm` for banks 1, 12,
   23. Then the `$0d8a` C-dispatch callers in bank 19 and whether
   state 8's step 2 ever emits state 9 (state 12 resolution), the
   `$0c80-$0dc7` region (including `$0d8a` dispatch + `$09f0`/`$09e1`
   helpers), `$0737+` (state-16 timer-1 chain), `$1f9a+`
   save-clear/write, `$17eb+` frame routines, and the SGB packet table
   in bank `$1e` at `$4000` (not yet touched).
2. **Gameplay code in banks 1–31** beyond the state sub-steps, starting
   with whichever bank state 2's handler calls into (bank 1).

## Not done / blocked

- Nothing is blocked. No GitHub push has been made (needs T's say-so).
- Ghidra was not needed: mgbdis + hand-checking against the bytes
  covered slices 1–2. It may still be useful for banked code later.
- Save RAM (battery) behaviour was not exercised. The SGB packet table
  in bank `$1e` at `$4000` is not yet curated. State 12 is unresolved
  (see Slice 2); the timer-29-in-state-17 oddity and the flaky early
  Start runs (2 of 5 went down the idle path) are unexplained.
- The generator script for the slice-2 files is in `/tmp/gen_slice2.py`
  (ephemeral — see Slice 2 notes); the durable output is `src/*.asm`.
