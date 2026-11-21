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

> SUPERSEDED in slice 3: state 12 is DEAD by mechanism — see the
> Slice 3 section. The two open paths below are both closed there
> (C-dispatch entry state is always 16; state 8 always returns to
> the state it came from). Kept as the record of what slice 2 knew.

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

## Slice 3 — DONE, byte-matching (2026-11-21)

**Curated in slice 3** (~13,180 new source lines; `src/` total now
16,398 lines): `src/bank1.asm` (3,962 lines, bank 1 `$4000-$59ff`),
`src/bank12.asm` (4,441 lines, bank 12 `$4000-$5916`; code ends at
`$5916` `ret`; `$5917-$599f` is data — repeating `4a 4e 4b 4c…` pattern —
and `$59a0+` is credits text, both stay INCBIN),
`src/bank23.asm` (587 lines, bank 23 `$731f-$7716`; `$7300-$731e` is
data, 3-byte records; the `$7722` `rst $08` site stays INCBIN),
`src/bank0slice3.asm` (4,065 lines: bank 0 `$0737-$0df3` state-16
chain + C-dispatch, `$1f9a-$257a` save + stream code, `$26b5-$28a7`
state-20 step 0, `$2920-$340d` mid code), `src/sgbpackets.asm` (117
lines: bank `$1e` `$4000-$40df`, 112-entry SGB packet pointer table,
all entries validated — target in `$40e0-$7fff`, packet-count byte
& 7 in 1..7; packets at `$40e0+` stay INCBIN). `src/banks.asm`
regenerated fragment-aware (INCBIN only for the gaps); `src/main.asm`
raw A2 shrunk to `$0df4-$0fc0`, raw D2/D3/D4 deleted;
`src/hardware.inc` gained `rSC`, `rDIV`, `rNR14`, `rNR42`. Generator
is durable this time: `tools/gen_slice3.py` (carve + `rst $08`
tables + data blobs + entry labels; rerun with
`python3 tools/gen_slice3.py`), `tools/survey3.py` (byte-pattern
survey helper), `tools/gen_banks.py` rewritten fragment-aware.
`tools/gb_probe17.c` is a one-shot cycle-stepping probe for the
timer-29 oddity (see below); `tools/gb_headless.c` had a real bug
fixed (see below).

**Byte-match proof:** clean `make` rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs
(`build/game.gb: OK`, `BYTE-MATCH: rebuilt ROM == original ROM`).

### State 12 verdict — DEAD (by mechanism, not by absence)

Slice 2 left state 12 unresolved with two open paths. Both are now
closed with positive evidence; the verdict rests on the mechanism,
not on never having seen the state.

- **Complete writer inventory for hGameState (`$ff8e`).** 23×
  `ldh [hGameState],a`: direct values {1, 2, 3, 4, 8, $10, $12, $14,
  $18, $1a, $1c, $1e} plus variable-A at bank 1 `$597e` (the
  `$c810` pair — state 8's return, see below). 4× `ld hl,$ff8e`:
  `$09fe` writes $15 (21), `$0d07` dec (C-dispatch), `$1d22`
  AdvanceState inc, bank 1 `$4e14` dec (file-select step 3).
  Zero `ld [$ff8e],a`. Zero credible `ldh [c],a` with C=$8e (the
  six `0e 8e` pairs sit in tile data in banks 20/24, which are
  never selected). No writer of 9, 12, or 13 exists anywhere in
  the ROM.
- **Path (b) dec-from-13 via C-dispatch: CLOSED.** The C-dispatch
  table at `$0d8c` has 23 entries (0–22): 0 `$0d07` (dec), 1
  `$0d1a` (store B, call `$24e7`, dec), 2 `$0d23` (state 20), 3
  `$0d2c` (state 4 or 20), 4 `$0d2b` (no-op), 5–18 alternating
  `$0d07`/`$0d1a` (all dec), 19 `$0d6c` (`jp $01fb` soft reset),
  20 `$0d6f` (state 30), 21 `$0d23` (state 20), 22 `$0d81`
  (state 26). The only entry to `$0d8a` is via `$0d04`, reached
  only from `$0cec` (sole `call $0cec` is at `$071f`,
  TransitionStep0, state 16 timer 0) plus re-entrant
  `jp $0d04`/`call $0d04` inside `$0d2c` itself. Entry state is
  therefore always 16; at most one dec per frame (dec entries
  `pop af; ret`); a dec gives 15, then AdvanceState 15→16. State
  13 can never be current at dispatch entry. The bank-12 queue
  table at `$4f97` (331 entries, indices 0–330) has C ∈
  {1,2,3,4,$14} only: C=1 → `$0d1a` → load stage B via bank-5
  `$24e7` (reads the stage entry from bank-5 `$4000+[$c829]*2`;
  does NOT write hGameState), then dec 16→15; C=2 → state 20;
  C=3 → `$0d2c` walk (B==0 → state 4; B==4 + `wSGBFlag` bit 4 →
  advance + re-dispatch; else advance + re-dispatch then
  `$0dc7`); C=4 → no-op; C=$14 → state 30. This is the traced
  16↔15 cycling. The seven `8a 0d` pairs in bank 19 (`$5671`,
  `$56f7`, `$5abe`, `$5b31`, `$5b46`, `$5bc9`, `$5c0f`) are NOT
  callers: they sit inside compressed/data regions (mgbdis
  decodes garbage there, e.g. `adc d; dec c`); bank 19 is NEVER
  selected by any `ld a,$xx / rst $10` in the ROM; no
  `call $0d8a`/`jp $0d8a` exists outside `$0d04` itself. (Slice-2
  confusion noted: bank keys were decimal, not hex — "13: 1"
  meant bank 0x0d, not 0x13.)
- **Path (a) AdvanceState from 11 via state 9: CLOSED.** State 9's
  only possible producer is the (`$c80f`=timer, `$c810`=state)
  pair consumed by state-8 step 2 (`$5977`). State 8 is entered
  ONLY via bank 1 `$4de7` (sole write of 8), the tail of the
  `$4dc9` routine (FileSelect step 1, `$4d66`): it writes
  `[$c80f]=6`, `[$c810]=current hGameState` (17 in that flow),
  then sets state 8 — so every state-8 entry overwrites the pair
  first, and state 8 always returns to the state it came from
  (17). Nothing rewrites the pair during state 8: state-8 steps
  don't touch it, and the per-frame routines (`$1643-$17ea`,
  `src/frame.asm`) are pure memory copies — no stream-code calls,
  no `$c80f`/`$c810` writes (re-verified this slice). Other
  `$c810` writers can't be consumed by step 2: bank 0 `$2252`
  gives {0,2} only (bank-1 tables `$7802`/`$780e`/`$781a` are the
  only sane ones across all 32 banks); bank 12 `$52ff` gives 0–7
  (bits 4–6 of a level-data byte); bank 0 `$2480` gives a bank-14
  level-data byte used immediately as a ROM bank number (overwritten
  by `$4dc9` before any state-8 entry).
- **Residue (stated honestly):** the proof is static. Three
  `e0 8e` pairs in data-looking regions (bank 0x15 `$78d2`,
  bank 0x19 `$45ef`, bank 0x1b `$70d6`) are classified as data,
  not code, on decode + bank-mapping evidence (0x15/0x19 never
  selected; 0x1b mapped only for the `$7918` sprite-table data
  read at `$1e08`). A full-execution trace of a complete
  playthrough would be the final confirmation; Nacre fuzzing this
  slice never observed states 8/9/12 either (state 8 itself was
  not reached — file-select confirmation flow needs the right
  button timing; see Next slices).

### Timer-29-in-state-17 — RESOLVED (not a bug, never jumps to WRAM)

- Slice 2 observed state 17 at timer 29 for 2 frames and
  hypothesised `FileSelectTable[29]` → bytes at `$351f` →
  `$cdc8` (WRAM). Reproduced in slice 3 (idle + Start at
  2500–2511 path, frame 4108) and probed with a cycle-stepping
  harness (`tools/gb_probe17.c`): WRAM `$cc00-$ce00` is all
  zeros at the moment, but **the CPU never executes at `$cdc8`**
  (no WRAM PC in `$c000-$dfff` at all in the window) and never
  even enters `FileSelect` (`$34df`) while the timer is 29. The
  three `rst $08` executions in the window are sub-dispatches
  inside the running stream-loader routine (bank switches
  2→3→12), not the state dispatch. Mechanism: the state variable
  changes mid-routine (18→17→18) while the CPU is still inside
  the long stream-loader routine; the main loop re-dispatches
  only after the routine returns, by which time the state is 18
  again (AdvanceState at cycle ~27412: 17→18, timer reset 0→1).
  `FileSelectTable` is therefore never indexed with 29. The two
  timer values that look alike are different things: timer 29
  (decimal, `$1d`) is set by `$256e` at the end of a stream
  routine and is a VALID index into the 46-entry State16Table
  (entry 29 = `$0ab5`); timer `$29` (41 decimal) is set by
  `$08c0` in state 16's step `$083e` and is the saved
  continuation for state 17's return — `FileSelectStep3`
  (`$4e06`) restores it from `[$c70b]` and decs 17→16.
  The one instruction that decs 18→17 inside the loader was not
  identified (candidates: bank-1 `$4e14` via a FileSelectStep3
  call chain, or `$0d07` via a re-entrant C-dispatch); it does
  not matter for the verdict, since the `$cdc8` jump provably
  never happens.
- **`$01fb` table entries (states 17/28) — RESOLVED.** `$01fb`
  is mid-`CheckSoftReset`: `ld a,$5f; call SendSGBPacketIfSGB`
  — jumping there skips the button/state guards and runs the
  reset sequence straight to state 2. In state 17 timer 5 is
  UNREACHABLE (steps go 0→1→2→3; step 3 restores `[$c70b]` and
  decs to 16). In state 28 timer 5 IS reachable and was observed
  dynamically: down+A in state 28 (file 1 → +3 timer bump in
  `State28Step1` `$4c1b`, timer 1→4; step 4 `$4ca2` waits for
  `[$ff95]==$2d`, then incs to 5) → frame 5945 timer 5 → frame
  5952 state 2 timer 0. The entry is a live reset exit in state
  28, dead in state 17.

### Flaky Start — NOT REPRODUCIBLE, cause narrowed

- The Start-900 test (Start 620–632) ran 10/10 identical on the
  original ROM: state 3 at frame 710 every time. Nacre's boot
  state is fully deterministic (`calloc` + `memset` WRAM/HRAM,
  SRAM filled `0xFF` in `gb_cart.c`/`gb.c`), so the "uninitialised
  RAM" hypothesis is ruled out for the current harness/Nacre
  build. Most likely the slice-2 early runs used an earlier
  harness build (the press-spec feature was being developed
  then). Recorded as closed-but-not-fully-explained; no evidence
  of a ROM bug.
- **Real harness bug found and fixed (`tools/gb_headless.c`):**
  two press windows for the same button clobbered each other —
  the later entry overwrote the earlier one each frame, so
  `start:620:632,...,start:2500:2512` silently dropped the first
  press and the game idled. Windows now OR (all buttons cleared,
  then every active window sets its button). Single-window specs
  are unaffected: slice-2 hashes reproduce exactly after the
  fix (600f `1cf92679…`, 900f `39ffd5ee…`, 3600f `88515f4e…`).
  This bug is also the likely explanation for the slice-2
  "multi-press run" going down the idle path (its spec had two
  Start windows) — the state-17-timer-29 observation came from
  that idle-path run, which is why it was hard to reproduce.

### Nacre results (slice 3)

- Slice-2 tests re-run on the slice-3 build, original vs
  rebuilt identical (framebuffer SHA-256 + full state traces):
  600f no-input `1cf926799cff7d9119d27ca6fde515c0da226eccb342eb0a823e8bbb79733c03`,
  900f Start `39ffd5eeceadd3dd34a33f90e6c58d813124ce141959aac4a4b2b37ca7e11c49`,
  3600f Start+A `88515f4ea0b61c47aac5b15c8d41887719521100f0ee8119676809120285318b`.
- **Further into gameplay:** Start 620–632 + A 1000–1012 +
  Start again 2500–2512 (fixed harness), 12000f: original and
  rebuilt identical (fb `92d2e18501ff9a2670d0b3260ed6dc83e53ff1e1b9a1f0ff9a5ea5e4b6aacdff`,
  traces identical). States visited `[0, 2, 3, 4, 15, 16, 20, 28]`:
  title → post-start → intro → gameplay/demo loop → **state 28
  screen at frame 5645** (file-management screen; waits for
  input). With down+A at 5800/5900 it reaches state 28 timer 5
  and soft-resets to state 2 (see `$01fb` above), then idles
  into attract (state 30) and back to title. The rebuilt ROM
  provably gets as far as the file-management screen and the
  soft-reset path.
- Idle + Start-at-2500 path (the old buggy spec's effective
  input), 6000f: states `[0, 2, 16, 17, 18, 20, 30]` — this is
  the run that reproduces state 17 timer 29 (frame 4108).

### Other findings from the carve (verified from code)

- Bank 1 `$4000`: 5-entry hStateTimer dispatch (entries `$400d`,
  `$406c`, `$41cf`, `$411b`, `$4142`) — state 24's handler when
  bank 1 is mapped. Bank 12 `$4000`: `call $4009; ld hl,$c7f7;
  jp $16c2` — state 24 when bank 12 is mapped (after states
  22/23). `$4009` pushes HL/DE into `$c7f7` + a byte from
  `$d93d+[$c725]`.
