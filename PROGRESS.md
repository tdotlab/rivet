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

## Next slices (priority order)

1. **Banked sub-step bodies, continued** — bank 5 (`$24e7`
   stage loaders; the timer-29 source in state 16), bank 7
   (`$7168`/`$7169`, called from TransitionStep0's tail), bank
   2/3/12 stream-loader code behind the `$30xx` routines, bank
   12 `$4f97` queue table as `db` pairs, bank 1 `$48d0-$48ff`
   counting data as `db`, bank 23 `$7722` `rst $08` site, bank
   12 `$5917+` data/credits.
2. **Gameplay:** drive the rebuilt ROM further with the fixed
   harness — file-select confirmation (state 8: file 2+ + A/B
   in state 17/28, which should exercise the `$c80f`/`$c810`
   pair return live), first stage gameplay past state 20, save
   RAM behaviour (battery: write a save, reload, check
   `$09f0` → state 21/22), state 26/30 paths.
3. **Gameplay code in banks 1–31** beyond the state sub-steps.

## Not done / blocked

- Nothing is blocked. Save RAM (battery) behaviour was not
  exercised. Ghidra was not needed: mgbdis + hand-checking
  against the bytes covered slices 1–3. It may still be useful
  for banked code later.
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