- Bank 1 `$400d` (dispatch 0): `call $1ec0; xor a; call $1ebf;
  ld hl,$bbc0…` (save-related).
- Bank 12 `$58f3-$5916`: tilemap-fill loop using `$c809`/`$c80a`
  (decompressor output), ends `ret` at `$5916`.
- Bank 23 `$73b2`: `xor a; ld [$c80f],a; ld [$c809],a;
  dec [$c85c]` (attract demo consumes queue entries).
- Bank 0 `$20d3` dispatcher: `xor a; call $30f3` (reads stream
  byte at `[$c80b]+A`, no bank switch), then type codes
  {1→`$21f1`, 3→`$2317`, 4→`$237f`, 7→`$23c6`, $0b→`$2109`,
  $11→`$2196`, $13→`$21b8`}. `$21f1` computes the pair via
  bank-1 tables `$7802` (B), `$781a` (timer), `$780e` (state).
- Bank 0 `$0cec` (called only from `$071f`): sets `[$c856]=$30`,
  `[$c857]=$b4`, calls bank-1 `$495c`, then falls through to
  `$0d04` → C-dispatch.
- `$0737+` (TransitionStep1) is a big level-load routine (clears
  VRAM, bank-1 `$1c29`, bank-12 `$432c`/`$46a9`/`$47a7`, bank-7
  `$7169`); at `$078c` it sets timer=2.
- `$09d5-$09ed`: queue-advance helper — sets timer `$2a` (42),
  advances the queue index, fetches next (C,B); if C==4 sets
  timer `$21` (33).
- `$09f0` CheckSaveForState21: if `[$c858]==0` and `[$c860]!=0`
  sets state 21/`$15`, increments to 22 if `[$c711]` bit 0.
- State-16 step `$083e` (timers 3/5/7/9): if `[$c82b]` bit 3
  clear → save timer to `[$c70b]`, set timer `$29` (41), ret;
  if set → save timer, `jp $1d22` (AdvanceState 16→17).
- Bank 1 `$48d0-$48ff` is DATA (counting sequence `30 31 32…`),
  not code — mgbdis mis-decodes it.
- Bank 12 `$4f97` table is 331 (C,B) pairs (indices 0–330);
  bytes after suggest a second table/script. It is still
  emitted as decoded code in `src/bank12.asm` (byte-identical
  but misleading) — a next slice should emit it as `db` pairs.
- `$0d2c` re-dispatch subtlety: nested dec returns into
  TransitionStep0's tail at `$0722` (InitStatePtrs,
  IncStateTimer→1, bank-7 call `$7168`, fall to `$0737`) with
  state 15, rather than to MainLoop. First-level dec returns to
  MainLoop.
- `$256e` sets timer `$1d` (29) at the end of a stream routine
  — the source of timer 29 in state 16.

### Mistakes caught by the byte-match check (slice 3)

1. mgbdis `@+/-$off` notation is relative to the instruction's
   own address, not PC-after-fetch: target = addr ± printed
   number (first draft used addr+2±off, mismatched 10 bytes:
   bank 1 `$48e0`, `$48e8`, `$52ad`; bank 12 `$4d8f`, `$4da4`,
   `$4dc0`, `$4dc3`, `$4e08`, `$4e0e`, `$4f04`). Note: the
   `$48df`/`$48e7` "jr" sites are actually data bytes (`30 31
   32…` counting sequence at bank 1 `$48d0+`), so targets there
   are meaningless — byte-match is what matters.
2. Raw A2 length `$1cc` vs correct `$1cd` (missed byte `$0fc0` =
   `$b4`).
3. `rDIV`/`rSC`/`rNR14`/`rNR42` missing from `hardware.inc`.

## Slice 4 — DONE, byte-matching (2026-11-21)

Code carved (`src/` 16,398 → 19,865 lines), all byte-matching
(SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero
diffs):

1. **New tool `tools/gb_rd.py`** — recursive-descent disassembler.
   mgbdis linear-sweeps from `$4000`, so one embedded data byte
   or `rst $08` table throws its alignment off for the rest of
   the bank (bank 2's sweep was misaligned before `$45a9`;
   slices 2–3 hit the same after `$3477`). `gb_rd.py` decodes
   one instruction at a time from ROM bytes using mgbdis' own
   opcode tables and walks control flow from seeds. Key facts:
   jr target = addr + 2 + s8 (mgbdis prints `@+/-$off` relative
   to the instruction's own address); `rst $08` is an inline-
   table dispatch (bytes after are a dw table, not code; table-
   entry routines `ret` to the rst site's caller, no fall-
   through); `rst $10` is the bank switch (falls through).
   Two bugs found and fixed during development: conditional
   `ret` must fall through (first version treated all rets as
   terminal, which under-counted bank 3's `$45a9` to 6 bytes);
   the `jr` fall-through logic for unconditional jr.
2. **Bank 5 `$4000-$40d3`: the 106-entry stage pointer table**
   (dw, generated by `tools/gen_slice4.py`). Run 0: 45 entries
   (indices 0–44) → bank 5, `$4200-$7b64`; run 1: 35 entries
   (45–79) → bank 6, `$4000-$71a1`; run 2: 26 entries (80–105)
   → bank 18, `$4000-$61b2`. `$24e7` LoadStage (bank 0, already
   curated) reads entry `[$c829]`; `SwitchBankByE` (`$2611`)
   picks the bank by index. Stage data is compressed level
   data (5-byte header + RLE + LZ + patch list) and stays
   INCBIN. Bank 6 `$4000` starts `03 0b 16 96…`, bank 18
   `$4000` starts `02 17 04 c8…` — plausible stage headers
   (unverified).
3. **Banks 2/3 stream engine** (`src/bank2.asm`,
   `src/bank3.asm`): timer-callback stubs (`$4003`/`$4000`),
   the stream command engine `$4010-$43af` (byte-identical
   between banks 2 and 3; bank 2's own dispatch never targets
   `$4142-$415b`, so that sub-range aligns on bank 3's walk —
   bytes verified identical), stream tick `$45a9-$47fb` (bank
   2, `StreamDispatch` at `$4744`: a `jp z, $40xx` chain over
   a type byte into ~17 handlers) / `$45a9-$48f0` (bank 3,
   `Bank3_TimerTail` at `$481e`), bank-2 stream restart
   `$6212-$6491`, bank-3 sound init + tick `$76eb-$78af`
   (`SoundInit` writes rNR52/rNR50/rNR51/rNR30/rNR32, sets
   `$df00-$df66`). Bank 2 `$4003`: `call $45a9; jp $6212`.
   Bank 3 `$4000`: `jp $76eb`; `$4003`: `call $45a9; call
   $7739; jp $481e`. No `jp (hl)` in any carved range (the
   two `0xE9` bytes found — bank 2 `$6296`, bank 3 `$4631` —
   are jr offset immediates, not `jp (hl)`). No `rst $08`
   sites in the banks 2/3/7 walks. Handler roles beyond
   `$4010` (LoadPtr) are NOT individually verified — labels
   are address-derived (`Bank2_StreamOp_*`).
4. **Bank 7** (`src/bank7.asm`, 53 → 755 lines): `$7168`
   (1-byte `ret`, `Bank7_Noop`, called from TransitionStep0
   tail) + `$7169-$71b9` stage-RAM clear (memsets `$dd17`
   len `$9c`, `$c117` len `$5b`, clears `$ff91` len 4, copies
   16 bytes `$7394→$dd59` and 4 bytes `$74ee→$dd72`, sets
   `[$dd69]=[$dd59]`, `[$dd7a]=$60`, `[$c0a5]=[$c1bf]=0`,
   `[$dd22]=$ff`); extension: `$4794-$480d` + `$6ea9-$6ed1` +
   `$6f2e-$6f61` (one routine, three spans; clears `[$ff92]`
   bit 0, loads a pointer from `[$c215]`; no call site in
   curated code, role unverified) and `$77a9-$7aba` (stream/
   stage index setup, two entries `$77a9`/`$78ba` called from
   bank-0 `$3323`/`$3331`). `$6f62` is NOT carved: its walk
   hits `rst $08` at `$6f74` and `gb_rd` has no rst-$08 table
   handling yet — slice 5.
5. **DATA fixups** (spliced into the slice-3 files by
   `tools/gen_slice4.py`, idempotent): bank 1 `$48cb-$48f3`
   as `db` (41 bytes: five 4-byte records + counting sequence
   `$30-$43` at `$48df-$48f2` + `$9d` at `$48f3`); bank 12
   `$4e55-$52d4` as `db` — the 331-entry state-16 queue table
   `$4f97-$522c` as (C,B) pairs (C histogram {2:101, 1:101,
   3:68, 4:35, 20:26}, B range 0–203; C meanings from the
   C-dispatch table at bank-0 `$0d8c`) plus the flanking
   walk-verified dead data `$4e55-$4f96` and `$522d-$52d4`
   (a second table of repeating `(02 xx 01 xx 04 xx)`
   records). A recursive-descent walk of bank 12 from all
   known entries reaches `$4e15-$4e54` and `$52d5+` but
   NOTHING in `$4e55-$52d4` — the whole span is provably dead
   data. The `$4e55-$4f96`/`$522d-$52d4` tables' internal
   record structures are unanalyzed (plain `db` blobs).

**Corrections to the task's stated ranges** (recorded here so
they are not re-"fixed" later):
- Bank-1 "$48d0-$48ff counting data as db" was wrong at the
  tail. `$48f4+` is LIVE CODE: `call $48fd` at bank-0 `$0a8d`
  with bank 1 mapped (`ld a,$01; rst $10` at `$0a8a-$0a8c`),
  and a recursive-descent walk from `$48f4`/`$48fd` aligns
  exactly with the existing decode. Correct data range is
  `$48cb-$48f3`.
- Bank-12 "$4f97 queue table as db pairs" — the table proper
  is `$4f97-$522c`, but the splice had to cover the whole
  dead span `$4e55-$52d4`. Reason: mgbdis decoded phantom jr
  instructions inside `$4e55-$4f96` (e.g. at `$4f78`
  targeting `$4fda`, `$4f7e` targeting `$4fc0`) whose labels
  sit inside the table span; moving those labels would change
  jr offset bytes and break byte-match. Converting the whole
  walk-verified dead span removes them cleanly.

**What the byte-match check caught in slice 4** (all fixed,
all worth not repeating):
1. New `.asm` files must be INCLUDED from `src/main.asm` —
   first build left all carved regions as zeros (4,661
   differing bytes, first cluster at bank 2 `$4003`).
2. RGBDS section names must be unique — both engine carves
   were titled "Bank 2/3 stream command engine"; renamed to
   bank-specific titles.
3. Global `::` labels must be unique — `StreamOp_*` collided
   between bank2/bank3; renamed to `Bank2_StreamOp_*` /
   `Bank3_StreamOp_*`.
4. A jr targeting an address with a named label must use the
   named label, not the `jr_BBB_AAAA` label (5 undefined-
   symbol link errors, e.g. `jr_002_4629` — `$4629` has named
   label `Bank2_StreamTickLoop`, so the jr_ label was never
   emitted). Fixed in `emit_carve`.
5. `tools/gen_banks.py` prints to stdout — regenerate with
   `python3 tools/gen_banks.py > src/banks.asm`, not bare.
   Running it bare once left the old `src/banks.asm` in place
   (link failed on the overlapping bank-7 section) while the
   stale `build/game.gb` still sha1-matched — a stale
   artifact is not proof; always `rm build/game.gb` before
   the verifying `make` when a link step failed.

**Nacre regression** (orig vs rebuilt, identical in every
case; artifacts in `build/nacre-test/slice4/`):
- 600f no input: fb `1cf926799cff7d9119d27ca6fde515c0da226eccb342eb0a823e8bbb79733c03`.
- 900f Start 620–632: fb `39ffd5eeceadd3dd34a33f90e6c58d813124ce141959aac4a4b2b37ca7e11c49`.
- 3600f Start 620–632 + A 1000–1012: fb `88515f4ea0b61c47aac5b15c8d41887719521100f0ee8119676809120285318b`.
- 12000f Start 620–632 + A 1000–1012 + Start 2500–2512:
  fb `92d2e18501ff9a2670d0b3260ed6dc83e53ff1e1b9a1f0ff9a5ea5e4b6aacdff`,
  traces identical, state 28 at frame 5645 (slice-3 values
  reproduced exactly). Re-run on the final build (after the
  bank-7 extension) reproduces it exactly: same fb
  `92d2e185…`, traces identical; the state-8 7000f run was
  also re-verified identical on the final build.

**Harness: SRAM save/load** (`tools/gb_headless.c`,
optional trailing args `save_in.sav save_out.sav`; always
prints `save_dirty` + `save_size`). Nacre exposes
`gb_save_*` in `include/gb.h` (`gb_cart.c`); DK94 save is
8 KiB. A plain title run writes nothing (`save_dirty: 0`).

**Gameplay, verified live** (all orig-vs-rebuilt identical:
framebuffer hashes, state traces, and SRAM dumps):
- **State 8 is LIVE.** Path: Start 620–632, A 1000–1012,
  Start 2500–2512 → state 28 at 5645; Down 5700–5712,
  Down 5800–5812 (file 0→1→2), A 5900–5912 → state 8
  timer 0 at frame 5900; A 6100–6112 → state 8 timer 2 at
  6100, back to state 28 timer 0 at 6101. Matches the
  disassembly exactly: state-28 step 1 (`$4c9e`) with file
  2+ jumps to the `$4dc9` block, which stores the
  `($c80f,$c810)` = (timer 0, state 28) pair and sets state
  8; state-8 step 1 (`$593c`) takes A/B/Select/Start (`$0f`)
  → `IncStateTimer` (8:1→2); step 2 (`$5977`) loads the pair
  and returns to state 28. State 8's Up/Down adjusts
  `[$c818]` (0–9 wrap) — a selection inside the dialog;
  its exact meaning (confirm value) is unverified. fb
  `92d2e185…` (same final screen as the 12000f run).
  Also verified: state 8 is reachable from state 17 the
  same way (file 2+ + A at `$4dc9`, pair = (6, 17)) — by
  code reading only; the live state-17 entry is a 4-frame
  transient in the attract loop (see below), so the live
  test used state 28.
- **Save write (state 28, file 1 + A).** Down 5700–5712
  (file 1), A 5800–5812 → `$4cbe` save write → step 4 waits
  for `[$ff95]==$2d` → step 5 (`$01fb`) → soft reset to
  title (state 2) at frame 5852. SRAM dump (8 KiB,
  byte-identical orig vs reb, 1,622 non-`$ff` bytes):
  `$a000-$a4af` zeroed by the `$1f9a` clear, `$bffa` =
  `09 04 00 02 00 08` (the ROM `$2017` signature template),
  `$bff6`/`$bfd8` = `02 07` markers, `$bfbe` file data
  `00 01 04 40 …`. The save VALIDATES: `ValidateSave`
  (`$1ed2`) passes on a reload (a no-input boot with this
  SRAM shows `save_dirty: 0`).
- **Save-load boot.** Booting with the file-1 save + Start
  620–632, A 1000–1012 follows the fresh path (3 → 16 → 4
  → 16 → 20 → attract loop → state 28 at 5645) — it does
  NOT go to state 21/22. Mechanism, verified statically:
  `$09f0` (called from TransitionStep0 `$071c`) fires state
  21 only when `[$c858]==0` AND `[$c860]!=0`, and `[$c858]`
  is set to `$ff` by the state-16 step-12 queue-advance
  (`$094d`, reached by fall-through from `$08f7`) on every
  attract cycle — so the continue condition never holds in
  the attract flow. `[$c860]` is the current stage, set in
  state 20 (`$26e5`/`$2745`); `[$c858]` is cleared only by
  boot (WRAM = 0). States 21/22 remain unvisited live.
- **First stage past state 20 (state 28, file 0 + A).** A
  5700–5712 in state 28 → step 2 (wait) → step 3 (`$4cb6`,
  state 16) → state 20 at frame 5747, then the
  20↔16↔15 cycle continues (state-20 visits ~145f, timer-29
  state 15 between). fb `6dbff66a77f32b77c56cd4e28d3855dc805a02193db9f82144ffa2d74474680f`
  (6,190/23,040 nonzero pixels), traces + SRAM identical.
- **State-20 visits in this flow are attract demos, not
  player-driven gameplay.** Holding Right 5800–5890 + A
  5850–5862 during the state-20 visit (5747–5892) produces
  a byte-identical fb and trace to the no-input control
  (`6dbff66a…`). Player control in state 20 is NOT yet
  demonstrated — the real new-game path (a stable state-17
  file select, or a save with actual stage progress) is
  still unfound. State 17 appears only as a 4-frame
  transient (timer 29) inside the attract loop: title
  idles → 16 → 30 (attract) → Start during attract → title
  → 16 → 20 → 18 → 17 (timer 29, ~4f) → 18 → title ….
  The `$09f0`/`[$c858]` blocker above is the same reason
  the continue flow never engages.

**Inferred, not verified** (do not present as settled):
- Stream-op handler roles beyond `$4010` (LoadPtr).
- Bank 2 `$4142-$415b` is code (byte-identical to bank 3,
  reached there) but never targeted by bank 2's dispatch
  from the `$4003` seed — why is unverified.
- Bank 12 `$4e55-$4f96` / `$522d-$52d4` table structures.
- Bank 7 `$4794` role; `$77a9`/`$78ba` roles beyond "stream
  index setup, called from bank-0 `$3309` area".
- State 8's `[$c818]` selection meaning; state 21/22
  contents live; the stable state-17 entry; player-driven
  state-20 gameplay.

## Slice 5 — DONE, byte-matching (2026-11-21)

Code carved (`src/` 19,865 → 21,640 lines), all byte-matching
(SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero
diffs):

1. **Tooling: `rst $08` table handling in `tools/gb_rd.py`.**
   `walk()` already decoded `rst $08` tables (reads the dw
   entries after the rst, walks each target); the table-entry
   cap was raised 64 → 128 because bank 23's table has 74
   entries. A table ends at the first word that is not a
   plausible address. `tools/gen_slice5.py`: `emit_carve()`
   now emits `rst $08` tables as `dw` lines.
2. **Bank 7 `$6f62`** (`src/bank7slice5.asm`, 557 lines).
   Walk: 348 instructions (464 with hand-seeded gap seeds),
   1 `rst $08` site at `$6f74`, 4 entries `$6f81`, `$6f96`,
   `$4121`, `$7edd`. Spans: `$4016-$4084`, `$4121-$4132`,
   `$4157-$41a9`, `$41c9-$41dc`, `$480e-$4826`, `$6572-$6580`,
   `$68ad-$68c3`, `$6b0a-$6b54`, `$6f62-$6f74`, `$6f81-$7000`,
   `$7edd-$7f0c`. Reachability: `$4016` ← `jp z` from `$41cd`;
   `$480e` ← call from `$401f`; `$6572` ← `call c` from
   `$4815`; `$68ad` ← call from `$4016`; `$6b0a` ← call from
   `$4022`; `$4121`/`$6f81`/`$6f96`/`$7edd` reachable only
   via the `rst $08` table. All spans end in `jp hl`
   (computed return). `$7f0d` decodes as data (`db $10`) —
   carve ends at `$7f0c`. Prologue: `ld a,[$dd41]; rla;
   jr c,$6fad; ld hl,$dd40; dec [hl]; ret nz; ld hl,$6f79;
   push hl; ld a,[$dd41]; rst $08`. The return code at
   `$6f79` **overlaps** table entries 2–3: bytes
   `21 41 dd 7e ee 01 77 c9` are both `dw $4121, $7edd` and
   `ld hl,$dd41; ld a,[hl]; xor $01; ld [hl],a; ret`
   (verified from ROM bytes) — `emit_bank7_6f62()` emits
   entries 0–1 as `dw` and entries 2–3 as the return-code
   instructions producing the same bytes, with a ROM-bytes
   assertion. Gaps `$4085-$4120`, `$4133-$4156`,
   `$41aa-$41c8` (unreached by the `$6f62` walk alone)
   decode as clean code merging exactly with the `$4121`
   walk (341 instructions from those seeds, no data notes;
   `$408d` jumps to `$41aa`, `$41aa` code jumps back to
   `$408f`); seeded by hand in the generator — most likely
   `jp hl` continuations, exact entry mechanism unverified.
   Combined walk gives one contiguous span `$4016-$41dc`
   (455 bytes).
3. **Bank 23 `$7722`** (`src/bank23slice5.asm`, 1,201 lines).
   Walk: 1,110 instructions, 74-entry table at
   `$7723-$77b6` (ends at first invalid word `$013e`),
   handlers `$77b7-$7e11` one contiguous span (1,627 bytes).
   Prologue `$7717-$7722`: stores HL to `$ca6a`/`$ca6b`,
   `A=[HL]`, `rst $08`; called from `$7707` inside the
   `$76f1` loop (iterates `$c200` records, 16 of them). Two
   bank-0 calls `$106e`, `$169c` (noted as outside-window
   targets; normal).
4. **Ranges** (`tools/gen_banks.py` CARVED): bank 7 added
   `(0x4016,0x41DD)`, `(0x480E,0x4827)`, `(0x6572,0x6581)`,
   `(0x68AD,0x68C4)`, `(0x6B0A,0x6B55)`, merged
   `(0x6F2E,0x7001)`, `(0x7EDD,0x7F0D)`; bank 23 added
   `(0x7717,0x7E12)`. `src/main.asm` now INCLUDEs
   `bank7slice5.asm` (after `bank7.asm`) and
   `bank23slice5.asm` (after `bank23.asm`). Labels are
   address-derived (`Bank7_6F62`, `Bank7_6F62Return`,
   `Bank7_4016`, `Bank7_4121`, `Bank7_480E`, `Bank7_6572`,
   `Bank7_68AD`, `Bank7_6B0A`, `Bank7_6F81`, `Bank7_6F96`,
   `Bank7_6FAD`, `Bank7_7EDD`, `Bank23_7717`); roles beyond
   call-site notes are unverified.

**Byte-match on first try** — `rm build/game.gb && make` →
SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` clean.

**What the byte-match check caught in slice 5** (all fixed,
all worth not repeating):
1. An edit to `tools/gen_banks.py` CARVED nearly dropped
   the existing `(0x6EA9,0x6ED2)` range (slice 4's bank-7
   extension) — it was restored. Verify CARVED against the
   previous version on any future edit; a dropped range
   silently reverts carved code to zeros.
2. Nothing else: no link errors, no stale-artifact trap
   this slice (the `rm build/game.gb` before the verifying
   make was done first).

**Harness: WRAM watch** (`tools/gb_headless.c`). `GB_WATCH`
   env var — comma-separated hex WRAM addresses in
   `$c000-$dfff`, up to 8 (e.g.
   `GB_WATCH=c858,c860,da4b,c711,c712`) — values appended to
   every trace line so a state transition can be read against
   the flags that caused it; unset = trace format unchanged.
   Rebuilt with the documented command in the file header.

**Nacre regression** (orig vs rebuilt, identical in every
case; artifacts in `build/nacre-test/slice5/`):
- 600f no input: fb `1cf926799cff7d9119d27ca6fde515c0da226eccb342eb0a823e8bbb79733c03`.
- 900f Start 620–632: fb `39ffd5eeceadd3dd34a33f90e6c58d813124ce141959aac4a4b2b37ca7e11c49`.
- 3600f Start 620–632 + A 1000–1012: fb `88515f4ea0b61c47aac5b15c8d41887719521100f0ee8119676809120285318b`.
- 12000f Start 620–632 + A 1000–1012 + Start 2500–2512:
  fb `92d2e18501ff9a2670d0b3260ed6dc83e53ff1e1b9a1f0ff9a5ea5e4b6aacdff`.
- s8 7000f (state-8 path): fb `92d2e185…` identical.
- f0 7000f (state-28 file 0 + A): fb `3390d76364f76cdfc6efd694c3ad9ed008d864289c12e65bd6e0ef10ced78985`
  identical (differs from slice 4's `6dbff66a…` only because
  slice 4 measured at a different frame count).
- f1 7000f (state-28 file 1 + A): fb `1cf92679…` identical.
- 30000f idle (new): fb `40cefdae99c7d9497dd12f1023aef47cf2f92b395439f1859a3fd6ed021f2140`
  identical, traces byte-identical.
- Right 9450–9750 during a real-stage visit (new): fb
  `89ce425cf8593fc3185e58f76e3e99d502e93679a3739991811777b6fa0e59c4`
  identical, traces byte-identical.
The f0 trace re-confirms state 28 at frame 5645 and state 20
at 5747.

**Gameplay, verified live** (all orig-vs-rebuilt identical:
framebuffer hashes, state traces, screenshots):

- **State 17 is the PAUSE menu — stable entry proven.**
  Path: Start 620–632, A 1000–1012, Start 2300–2312 —
  pressing Start during the state-16 timer 3–10 cycling →
  **state 17 timer 0 at frame 2301**, timer 1 (input wait)
  holding through frame 3200. Screenshot
  (`build/nacre-test/slice5/exp/s17-orig.png`): "STAGE
  0-1", options CONTINUE / SAVE+END / RECORD, cursor on
  CONTINUE, Mario standing on bricks; top bar `099`,
  `0000000`, `x04`. Mechanism (code + live watch):
  state-16 steps at timers 3/5/7/9 (`$083e`) and 4/8
  (`$0847`), 6 (`$0859`), 10 (`$0853`) run the `$0868`
  joypad watch (`call $1805; ldh a,[hJoypadNew $ff8b];
  and $0c`); Start (bit 3) → save timer to `[$c70b]`,
  `jp $1d22` (AdvanceState 16→17); Select (bit 2) → save
  timer, timer=`$29` (41). Guards at `$088f-$089e`:
  `[$da4b]!=$21` and (`[$c712]!=0` or `[$c711]!=1`). Live
  watch at entry (frame 2301): `[$c858]=$ff, [$c860]=00,
  [$c82b]=06, [$da4b]=00, [$c70b]=07, [$c711]=$63,
  [$c712]=00` — guards pass; saved timer 7. Timer 10's
  entry `$0853` sets timer=3, so timers 3–10 cycle
  indefinitely — the Start window is wide, not a single
  frame. FileSelectStep1 (`$4d66`, bank 1): Up/Down/Select
  move cursor `[$c809]` (0–3, refreshed each frame by
  `$10dd`); A/Start: file 0 (CONTINUE) → step 2 (`$4e6d`:
  clear `[$c200]`, `call $10dd`, IncStateTimer) → step 3
  (`$4e06`: restore timer from `[$c70b]`, dec 17→16);
  file 1 (SAVE+END) → `[$c82d]/[$c835]=$4a`, `call $4cbe`
  (save write), timer+=2 → step 4 (`$4e7c`: wait for
  `[$ff95]==$2b`) → step 5 (`$01fb` soft reset to title);
  file 2+ (RECORD) → `$4dc9` stores pair
  (`[$c80f]=6`, `[$c810]`=current state 17), timer=0,
  state 8 (confirm dialog; matches slice 4's state-8
  finding). `$10dd`: switch to bank `$0b`, clear
  `[$c701]`, loop 32× over the `$c200` table calling
  `$112c` per nonzero byte.
- **File 0 + A from the pause menu returns to the demo,
  no new game.** s17 flow + A 2400–2412: state 17 timer 2
  at 2400, timer 3 at 2401, **state 16 timer 7 at 2424**
  (FileSelectStep3 restored `[$c70b]=7`, dec 17→16 —
  exactly as code predicts), then demo cycle resumed:
  state 20 at 2845/3576/4307/5039, state 28 at 5769.
  `[$c860]=00`, `[$c858]=$ff` throughout. `[$c809]` was
  `00` at the A press (it fluctuates during state 17
  because the stream engine also writes `[$c809]`, but
  `$10dd` refreshes the cursor each step-1 frame).
- **State 28 is the GAME OVER screen.** Screenshot
  (`build/nacre-test/slice5/exp/ng-orig.png`): "GAME OVER"
  with DK, same menu CONTINUE / SAVE+END / RECORD.
- **The queue's real stages ARE reached — in the attract
  demo.** 30000f idle (no input): queue index reaches 158;
  state-20 visits at indices 1 (B=200), 14 (B=0), 40
  (B=8), 79 (B=20), then 1, 14, 40 again. The C=2 entries
  are NOT all B>=200: indices 1,4,7,10 → B=200,201,202,203
  (demo stages), indices 14,17,20,23,27,30,33,36,40,43 →
  B=0,1,2,3,4,5,6,7,8,9 (real stages). Live: index-14
  visit (frames 9442–~9700) has `[$c860]=01, [$c861]=01`
  (world 1, stage 1), timers 1 → 16 → 17 (long visits,
  ~200+ frames — real gameplay timers, not the 144f
  intro); index 40 → `[$c860]=02`; index 79 →
  `[$c860]=03`. `[$c860]` is the WORLD number,
  `[$c861]` the stage-in-world (the pause menu's "STAGE
  0-1" is world 0, stage 1). The B<200 path at `$271e`
  reads the stage table at bank `$18` `$4934 + B*8`.
  States visited in the idle run: {0, 2, 16, 17, 18, 20,
  30} — states 17/18 appear transiently without input.
- **Why state 20 ignores input in the demo flow
  (verified live + code).** Queue: `QueueFetchBC $0dda`
  reads bank-12 table `$4f97+[$c85c]*2` → (C,B);
  `[$c85b]`=C. C meanings (C-dispatch table at bank-0
  `$0d8c`, 23 entries): 1=load stage B (`$0d1a` →
  `$24e7`, then dec), 2=state 20 (`$0d23`), 3=state
  4-or-20 walk (`$0d2c`), 4=no-op, `$14`=state 30.
  State-20 step 0 (`$26b5`): clears `[$c860]/[$c861]` at
  `$26e5`, fetches (C,B); `B<$c8` → stage-table path sets
  `[$c860]` from stage data at `$2745`; `B>=$c8` →
  `$2701` branch, `[$c860]` stays 0, `[$c861]=1` (B=200:
  `200-$af-$19+1=1`). B=200 is exactly the `$c8`
  threshold. State-20 timer 1 (`$43f9`, bank 1): joypad
  check (A/Start bits 0/3 of `hJoypadNew`) runs only if
  `[$c82b]` bit 5 clear AND `[$c860]!=0`; otherwise it
  counts down `[$c20b]` and calls `$169c` every 16
  frames. With `[$c860]==0` the check is skipped — this
  explains slice 4's byte-identical Right+A test during
  state 20 (Right isn't even checked there).
  State-20 prologue `$266c`: if bit 5 set and any joypad
  held → `jp $06a5` (→ `$01fb` soft reset to title).
  State-16 timer-12 queue-advance path (`$08f7`):
  `[$c858]=$ff`, `[$c859]=0`, `[$c838]=0`, dec `[$da43]`;
  when `[$da43]` wraps to `$ff` → state `$1c` (28),
  timer 0. `[$da43]` starts at 4 (ClearRAMAndInit) — the
  5 demo cycles then state 28 at 5645. Full f0 state
  sequence (verified): 0→2 (17)→3 (710)→16 (1089)→4
  (1090)→16 (1988)→20 (1989)→16 (2134)→15 timer 29
  (2142)→16 timer 1 (2147)→20 (2720)→…→28 (5645)→16
  (5746)→20 (5747)→16 (5892)→15 (5900)→16 (5905)→20
  (6478)→…
- **Player-driven state 20 is NOT reached — and now the
  mechanism is mapped.** The real stages (world 1/2/3)
  are reached only through the attract demo (state 30),
  which sets the demo flag `[$c82b]` bit 5 at every
  state-16 timer-0 transition (live: bit 5 set at frames
  1475, 7281, 9441, all state 16 timer 0; cleared at 5835
  state 2 and 7978 state 18 timer 7 — both resets). While
  bit 5 is set, ANY joypad input during a state-20 visit
  soft-resets to title — proven live: holding Right
  9450–9750 during the index-14 real-stage visit →
  **state 2 at frame 9469**, `[$c82b]` `$20`→`00`,
  `[$c860]` 01→00, queue index `0e`→00 (control run
  stayed in state 20). Bit-5 inventory (whole-ROM
  survey, opcode-corrected): the ONLY `set 5,[hl]` with
  HL=`$c82b` in the ROM is bank-1 `$4ab4` (inside
  `$4aa4`, reached via the bank-0 `$3414` jump table —
  entries `$4998, $49bf, $49ef, $4a2e, $4a75, $4aa4,
  $4b14, $4b21, $4a7f, $4b2a`; the table's dispatcher is
  unidentified, no `ld hl,$3414` in the ROM); the ONLY
  `res 5,[hl]` on `$c82b` is bank-0 `$06b8`
  (FileSelectLoop_Joypad, then `jp $01fb`); boot clears
  bit 5 via ClearRAMAndInit's `[$c82b] & $cd` mask.
  `$4a75` sets up the 16-bit countdown `[$def7]=$03fc`;
  `$4aa4` decrements it and sets bit 5 at 0. No `call
  $4a75`/`call $4aa4` anywhere — they are entered via the
  `$3414` table only. The real-gameplay path (bit 5
  clear + world!=0) must reach a real stage WITHOUT the
  attract demo — most likely starting a new game from a
  file screen, which the demo flow never offers (state
  28's CONTINUE just replays the demo). That is the next
  slice's target.
- **States 21/22: UNREACHABLE — verdict, not a guess.**
  `$09f0` (called only from TransitionStep0 `$071c`,
  state-16 timer 0) sets state 21 (`$15`, then inc to 22
  if `[$c711]` bit 0) iff `[$c858]==0` AND `[$c860]!=0`.
  Both conjuncts fail at every timer-0 check in every
  observed flow (demo, attract, game-over):
  - `[$c858]==0` is impossible by construction. Complete
    writer inventory (9 `ld hl,$c858` sites + `$0273`;
    zero `ld [$c858],a` anywhere in the ROM): `$0273`
    boot `$ff`; `$094d` queue-advance `$ff`; `$505f`/
    `$5690` (bank 1/12 state→16 exits) `$ff`; `$47a7`
    clears to 0 (transient — see below); `$4866`
    normalizes to `$ff` (count<3) or 3 (count>=3);
    `$48a7`/`$48b5`/`$48c3` inc during the scan; `$7e07`
    (bank 7) reads only. `$47a7` (bank 12, called only
    from `$077a` TransitionStep1; sole `call $47a7` site
    in the ROM) clears `[$c858]/[$c859]/[$c0a4]/[$c863]`,
    scans 960 bytes `$c86d-$ca2c` counting `$20`/`$22`/
    `$4a` bytes, then `$4866` normalizes `[$c858]` to
    `$ff`/`3`. Verified by grep that no `ret` exists
    between `$47a7` and `$4866` (the `$4716` ret belongs
    to the separate `$46a9` loop) — the normalization
    always runs. Ordering: `$09f0` runs at state-16
    timer 0; `$47a7` runs at state-16 timer 1. Timer 0
    always precedes timer 1 in a state-16 visit, so at
    `$09f0` time `[$c858]` is the previous load's
    `$ff`/`3`, never 0. The only 0-window is transient
    inside `$47a7`'s own execution, which `$09f0` cannot
    observe on a single CPU. Live: WRAM watch shows
    `[$c858]=$ff` at all 12 state-16 timer-0 visits in
    the 7000f f0 flow, and at every timer 0 in the
    30000f idle flow. No save path writes `[$c858]`
    (save routines operate on SRAM `$a000-$bfff` only;
    `$bfbe` readers `$5789`/`$53c7`/`$5512` read file
    data into other variables) — a crafted save cannot
    set it either.
  - `[$c860]!=0` is never true at a timer-0 check either.
    `[$c860]` is set only during a state-20 visit (the
    B<`$c8` path at `$2745`) and cleared only at the
    next state-20 step 0 (`$26e5`) or by a reset
    (ClearRAMAndInit) — but no state-16 timer-0 check
    follows a real-stage visit before a reset clears it:
    verified in the 30000f idle trace, there is no
    state-16 timer-0 line between the index-14 visit's
    end (~9700) and the reset at 10647 (state 2,
    `[$c860]`→00, queue index→00), and every timer-0
    line in the trace has `[$c860]=00`.
  - No other path writes 21. `jp $1d22` (AdvanceState)
    has only 2 sites in the ROM — `$08c9` (16→17 via
    Start) and `$30bb` (called only from the C-dispatch
    dec handler `$0d07` via `$30b8`, which does
    `call $42c8; jp $1d22` — the dec→inc round trip
    16→15→16); `call $1d22` has 0 hits. Slice 3's writer
    inventory stands: direct `ldh [hGameState],a` values
    {1,2,3,4,8,$10,$12,$14,$18,$1a,$1c,$1e} plus `$09fe`'s
    `$15` plus variable-A at bank 1 `$597e` (state-8
    return pair — returns to the state it came from).
  States 21/22 are therefore dead code, same class as
  state 12 (slice 3), but by an unsatisfiable guard
  rather than a missing writer. Their contents (`$3582`,
  9 entries, bank 0; `$3663`, 8 entries, bank 12) have
  not been examined live — they never run — and are
  readable statically in a later slice.
- **Save-RAM side finding.** Slice-4 f0 and f1 saves are
  byte-identical except the tail: both 1,622 non-`$ff`
  bytes, `$a000-$a4af` zeroed (the `$1f9a` clear),
  scattered data `$b4ca-$b927` in both; f0 tail
  `$bfbe-$bfff` all zeros, f1 tail has file data
  `00 01 04 40 …`, `$bffa` signature, `$bff6`/`$bfd8` =
  `02 07`. `save_dirty: 1` also in the 12000f and f0
  regression runs, `0` in the 600f title run — the game
  writes SRAM during longer demo flows, not just on
  explicit save. Which routine writes the `$b4ca-$b927`
  region is not yet established.

**Inferred, not verified** (do not present as settled):
- Bank 7 `$6f62` routine roles (what `[$dd40]`/`[$dd41]`
  are, what the 4 dispatch entries do) and bank 23
  handler roles — labels are address-derived only.
- The `$3414` jump table's dispatcher identity.
- The `$b4ca-$b927` SRAM-write source.
- State 21/22 handler contents (`$3582`, `$3663`) — never
  run, readable statically.
- Bank 2 `$4142-$415b` (slice 4), bank 12 `$4e55-$4f96` /
  `$522d-$52d4` table structures (slice 4), bank 7 `$4794`
  role, `$77a9`/`$78ba` roles (slice 4) — unchanged from
  slice 4.

## Slice 6 — DONE, byte-matching (2026-11-21)

Code carved (`src/` 21,640 → 22,713 lines), all byte-matching
(SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero
diffs). Not pushed — coordinator pushes after verifying.

### 1. The real new-game path — ANSWERED (verified live)

Fresh file (Start 620–632, A 1000–1012, 12000f, expA): title →
Start → file select (state 3) → A on a New file → intro (state 4,
~900f) → queue 1 → the 25m "stage" visit, which is a FROZEN tableau
(DK sitting, "25m", no Mario, no animation, no input response,
~141 frames, `[$c20b]` 00→`$82`) → (1,0) load → state 15 → state 16
→ timer-12 retry → replay 25m, ×5 (lives `[$da43]` 4→0) → game over
(state 28 at 5645). Bit 5 of `[$c82b]` CLEAR throughout. Input
during the 25m visit (Right, A, Start — expB/D/E) changes nothing:
fb hashes identical to the no-input control.

Progress-1 save (see §3): the same Start+A flow reaches queue 14
(`[$c85c]`=14 at state-16 entry, frame 1088) → state 20 with
world 1, stage 1 → the BIG-CITY 1-1 MAP (state-20 timer 17,
entered 1259, Mario icon on the 1-1 node). With no input the map
waits forever at timer 17 (still there at 12000f). A or Start on
the map (2000–2012) SKIPS it: timer 18 at 2000, queue 14→15→16,
then the state-16 timer 3–10 cycle — the queue ping-pongs between
(3,1) and (1,4) for ~9600 frames until the timer-12 retry fires:
retreat to the last C=2 entry (queue 14), lives 4→3, and the map
visit runs again (state 20 at 11760, qidx 14). Right on the map
does nothing (still timer 17 at 3000f). So the (2,1) playable-stage
entry at queue 17 is never dispatched in any flow tested: the
(3,1) handler (`$0d2c`, B==1) always takes the
advance+fetch+dispatch-then-retreat path, so the queue never
advances past 16, and the only exit is the timer-12 retry back to
14. State-20 gameplay timers 2–17 never run in any observed flow
(fresh 12000f, idle 30000f, all input variants). The attract demo
is the same story: it cycles queue indices 1, 14, 40, 79 only
(25m card + three map visits), A/Start during a map skips it, and
it soft-resets to title by 12000f (state 2, timer 6). What
dispatches (2,1) is the next slice's question: candidates are the
(3,1) B==4 + `[$c82b]`-bit-4 path in `$0d2c` (advance WITHOUT
retreat — bit 4 is set by the retry itself at `$091a`), or a map
input other than A/Start (directional move to the node first).

### 2. `$3414` table identity — RESOLVED

It is the TitleScreen table: dispatcher is `TitleScreen` at
`$340e` (`ldh a,[hStateTimer]; rst $08`). Entries `$342a, $4998,
$49bf, $49ef, $4a2e, $4a75, $4aa4, $4b14, $4b21, $4a7f, $4b2a` are
title steps 0–10 in bank 1. Step 5 (`$4a75`) sets countdown
`[$def7]`=$03fc; step 6 (`$4aa4`) decrements it, and on expiry sets
bit 5 `[$c82b]`, timer=0, state=16, queue start from the `$48f3`
table. Start in step 6 → step 7 (`$4b14`) → state 3; Select in
step 6 → `jp $4dcb` → state 8 with return pair (timer 0, state 2).

### 3. Save validation — CORRECTION to slice 4

Slice 4's claim "the save VALIDATES" is overstated. The no-input
reload boot never reaches `ValidateSave` (it runs only in
PostStartStep0, state 3); `save_dirty: 0` only proves nothing
wrote during the title screen. The game's own f1 save FAILS its
own validation: `SaveChecksum($a000)` E=`$00` vs stored `$ff`,
backup `SaveChecksum($be2c)` E=`$70` vs stored `$ff`. Cause: the
save-write routine `$4cbe` NEVER writes `$be2a/$be2b` (the `$a000`
checksum). The ONLY writer of `$be2a` is bank-23 `$74a9` (see §5),
which runs only in the attract-demo flow when `[$ca66]` < `$18`
or == `$1a` — and in the f1 flow state 30 was never visited, so
`$74a9` never ran. Consequence: a fresh save written via state 28
can never validate until the attract demo has run `$74a9` once.
`tools/make_progress_save.py` now fixes both checksum pairs
(nibble-encoded, high nibbles preserved): `$be2a/$be2b` from the
`$a000` checksum, `$bfbc/$bfbd` from the `$be2c` checksum. With
the fix, the progress-1 save validates: expH2's save-out has the
file records intact (not wiped), fb `a50e8bb0…` (a different flow
from expA's `92d2e185…`).

### 4. `$b4ca-$b927` SRAM writer — IDENTIFIED (dynamic proof)

New tool `tools/gb_sramwatch.c` (snapshots SRAM every frame,
reports the first frame each watched byte changes with PC/bank/
state/timer): ALL `$b4ca-$b927` first-writes happen in ONE frame
(2146, PC `$42e7`, bank 12, state 15 timer 29 — right after the
first stage load). The writer is bank-12 `$42c8`, called via
`$30b8` from the C-dispatch dec handler `$0d07` (the only
`call $42c8` in the ROM; the only `call $30b8` is at `$0d14`):
`EnableSRAM; HL=$d44d, DE=$b4c0, BC=$0380; call $42de;
DisableSRAM`. `$42de` copies 896 WRAM bytes (`$d44d-$d7cc`,
stage data) to SRAM `$b4c0-$bbbf`, expanding each byte to a
(value, nibble-swapped) pair. So the region is a nibble-expanded
backup of the current stage data, rewritten on every C=1 stage
load — which is why the idle 30000f save has 1109/1117 bytes
there (union of many stages) vs 356 in the fresh-file flow.

### 5. Bank 23 roles (partial) + `$48f3` verification

- Bank 23 `$74a9` (AttractSaveRecord, called from `$73f3` in the
  attract-demo flow): `call $293e` (progress index) →
  HL=`$a000+16·progress`; checksums; copies 16-byte records; then
  `$74e4` writes `[$be2a]/[$be2b]` (the validation checksum),
  copies `$a000→$be2c` (`$190` bytes) + checksum byte to
  `$bfbc/$bfbd`, fixes `$bfd8/$bfc0` checksums if markers are
  missing, sets `[$c80f]=1`. Its records live at `$a000-$a18f`,
  NOT `$b4ca-$b927` (ruled out as that region's writer).
- Bank 23 `$7200-$731e` is DATA, not code: a `gb_rd` walk from
  seeds there produced garbage (`jp nz,$00xx` chains); the
  `$725b`/`$726d` `ld bc/hl,$bxxx` hits are data bytes. Do not
  treat as code. Real code resumes at `$731f` (slice 3).
- `$48f3` demo-start table verified live (expG2, re-run with a
  trace file — the first expG run had no trace file): title
  timeout at frame 1475 sets `[$c85c]`=`$9d`, `[$c85d]`=01 →
  queue 413, `[$c82b]`=`$20` (bit 5 set); state 30 at 1476, qidx
  414. Matches the corrected table (defb 0→413).

### 6. State 8 = RECORD screen (Select at title)

Select at title (620–632, 3000f): state 2 → state 8 at 620, timer
0→1 at 635, waits there (fb `e3323ba3…`). Screenshot at 1000f:
"STAGE 0", "STAGE TOTAL 000", four entries (1–4, all 000 with
timer icons), "TOTAL 000", three stage-preview thumbnails (25m
construction site, a cave, the girder stage). This is the
record/replay viewer — the RECORD option in the pause/game-over
menu (`$4dc9` → state 8) and the Select-at-title entry point.
Return pair is (timer 0, state 2).

### 7. States 21/22 — static read (they never run)

- State 21 (`$3582`, 9 entries, bank-1 `$4f31-$5051`): a
  cutscene/story sequence. Step 0 (`$4f31`) builds a tile scene
  from the `$5db4` pointer table (10 records of 4×4 tile blocks
  into VRAM `$9800`), sets `[$c836]`=$35, jumps to `$3891`.
  Step 1 (`$4fbd`) waits `[$ff95]`==`$b5`. Step 2 (`$4fcf`)
  waits for joypad bit 0 (A), sets `[$c82f]/[$c835]`=$4b,
  computes `[$c22f]` from `[$c711]`. Step 3 (`$5004`) waits
  `[$ff95]`==`[$c22f]`. Step 4 (`$5018`) runs the `$506a`
  text/scroll routine (tables `$5d8a/$5d9e`). Step 5 (`$501d`)
  waits `[$c22b]`==`$3d`, reads a `$5dae` table → `[$c809]`.
  Step 7 (`$5051`) waits B==`$3d`, then sets state 16
  (`[$ff8e]`=$10), `[$c858]`=$ff, `[$c859]`=0, timer 0. Most
  likely the intro story (DK stealing Pauline) or the ending.
- State 22 (`$3663`, 8 entries, bank-12 `$553d-$5680`): a
  results/credits setup. Step 0 (`$553d`) builds three
  number displays (routines `$55c9/$55d6/$55e3` read `[$defe]`
  & `$1f` + `$20`; `$55ee` copies 3-byte records from
  `$5918/$5922/$592c` into `$c220/$c280/$c2e0`), sets
  `[$c836]`=$35, `[$ff8f]`=$26, checks lives `[$da43]` < 10,
  jumps to `$3891` (shared state-16 entry, A=$29). The
  bank-12 `$59a0` credits text belongs to this bank.

### 8. Carve: bank 0 `$10c2-$1642` (sprite-stream engine)

`src/bank0slice6.asm` (991 instructions, `tools/gen_slice6_bank0.py`,
`tools/gb_rd.py` recursive descent — the linear sweep misaligns
here; full coverage, 0 uncovered bytes). Four iterator/dispatcher
pairs walk the 32-entry stream-record table at `$c200` (stride
`$20`) and copy sprite bytes into the OAM buffer at `$c000`,
dispatching through the bank-`$0b`/`$1c` `$4000` table:
A `$10dd`/`$112c` (32 records from `$c200`; `$f0`/`$f1` special
cases; flip `$1a`/`$11`), B `$11e8`/`$123d` (31 records from
`$c201`; flip `$2b`/`$12`), C `$12f9`/`$1348` (32 records from
`$c200`, zeroes the OAM tail; simpler layout; flip `$36`/`$13`),
D `$13e7`/`$143e` (bank `$1c`; alternates `$c5e0` stride `$22` /
`$c200` stride `$20` on bit 0 of `[$ce21]`; bit-7 h-flip variant).
`$10c2` clears the OAM buffer (160 bytes) and the record table
(1024 bytes), then switches to bank `$1d` and jumps into the
`$10dd` loop at `$10e3` (so it dispatches through bank `$1d`'s
table). Tail: `$1522`/`$1528` trampolines (bank `$0c` →
`jp $4bcd`/`$4bf1`); `$152e`/`$15f8` clamp record positions
against the scroll registers into `wScrollShadow` (`$c707`/
`$c708`), dispatched on `[$c705]` (1 = both axes, 2/5 = X only,
3 = Y only, 4 = none). `$15f8`'s caller is unidentified (no
carved call site) — carved as code because the bytes decode as a
coherent routine with a proper prologue/epilogue, not data.

### Nacre results (slice 6, rebuilt ROM = original)

- Regression script (`tools/run_slice5_regression.sh`): all 7
  prior cases identical (600f `1cf92679…`, 900f `39ffd5ee…`,
  3600f `88515f4e…`, 12000f `92d2e185…`, s8/f0/f1).
- Slice-6 cases, original vs rebuilt: expA (Start+A 12000f)
  `92d2e185…` OK; idle 12000f `1cf92679…` OK; Select-at-title
  3000f `e3323ba3…` OK; idle +A-during-map 12000f `cbb9caad…`
  OK; idle 30000f `0b8b12b6…` OK with the SRAM dump
  byte-identical.
- New cases this slice: expH2 (progress-1 save, Start+A 12000f)
  fb `a50e8bb0…`, records intact, queue 14 reached; prog1+A-long
  (A on the map, 12000f) fb `0d835d95…`, map skipped, ping-pong,
  retry, map again at 11760 with lives 3.

### Mistakes caught by the byte-match check (slice 6)

- The `gen_slice6_bank0.py` jr-label regex missed the comma
  after the condition (`jr nz, $…`): references were rewritten
  to `jr_000_…` labels but no definitions were emitted — 52
  undefined symbols at link time. Fixed in the generator
  (collection regex now matches the rewrite regex), regenerated.
  The check also caught the walk following `call $1060` /
  `jp $1057` outside the carve (already curated in main.asm) —
  the generator now filters emission to `$10c2-$1642`.

## Slice 7 — DONE, byte-matching (2026-11-21)

Headline: **(2,1) is NOT the blocker for playable stages.**
Slice 6's premise was wrong. Playable stage 1-1 runs in STATE 16
(timers 3-10), reached via map -> (3,1) -> (1,4) load -> timer
chain; player control verified live (Mario moves and dies, deaths
cost lives, the stage replays via the intro card). (2,1)@17 is the
post-completion entry (next stage's map/card visit), reachable only
after completing 1-1 (key -> door). Slice 6's "never dispatched"
framing is corrected below; the queue oscillates 14->15->16->14
(map exit +1, timer-32 +1, retry -2) until the stage is completed.

### 1. The (2,1) dispatch — verified live

- Queue table (bank 12 `$4f97`, 331 entries, dumped from ROM):
  indices 0-40 are 0 (3,0), 1 (2,200), 2 (1,0), 3 (4,0), 4 (2,201),
  5 (1,1), 6 (4,0), 7 (2,202), 8 (1,2), 9 (4,0), 10 (2,203),
  11 (1,3), 12 (4,1), 13 (0x14,0), 14 (2,0), 15 (3,1), 16 (1,4),
  17 (2,1), 18 (3,2), 19 (1,5), 20 (2,2), 21 (3,2), 22 (1,6),
  23 (2,3), 24 (1,7), 25 (4,0), 26 (0x14,1), 27 (2,4), 28 (3,1),
  29 (1,8), 30 (2,5), 31 (3,2), 32 (1,9), 33 (2,6), 34 (3,2),
  35 (1,10), 36 (2,7), 37 (1,11), 38 (4,5), 39 (0x14,2),
  40 (2,8). C histogram {1:101, 2:101, 3:68, 4:35, 20:26}. The
  ONLY (3,4) entry in all 331 is index 327, successor (1,100)@328;
  the only (3,0) is index 0. C==3 B values {0,1,2,4}; C==1 B range
  0-100; C==4 B values {0..5}; C==0x14 B values 0-26 except 25.
- `$0d2c` (C-dispatch entry 3): B==0 -> state 4; B==4 +
  `[$c82b]` bit 4 set -> advance (qidx++), fetch next,
  `jp $0d04` re-dispatch (NO retreat); else -> advance, fetch,
  `call $0d04` (nested dispatch), `jp $0dc7` retreat. Subtlety:
  nested C=2 dispatch (`$0d23`) does `pop af; ret`, discarding
  the return address, so the retreat at `$0d59` is SKIPPED and
  qidx stays advanced. Nested C=1 returns normally, so retreat
  runs.
- State-16 timer-12 retry (`$08f7`): after stream calls, if the
  timer is still 12, checks bit 3 of `[$c82b]`; if clear, sets
  bits 3 AND 4 (`$0920`/`$0922`), retreats up to twice looking
  for C==2 or C==$15, else advances twice (net 0); then `$094d`
  sets `[$c858]`=$ff, `[$c859]`=0, `[$c838]`=0, dec `[$da43]`
  (lives); lives wrapping to $ff -> state 28. Retry takes ~263
  frames of stream work.
- `$495c` (bank 1, from `$0cec` before C-dispatch): peeks at the
  next entry (advance + fetch + retreat, net 0), sets
  `[$c856]`/`[$c857]` from tables `$5d5e`/`$5d74` indexed by C;
  if next C==4 sets `[$c857]`=$5b; if world==9/stage==8 sets
  `[$c856]`=$3b. Preserves BC; does NOT change qidx permanently.
- State-20 step 0 (`$26b5`): clears `[$c860]`/`[$c861]`
  (`$26e5`), IncStateTimer (`$26ee`), bank $18, fetch (C,B);
  B>=$c8 demo branch (`$2701`); B<$c8 stage-table path (`$271e`:
  HL=bank-18 `$4934`+B*8). Tail `$2829`: if timer<2 AND
  `[$c82b]` bit 4 clear: `[$c70f]` bit 0 -> timer=$13 (19);
  `[$c70f]` bit 2 -> timer=$0f (15). World==9/stage==9 ->
  timer=1.
- State-20 timer 1/17/26 (`$43f9`, bank 1): bit 5 set OR
  world==0 -> countdown path (dec `[$c20b]`, exit at $81 wrap
  -> timer 18 + QueueAdvance `$446a`); else joypad path: A/Start
  (bits 0/3 of hJoypadNew) -> exit `$4434` (timer=$12 (18),
  `jp $0dba` advance); else dec `[$c20b]` with NO $81 check
  (waits forever without input). Timer 18 (`$448e`): waits
  `[$ff95]`==$60 (or $a0 if `[$c80d]`==$6f); then timer=0,
  state=16 (bit 5 clear) or 18 (bit 5 set).
- State-16 timer chain after a (3,1) dispatch: timer 0
  (dispatch) -> 15 (dec) -> 1 (level load `$0737`) -> 2
  (`$07e7`; tail: `[$c85b]`==3 -> timer 27) -> 3 -> 28
  (`$0a98`; `$0a9b` quirk: if bit 4 set AND fetched B==1, B++
  before bank-$10 `$6b32`(B)) -> 29 -> 30 -> 31 -> 32
  (`$0ac4`: advance qidx, timer=3) -> 3-10 cycle (joypad watch
  `$0868`: Start -> pause state 17, Select -> timer $29) -> 12
  (retry). Timer 9->12 jump via timer-9 tail `$1528` -> bank $0c
  `$4bf1`.
- `$0c2f` (timer-4 tail): stage-time countdown -- every 15th
  call decrements 16-bit `[$c711]`/`[$c712]`; hits 0 -> timer=12
  (retry). This is the TIMEOUT trigger.
- Complete QueueAdvance (`$0dba`) call-site inventory:
  `$0d47` (bit-4 path), `$0d50` (else path), `$0d7e` (C=$14),
  `$446a` (map/card exit), `$0ac4` (timer 32), `$0997`
  (timer 23), `$09d5` (timer 26), `$0b25` (timer 40), `$58f0`
  (state-4 step 3 exit: state 16 + timer 0 + advance),
  `$0942`/`$0945` (retry fall-through, net 0), `$4970`/`$4993`
  (`$495c` peek, net 0). `$4d21` loads qidx from the `$5e99`
  progress table.
- Timers 23/26 clear bit 4 (`$09a1`/`$09d9` `res 4,[hl]`).
  Timer 40 (`$0b21`): timer=$2a + advance. Timer 42 (`$0b45`):
  world/stage 9,9 -> timer 0; else Select-path + timer $2b (43).
  Timer 43 (`$0b6a`), 44 (`$0b95`: countdown `[$c711]`, inc timer
  at 0), 45 (`$0bde`: wait any joypad -> timer 0). Chain
  33->...->40->42->43->44->45->0 is the stage-clear sequence,
  entered from timers 23/26 when the advanced-to entry has C==4.
- `$4bcd`/`$4bf1` (bank 12) are scroll/sprite routines, NOT
  gameplay logic. `$169c` is a memory-copy helper, not a timer
  advancer. `$0bff` decrements 16-bit `[$da47]`, scans 32
  `$db15` records (stride 15), calls banked `$4000` for records
  with byte >= $30.
- `[$c70f]` writers: `$2735` set bit 1, `$2758` set bit 2,
  `$29ea` clear, `$4463` clear, `$46af` clear. Bit-0 setter NOT
  yet found in carved code.
- **`[$c82b]` bit 4 role pinned (verified live)**: set ONLY by
  the timer-12 retry (`$0922`); cleared by state-16 timers
  23/26 and boot. It flips the state-20 visit from map-lane
  (timers 15-17) to card-lane (timers 0/1/18) -- after a retry,
  the (2,0) visit shows the stage card, not the map. It also
  gates the `$0d2c` B==4 path and the `$0a9b` B++.
- Slice 6's `$73b2` question answered: the attract map
  auto-advances because `$43f9`'s countdown path ($81 wrap)
  runs when bit 5 is set or world==0; the progress map waits
  for A/Start because the joypad path decrements `[$c20b]`
  without the $81 check.
- Live runs (original ROM, Nacre `gb_headless`, progress-1
  save, `GB_WATCH=c85c,c82b,c860,c861,da43,c70f`): retry run
  (15000f, fb `0d835d95da32f694f2ad35754221c89da3ecea0bbeba0d52e50fd937194c9ab1`)
  -- after the retry (f=11496 timer 12; f=11759 state 16 timer
  1; f=11760 state 20 timer 0 qidx=14 lives=3) the second map
  visit sits at state 20 timer 1 FOREVER (f=11763-14997),
  `c82b`=$1e (bits 1,2,3,4 set), world=1 stage=1 lives=3
  `c70f`=$04. The bit-4-set visit does NOT jump to timer 15;
  it waits at timer 1 for A/Start. Mid-stage screenshot
  (5000f, fb `2ab1bb5dfac756816557ed1f86dbd875623b4ae71cbdfa5417e187b96006b237`,
  `build/nacre-test/slice7/mid5000.png`): PLAYABLE stage 1-1
  (Mario bottom-left, Pauline bottom-right, girders, ladders,
  key, door, oil can; top bar "109", score 0000000, lives x04).
  Play test (5000f, right 2500-5000 + A presses 2600-4700, fb
  `b3cb6c8b25271e0c759cce70c28dc4468ad1b9c3b2abfcc4a4e2716cbcfef094`):
  timer 12 (death) at f=2668 (~170f into stage); f=2932 timer 0;
  f=2933 state 20 timer 0; f=2936 timer 1; f=3200 timer 18;
  f=3296 state 16 timer 0; stage again f=3528; second death
  f=3677; third death f=4600; final screenshot shows
  "BIG-CITY / STAGE 1-1 / x1" intro card at state 20 timer 1.
  Lives 4->1 across three deaths. Death probe (3000f, fb
  `632b2eaf7002bc0ab2a1785b41c8ad166bc29f47f8115fec1226448f0d4efc44`):
  first timer 12 at f=2668 with `[$c711]`=$94, `[$c712]`=$00 --
  countdown NOT zero, so death does NOT go through `$0c2f`'s
  countdown==0 path. `[$c711]` $96 at f=2500 -> $94 at f=2650
  (~1/100f).
- OPEN from Part 1: completing stage 1-1 live (needs real play,
  key -> door) to watch the queue advance 16->17; the
  death->timer-12 exact instruction is not pinned (candidates:
  bank-9 `$0bff` `$db15`/object dispatch, `$11e8` iterator-B
  handlers; the countdown path is ruled out).

### 2. Bank 7 `$6f62` / bank 23 `$7722` roles — pinned

- Bank 7 `$6f62` = **timed sprite-record animator for the stage
  intro**, called from `$08ee` (state-16 timer 8/9 region).
  `[$dd40]` is a per-step countdown (reloaded from
  `[$dd3e]`/`[$dd3f]`); `[$dd41]` is the phase (bit 0 toggled by
  the return code after each dispatch, bit 7 = done, set by
  `$6fad` when hStateTimer != $13). Entry 0 (`$6f81`): writes
  `[$c201]` = ([$dd43]&1)+$30, `[$c202]`=0. Entry 1 (`$6f96`):
  writes `[$c201]` = [$dd43]&1, `[$c202]`=0; increments
  `[$dd42]`; after 7 cycles falls to `$6fad`. `$6fad` (on
  hStateTimer==$13): writes `[$c201]`/`[$c202]` from
  `[$dd43]`/`[$dd44]`, restores hStateTimer from `[$c70b]`,
  clears `[$c838]`, clears bit 1 of `[$ff91]`, and jumps via the
  `$7001` table (entries $701b, $706c, $7068, $708f, $70c2,
  $70e4, $70f0 — per-`[$dd18]` intro endpoints). Entry 2
  (`$4121`) is the per-frame tick (writes `$c830`/`$c831`/
  `$c835`, sets hStateTimer=$11). Entry 3 (`$7edd`) is DATA,
  not a handler (garbage disassembly — `ld d,d` filler).
- Bank 23 `$7722` = **stage-data stream interpreter (bytecode
  VM)**, driven by the `$c200`-record loop (`$76f1`/`$7707`,
  bank23.asm). Entry `$7717` stores HL+1 into `[$ca6a]`/`[$ca6b]`
  (the resume pointer), reads the opcode A=[HL], rst $08
  dispatches on it (74 entries, `$77bc`-$7af5). Handlers copy
  bytes from the stream (HL) to a destination (DE) and loop
  back to `$7717` (`jp $7717`); some call `$7de6`/`$7dee`
  (stream helpers) and set `[$ca65]` / `[$c835]`. It consumes
  the compressed stage stream and materializes it into
  WRAM/VRAM. `[$ca6a]`/`[$ca6b]` and `[$dd40]`/`[$dd41]` are
  local state for their subsystems — no other carved code
  touches them.

### 3. Carves (933 new lines; `src/` now 23,652 lines)

- Bank 0 `$17eb-$1d06` (584 instructions, `src/bank0slice7.asm`,
  generator `tools/gen_slice7.py`): `$17eb`
  SpriteRecordDispatch (gated on `[$c200]`!=0; A=`[$c201]`>>1,
  dispatch via `$1832` on change; called from `$0a95`), `$1805`
  SpriteRecordDispatchB (ungated; called from `$0886`/`$08d8`/
  `$090f`/`$0986`/`$09b9`/`$09c6`/`$0a18`), `$1832` Rst08Dispatch
  (rst $08, **44-entry** dw table `$1833-$188a`, handlers
  `$188b-$1c28` plus `$1d29` `ret` as entries 15 and 24),
  `$1c29` BuildAttrMap (reads exactly 13 bytes from the `$1c7d`
  table, C=0..12, indexes `$ddf5`/`$d93d`, writes VRAM pointers
  into `$daf5` and C+1 into `$da4f`+C, tail-jumps to banked
  `$5d21`; called from `$076b`), `$1c8a` LoadStagePtrWrapper
  (call `$1c91`, switch bank to $17, ret), `$1c91` LoadStagePtr
  (bank $1e, loads the stage's state-table pointer from
  bank-$1e `$64e5`, 16-byte stride, `[$c853]`/`[$c854]`/`[$c855]`
  overrides for D==0/1/9, into `[$da5f]`/`[$da60]`; jumps to
  `$1d07` when the record byte is 0), `$1cf7` IncAttrCounter
  (two-nibble counter at `$da4d`). Seeds `$17eb`/`$1805`/
  `$1c29`/`$1c8a` recorded in the generator. The walk also
  reaches `$1060-$1064`/`$106e-$1074` (called from the carved
  code, still INCBIN'd in the $1000-$17ea raw region — bare
  `call $1060`/`$106e`, not emitted).
- Bank 11 `$4000-$40ff` (128 dw, `src/bank11.asm`): the `$112c`
  sprite-pointer table (bank $0b/$1d $4000, indexed by
  2*record[0], then +2*record[1]). Entries 0-87 are a clean
  increasing run ($4269-$591e, pair repeats); 88-95 and 98-101
  are $4200 (the empty/default block); 114-119 point at
  $53xx-$71xx. Extent 128 is INFERRED (the $4200 runs are
  consistent with unused slots; every word is a plausible
  pointer) — not verified against live record[0] values.
- Bank 18 `$4934-$4c83` (106 8-byte db records,
  `src/bank18.asm`): the stage table read by `$271e`/`$4586`/
  `$4807` (base `$4934`, stride 8, index B). Entries 0-100
  verified (B<=100 from the queue's C==1 entries); entries
  101-105 inferred (same texture, 106 matches bank 5's 106
  stage pointers). **RECORD LAYOUT UNRESOLVED (honest gap)**:
  the naive (world=[+0], stage=[+6]) reading gives world=$03/
  stage=$ee for B=0, but the live map visit shows world=1/
  stage=1 (verified by ROM bytes at file offset $48934:
  `03 44 01 f0 f0 f3 ee 40`, and by the `$271e` hand-decode,
  which the disassembly matches exactly). The only writers of
  `[$c860]`/`[$c861]` in carved code are `$26e5`/`$26e8`
  (clear), `$270e` (demo branch), `$2745`/`$2750` (stage-table
  path), and the live trace shows world=0 until f=1100 — 7
  frames into state-20 timer 1 — so the (1,1) must be written
  by UNCARVED stream code during timer 1 (bank 2/3 + bank-11
  table handlers). The bytes are carved as db with no field
  claims; do not read (world, stage) off offsets 0/6 until
  the stream writer is found.
- `tools/gb_rd.py` fix (slice 7): `walk()`'s rst-$08 table
  reader rejected ROM0 addresses (only accepted
  $4000-$7fff/$c000-$dfff), so bank-0 tables read zero
  entries. It now accepts $0000-$3fff when bank==0 (and
  bounds the table scan at $3fff). Slice-6's walk is unchanged
  (1003 instrs, 0 rst08 sites, no notes — verified after the
  patch).
- `tools/gen_banks.py` CARVED map: added bank 11
  `$4000-$4100` and bank 18 `$4934-$4c84`; `src/banks.asm`
  regenerated. `src/main.asm`: "Raw bank 0 B2" INCBIN removed,
  INCLUDEs added for `bank0slice7.asm`, `bank11.asm`,
  `bank18.asm`.

### 4. Byte-match + Nacre (slice 7)

- Clean `make` (build/game.gb removed first): rebuilt SHA-1
  `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs.
- `tools/run_slice5_regression.sh`: all 7 prior cases identical
  (600/900/3600/12000/s8/f0/f1).
- `tools/run_slice7_cases.sh` (new, 4 cases, orig vs rebuilt —
  fb + trace + save all identical, and each fb matches the
  slice-7 original run): retry 15000f fb `0d835d95...`,
  mid5000 5000f fb `2ab1bb5d...` (playable stage 1-1), play-right
  5000f fb `b3cb6c8b...`, death 3000f fb `632b2eaf...`. Note: the
  first mid5000 attempt used a spec missing `a:2000:2012` and
  sat on the map (fb `a50e8bb0...`); the corrected spec (with the
  second A) reproduces the playable-stage fb exactly — the
  script now carries the corrected spec.
- Pushed: slice 6 `fb1f1626` (head at slice-7 start). Slice 7
  NOT pushed (coordinator handles pushes).

## Slice 8 — IN PROGRESS, byte-matching (2026-11-21)

Head at start: slice 7 pushed (`cd9f78fe`). `src/` 23,652 lines
at start, 25,071 after the bank-$10 carve. Byte-match holds
throughout (clean `make` → SHA-1 `397ad2ff…`, `cmp` clean) and
both regression suites re-pass after every carve.

### 1. Stage-table layout — RESOLVED (slice 7's decimal/hex slip corrected)

- Slice 7 carved bank 18 **decimal** (`$12`) `$4934` as "the
  stage table". Wrong bank: the game selects bank `$18`
  (**hex** = 24 decimal; `ld a,$18; rst $10` at `$26f6`).
  The real table is bank `$18` (decimal 24) `$4934`.
- Writer found live with the new `tools/gb_watch` (two-pass
  write watchpoint): the (world,stage) writes are at bank-0
  `$2745` (`ld [$c860],a`) and `$2750` (`ld [$c861],a`), in
  the already-curated state-20 step-0 stage-table path
  (`$271e`), executed with bank `$18` mapped — frame 1100,
  cycles 3381/3388, state 20 timer 1, regs A=01 B=00 C=02
  HL=$4935/$493a, rom_bank=24. Slice 7's hypothesis ("written
  by uncarved stream code during timer 1") was wrong; the
  write is the tail of step 0 (IncStateTimer at `$26ee` runs
  before the fetch at `$26f9`, so the write lands during
  timer 1). Queue fetch confirmed: index 14 = (C=2,B=0) via
  `QueueFetchBC $0dda` (bank-12 table `$4f97+[$c85c]*2`).
- Layout VERIFIED: `[+0]`=world, `[+5]`=world (duplicate, for
  B<97), `[+6]`=stage-in-world. B=0..96 are clean: world 1
  B=0–7 stages 1–8; world 2 B=8–19 stages 1–12; world 3
  B=20–27 stages 1–8; world 4 B=28–39 stages 1–12; world 5
  B=40–51 stages 1–12; world 6 B=52–59 stages 1–8; world 7
  B=60–71 stages 1–12; world 8 B=72–87 stages 1–16; world 9
  B=88–96 stages 1–9. Evidence: bank `$18` record B=0 is
  `01 80 20 60 80 01 01 05` ([0]=01, [6]=01) matching the live
  (1,1); the instruction ring independently showed the `jr z`
  at `$272c` taken (record[0]==$01), which bank `$12`'s record
  (`03 44 01 f0 f0 f3 ee 40`) cannot produce.
- `[+1..+4]` are coordinate-like pairs (unresolved; often
  [1]==[3], e.g. B=0 `80 20 60 80`); `[+7]` is a small value
  4–40 for B<97 (unresolved). B=97..105 do NOT fit the
  pattern (worlds 0/110/62/28, stages 60/67/255/62) — role
  unresolved; the queue does contain C==1 entries with
  B=97..100 (C==1 B values are 0..100, each exactly once
  across 101 entries), so they may be reachable live.
- Also decoded: `$2738` sets bit 1 of `[$c70f]` when
  record[0]!=$01 and != prev record[0]; `$2758` sets bit 2
  when (stage−1)&3==0; `$288e` returns Z iff
  `([$c70f]&3)==3`, in which case the world/stage are read
  from the **previous** record (HL−=8) — the prev-record
  fallback. The bit-0 setter of `[$c70f]` is still unfound
  (open). Demo branch (`$2701`, B≥$c8): `[$c861]`=
  B−$af−$19+1, `[$c860]` stays 0.
- Carve: new `tools/gen_slice8.py` emits `src/bank24.asm`
  (106 records with world/stage annotations);
  `tools/gen_slice7.py` `emit_bank18` header corrected and
  `src/bank18.asm` regenerated — it keeps its bytes (bank
  `$12` $4934, 106 records, byte-correct) but is now honestly
  labelled "NOT the stage table, role unknown".
  `tools/gen_banks.py` CARVED gained
  `24: [(0x4934, 0x4C84)]`.

### 2. Death→timer-12 instruction — PINNED (both slice-7 candidates wrong)

- The write: frame 2668, cycle 4184, `$ff90` (hStateTimer)
  05→0c, by the instruction at bank `$10` (decimal 16)
  `$53c8`: `ldh [hStateTimer],a` with A=$0c (ROM bytes
  `e0 90`, preceded by `ld a,$0c` at `$53c6` and
  `ld hl,$ff91; ld a,[hl]; or $03; ld [hl],a` at
  `$53bf-$53c5`, which sets bits 0–1 of `[$ff91]`). The death
  run spec: progress-1 save,
  `start:620:632,a:1000:1012,a:2000:2012,right:2500:3000,a:2600:2612,a:2900:2912`,
  3000f; the only transition to $0c in 3000 frames was
  04→0c at frame 2668 (state 16, timer 12, `[$c711]`=$94,
  countdown not zero — confirming the `$0c2f` timeout path is
  ruled out, as slice 7 found).
- Call chain (128-instruction ring): state-16 timer code
  `$0874` (in `$0868`, the per-frame object-update routine
  called from timers 3/5/7/9) → `ld a,$10; rst $10; call
  $51c8` → bank $10 `$51c8-$51f5` → `$529a-$52e0` →
  `rst $08` at `$52e0` → dispatch handler `$0fd9` → table
  entry `$5664` → `$5349-$53c8` → write. Note `$0868` also
  calls bank-9 `$0bff` (the `$db15` object dispatch, slice 7's
  candidate) right before `$51c8`, in the same routine —
  right neighborhood, wrong instruction.
- Carve: `src/bank10.asm` (new, 1,285 lines, 1,179
  instructions in 4 spans: `$4031-$4044`, `$51c8-$52e7`,
  `$52e7-$5428`, `$5428-$59f1`; the span ends run through the
  rst-$08 tables, so the INCBIN gaps do not overlap them —
  the first attempt used `$52e1`/`$5406` ends and rgblink
  refused with an overlap error, which is what caught it).
  The `$52e0` rst-$08 table (3 entries: `$5349, $53fc,
  $5664`) and the `$5405` rst-$08 table (17 entries) are
  emitted as `dw`. Out-of-window targets `$2b30`/`$2b3c`
  are bank-0 routines already carved in
  `src/bank0slice3.asm`. The `$4031` span is a 19-byte
  routine whose entry mechanism is unverified (it ran in the
  death-run ring before `$0874`). `tools/gen_banks.py`
  CARVED gained
  `16: [(0x4031,0x4044),(0x51C8,0x52E7),(0x52E7,0x5428),(0x5428,0x59F1)]`.

### 3. Completing stage 1-1 live — IN PROGRESS (key collected, door not yet reached)

- New tools: `tools/gb_watch.c` (two-pass write watchpoint;
  values in watch specs are **hex** — `ff90=12` matches
  timer **18**, decimal timer 12 is `ff90=0c`) and
  `tools/gb_wramdump.c` (full WRAM+HRAM+VRAM dumps at
  selected frames; both in `tools/`, build commands in their
  headers).
- Mario's position by WRAM diff: `$c200` record 0 byte 7
  (`$c207`) = X, byte 3 (`$c203`) = Y (mirrors OAM `$c001`/
  `$c000`). At stage start Mario is OAM (17,136) = screen
  (9,120). Record 0 layout: byte 0 = type ($01 = active
  sprite), byte 3 = Y, byte 7 = X.
- Key position VERIFIED: background tiles `$3b`/`$3c` at
  tilemap `$9800` row 5, cols 9–10 → screen (72–87, 40–47),
  center ≈ screen (80,44), OAM (88,60). Confirmed by
  rendering tiles as ASCII (diagonal key shape) and by an
  annotated screenshot.
- Door position NOT yet positively identified (open). The
  top-right structure first thought to be the door is a
  ladder (screen x≈144–152, y≈16–48). Tiles `$c0`–`$c3`
  (rows 9–10, cols 12–13) are a gun/cannon pointing left;
  tiles `$b6`–`$b9` (rows 15–16, cols 12–13) are plain brick.
  The tilemap `$9800` is the displayed BG (`$9c00` is mostly
  blank). Stage layout from tilemap/screenshot: parasol box
  top-left (cols 0–3, rows 1–3); top girder rows 2–3 cols
  11–19; key niche rows 4–5 cols 8–11; middle column cols
  7–11 rows 7–14 (solid); ladders at col 6 (rows 6–10, tile
  `$30`) and col 5 (rows 15–16); ground girder row 17; Mario
  starts bottom-left, Pauline bottom-right (OAM (136,144)).
  Tile renders and crops are in `/tmp/slice8/` (ephemeral).
- New autopilot `tools/gb_play.c` (greedy fork-based; build
  command in its header): runs the intro, waits for the
  first playable frame (state 16, timer 3, Mario x<200 and
  y<200 — playable frame is 2499), then per 15-frame chunk
  forks one child per action (wait/right/left/up/down/
  right+A/left+A/A/B/right+B), each reporting Mario pos,
  key-present flag, death (timer 12 seen, or lives dropped)
  and stage-clear; the parent picks the best score, applies
  it, and repeats. On stall (no score improvement for 10
  chunks) or all-actions-die it backtracks by replaying from
  frame 0 to the last decision point with an untried action.
  Terminal is the real stage-clear (timer ≥33 — the
  33→40→42→43→44→45 chain; the first version used ≥23 and
  false-fired on timer 28, part of the normal post-(3,1)
  level-load chain 3→28→29→30→31→32→3).
- **Bug found by the score audit (slice 8): the two score
  branches were swapped** — the key-present branch scored
  distance-to-door and the key-collected branch scored
  distance-to-key, so the first two play runs (play2, play3)
  optimized "go to the door" from the start and never
  collected the key. Fixed in `tools/gb_play.c` (key present
  → distance-to-waypoint/key; key gone → distance-to-door),
  visit penalty 150→60/visit.
- **Waypoints were needed twice.** Plain distance-to-key
  leads Mario right along the ground into a local optimum
  (he never climbs, because walking right always scores
  better than climbing at each step); plain distance-to-door
  stalls the same way after the key, because the route
  backtracks down to the ground first. `gb_play` now takes
  pre-key waypoints (argv[5]) and post-key waypoints
  (argv[6]), each reached within 12px; the key waypoint is
  reached only when the key is actually collected.
- Play runs (all on the original ROM; the rebuilt ROM has
  not yet been run through a completion):
  - play2 (buggy score, 150 chunks): Mario walked right
    along the ground to (113,136), jumped around, reached
    the bottom-right (155,136) and up to (156,37) — proving
    the top-right is reachable — but never climbed a ladder
    and never reached the key; ended at max chunks.
  - play3 (fixed score, no waypoints, 172 chunks): Mario
    reached (124,56) near the key's height but oscillated
    at (116–124, 56–72), never reaching the key (88,60);
    the visit penalty drove him left/down.
  - play4 (waypoints `56,136;56,56;88,60`, 147 chunks):
    **key collected** — Mario reached (80,60) key=0 at
    chunk 31, via the col-5/col-6 ladders. Post-key he
    oscillated at (51–71, 59–90) near the ladder area and
    never reached the door.
  - play5 (added post-key waypoints `56,136;152,136`, 197
    chunks): key collected at chunk 31; both post-key
    waypoints reached (Mario got down to the ground and
    across to (152,136)); then stalled oscillating at
    (116–124, 56–72) — the climb from the ground-right to
    the door was not found.
  - play6 (added climb waypoints `148,112;148,88;148,64;
    152,40`, 250 chunks, 197 used): key collected at chunk
    31; ALL post-key waypoints reached (Mario climbed to
    (149,39) at chunk 64 and (156,35)/(156,39) repeatedly)
    — but stage-clear NEVER fired, and Mario kept falling
    back to (116–124, 56–72). Root cause: the door prior
    (152,40) was at the WRONG height. At (156,35) Mario is
    at the apex of a jump / on no floor, and he falls to
    y=50, y=64; the score penalized jumping up to the top
    girder (y≈16) because that moved AWAY from the (152,40)
    prior (distance term −10/px beats the upward bias
    +2/px). The door is plausibly ON the top girder (row 2,
    y=16–23), so the prior is corrected to (152,20).
  - play7 (door prior corrected to (152,20), last waypoint
    (152,20), 250 chunks, 205 used): key collected at chunk
    31; Mario reached the top girder — (128,23) at chunk 199
    and (120,19) at chunk 200, the closest yet — but he
    cannot LAND on it. His jump apex is y≈19, 3px below the
    girder top (y=16); from (120,19) every action falls to
    y=34, and he drifts left/down and stalls. The final step
    needs a jump from a takeoff at y≈40 (row 5), whose apex
    (y≈15) would clear the girder — the greedy does not
    chain it, because from the apex (y=23) a second jump
    only reaches y=19.
  - play8 (added takeoff waypoint (140,40), 250 chunks, 207
    used): key collected at chunk 31; all post-key waypoints
    reached, including (140,40) and (152,20); Mario reached
    (105,23) and (97,19) at chunks 205–206 — again y=19,
    now at x=97–105 — but never lands on the girder and
    never triggers the door.
  - **Jump height measured (slice 8): Mario's jump is 16px,
    not 25px.** Holding A from the ground (y=136) reaches
    apex y=120 and lands back at 136 (gb_wramdump, frames
    2500–2540). So the 24px girder gaps (row 14→11→8) cannot
    be jumped — they need the ladders. The right-side
    $50/$51/$52/$53 tiles at rows 5–6 and rows 9–10 (cols
    18–19) are ladder segments: the route is ground (136)
    → row 14 (112) → row 11 (88) → climb rows 9–10 ladder
    to 72 → jump to 56 → climb rows 5–6 ladder to 40 →
    jump to 24 → land on the girder (16). Play6/7/8's
    (148,64) waypoint sat in a gap between the ladders and
    demanded a 24px jump Mario cannot make — that is why
    they stalled at y=56–72.
  - play9 (post-key waypoints follow the right-side ladders:
    `56,136;152,136;152,112;152,88;152,72;152,40;152,16`,
    250 chunks, 201 used): key collected at chunk 31; all
    post-key waypoints reached, including (152,16); Mario
    reached (153,19) at chunk 74 — essentially on the door
    prior — but he was in mid-air, not standing: he fell to
    (150,34), (142,52), (140,64) over the next chunks. The
    top girder does NOT support Mario at x=153 (walking
    left from (153,19) falls to y=34 instead of staying at
    y=19). He ends drifting at (100–117, 32–48).
  - **Door findings (slice 8).** The door is NOT a
    background tile that appears after the key (tilemap diff
    pre-key frame 2500 vs post-key frame 3000 shows only the
    key tiles changing: `$3b/$3c/$3d/$3e` → `$3f/$40/$41/
    $42`, a 2x2 block at rows 5–6, cols 9–10) and NOT a
    sprite (OAM at frame 3000 has no new sprite near the
    top-right; the sprites present are Mario, Pauline, and
    the parasol/bonus items, several of which move). The
    door is therefore a fixed background structure or a
    position trigger, not yet identified. Candidates tested
    and NOT triggered by jumping/falling through: (152,40)
    [play6: (149,39)/(156,35) repeatedly], (152,20)
    [play9: (153,19)]. Remaining hypothesis: the door needs
    Mario STANDING at (152,40) — top of the rows 5–6 ladder
    (cols 18–19), climbed, not jumped.
  - play10 (post-key waypoints end at (152,40), door prior
    (152,40), 250 chunks, 195 used): key collected at chunk
    31; all post-key waypoints reached, including (152,40)
    13 times; Mario ends oscillating at (116–124, 56–72).
    Standing at (152,40) did not trigger the door (or Mario
    never actually stood there — the waypoint is "reached"
    within 12px, which includes (152,48)/(144,40)).
  - **Schedule-replay divergence (methodological, slice 8).**
    Replaying a play run's printed SCHEDULE through
    `gb_wramdump`/`gb_headless` reproduces it EXACTLY for
    the first ~10 chunks (frame 2648 = (49,87) and frame
    2663 = (41,83) match play10's log exactly) but then
    drifts: by frame 2994 Mario is 2px off play10's
    position, by frame 3009 he is stuck at (69,89) while
    play10 has him moving, and by frame 3309 the replay is
    on a different screen entirely (Mario (176,16), lives 0,
    state 19, a dense non-stage tilemap). The early
    1-frame/1px seed is not understood — the press windows
    use the same [start,end) semantics in gb_play,
    gb_headless, and gb_wramdump, and the intro table
    matches — but the drift compounds through the physics,
    so a SCHEDULE replay is NOT a reliable verification.
    A future completion must be verified inside gb_play
    itself (it already reports STAGE CLEAR + done=0/1) or
    the divergence source found. The frame-3600 "different
    screen" and Mario-at-(176,16) findings are artifacts
    of the diverged replay, NOT real game states — disregard
    them. (The stage is 160px wide: tilemap cols 20–31 are
    all $00 at stage start.)
  - **Door re-think (slice 8).** The $c0–$c3 2x2 block at
    rows 9–10, cols 12–13 (screen x=96–111, y=72–87) renders
    as a frame (vertical bars + bottom bar), consistent with
    a doorway, and is the one door-like structure never
    tested as a prior. Mario oscillates at (116–124, 56–72)
    just above it in the earlier runs, never dropping to
    y=88–96 to touch it, because the prior pulled him up.
  - play11 (door prior (112,96) — the $c0–$c3 block, post-key
    waypoint (112,96), 250 chunks, 193 used): key collected
    at chunk 31; Mario reached (116,98) at chunk 188 —
    INSIDE the $c0–$c3 block's OAM range — and (110,112),
    (100,113), (92,98), (90,103) around it, but no
    stage-clear fired. The $c0–$c3 block is NOT the door
    (or touching it is not enough).
  - **Door status at end of slice 8: UNIDENTIFIED.** Three
    candidates tested with no trigger: (152,40) [play6/10],
    (152,20) [play9], (112,96) [$c0–$c3 block, play11].
    The door is not a background tile appearing after the
    key and not a sprite in OAM. The $db15 records (stride
    15) are packed/flag-like, not clean x/y — decoding
    their stream format (likely via the bank-9 $0bff object
    dispatch) is the next step for slice 9, along with
    finding what sets timer 33 in the state-16 timer code.
    The state never left 16 in any play run and timer 33–45
    was never seen, so the terminal check (state 16,
    timer ≥33) is correct — it simply never fired.

### 4. Byte-match + Nacre (slice 8)

- Clean `make` (build/game.gb removed first): rebuilt SHA-1
  `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs
  (after the bank-24 carve, after the bank-10 carve, and
  after the span-end fix).
- `tools/run_slice5_regression.sh`: exit 0, "ALL REGRESSION
  CASES IDENTICAL" (re-run after the bank-10 carve).
- `tools/run_slice7_cases.sh`: exit 0, "ALL SLICE-7 CASES
  IDENTICAL" (re-run after the bank-10 carve; f1 fb
  `1cf92679…`, death fb `632b2eaf…` reproduce slice 7).
- Slice 8 NOT pushed (coordinator handles pushes).

## Next slices (priority order)

1. **Gameplay: complete stage 1-1 live (key -> door).**
   Slice 8 collected the key live (play4/play5, chunk 31,
   (80,60)) and proved the post-key route down to the ground
   and across to (152,136) — but no run has yet completed 1-1
   to watch the queue advance 16->17 and the (2,1) dispatch
   fire. Remaining: the door's exact position/trigger is
   UNIDENTIFIED (slice 8 §3) — three candidates tested with
   no trigger: (152,40), (152,20), and (112,96) [$c0–$c3
   block]. Slice 9 should decode the $db15 stream format
   (bank-9 $0bff object dispatch) and find what sets timer
   33 in the state-16 timer code, then complete 1-1. Once a
   run completes, verify the winning schedule by replaying
   it with `gb_headless` on both the original and rebuilt
   ROMs (framebuffer hash + state trace + save identical) —
   but note the slice-8 schedule-replay divergence (the
   SCHEDULE drifts slowly through gb_headless, so verify
   inside gb_play itself or find the divergence source
   first). Also open: the `[$c70f]` bit-0 setter
   (never found in carved code).
2. **Bank-11 sprite blocks.** The bank-11 table's pointed-to
   sprite blocks ($42xx-$71xx) are still raw data, and the
   table's extent (128 entries) is inferred, not verified
   against live record[0] values. (The stage-table layout is
   RESOLVED — slice 8 §1 — and the death->timer-12
   instruction is PINNED — slice 8 §2.)
3. **Roles for the carved code.** Bank 7 `$6f62` and bank 23
   `$7722` are pinned (slice 7 §2); bank 10 `$51c8`/`$5349`
   are pinned (slice 8 §2). Still open: bank 7
   `$4794`, `$77a9`/`$78ba` roles from slice 4; the `$3414`
   dispatcher and the `$b4ca-$b927` SRAM writer are resolved
   (slice 6 §2, §4).
4. **Further carves.** Whole banks 4, 6, 8–10, 13–15, 17,
   19–22, 25–31 still largely raw (bank 16 and bank 24 are
   now partially carved — slice 8). Next candidates by
   dependency: bank 12 `$5917+` data/credits, the bank-11
   sprite blocks the `$4000` table points at, bank 9 `$0bff`
   object dispatch (it runs in the same `$0868` routine as
   the death path, right before `$51c8`). Bank 11 `$4000`,
   bank 18 `$4934`, bank 24 `$4934`, bank 10 `$51c8-$59f1`,
   and bank 0 `$17eb-$1d06` are done (slices 7–8).

## Not done / blocked

- Nothing is blocked. States 21/22 are now VERDICTED
  unreachable by mechanism (slice 5 — a finding, not a
  block; see Slice 5) and their contents are read (slice 6
  §7). Player-driven state-20 gameplay is now visited live:
  slice 7 proved the playable stage runs in state 16
  (timers 3-10) and corrected slice 6's "(2,1) is the
  blocker" premise — (2,1)@17 is the post-completion entry,
  reached only after completing 1-1 (key -> door), which no
  run has done yet (see Next slices §1). CORRECTION (slice 6
  §3): slice 4's "save VALIDATES" was overstated — the f1 save fails its
  own validation because `$4cbe` never writes `$be2a`; a
  hand-crafted save must fix the `$a000`/`$be2c` checksum
  pairs (`tools/make_progress_save.py` now does). Save RAM
  (battery) behaviour was exercised in slice 4 (write via
  state-28 file 1 + A, reload). Ghidra was not needed:
  mgbdis + hand-checking against the bytes covered slices
  1–3, and the recursive-descent disassembler
  (`tools/gb_rd.py`) covered slices 4–7. It may still be
  useful for banked code later.
- Open (slice 8, not blocks): the door position/trigger is
  not positively identified (prior OAM (152,40) is a guess);
  no run has completed 1-1 yet (key collected, climb to the
  door pending — play6 running). The `[$c70f]` bit-0 setter
  is not found in carved code. The bank-11 table's extent
  (128 entries) is inferred, not verified against live
  record[0] values. Stage-table records B=97..105 do not fit
  the (world,stage) pattern — role unresolved. The bank-10
  `$4031` routine's entry mechanism is unverified.
- Pushed: slice 1 `62d9e52c`, slice 2 `6a21aa7f`, slice 3
  `e8d923ee858b188e2aa4ec229d0aae4f5156bc0f` (16 files, 887,317
  bytes; sync record `~/workspace/mike-monorepo.muse-github-snapshot-sync.json`),
  slice 4 `17b86513f1387c36b06107c7fc50c9677417ad23` (16 files,
  832,860 bytes; same sync record), slice 5
  `e9b049b5a481984b3c2dc68e23433f5b6d224301` (11 files; same sync
  record).
- The generator script for the slice-2 files is in `/tmp/gen_slice2.py`
  (ephemeral — see Slice 2 notes); the durable output is `src/*.asm`.
  Slice 3's generator is in the repo (`tools/gen_slice3.py`).
- `tools/gb_headless` (compiled binary) is in the repo but not in
  any push (see slice 1 note — keep-or-exclude undecided; it
  rebuilds from `tools/gb_headless.c` with the command in the
  file header). `tools/gb_probe17` + `tools/gb_probe17.c` are
  likewise build products of a one-shot probe; the `.c` is the
  durable part.
- State 12 residue: three `e0 8e` pairs in data regions
  (banks 0x15/0x19/0x1b) classified as data, not code; the one
  instruction that decs 18→17 inside the stream loader is
  unidentified. Neither affects the verdict (see Slice 3).
- The generator script for the slice-2 files is in `/tmp/gen_slice2.py`
  (ephemeral — see Slice 2 notes); the durable output is `src/*.asm`.
