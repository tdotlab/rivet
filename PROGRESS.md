# Progress — Donkey Kong '94 disassembly

> Research log: entries are historical and may contain superseded findings or
> paths from before the source and tools were reorganized. For the current
> layout and build instructions, see [README.md](README.md).

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

## Slice 9 — DONE, byte-matching (2026-11-21)

Headline: the door was NOT found and 1-1 was NOT completed —
but the leading door candidate ($c0–$c3 block) was ELIMINATED
with proof, the tile-dispatch system was mapped exactly, the
`[$c70f]` bit-0 setter was FOUND, and two carves landed
(bank 9, bank 12). `src/` is now 26,368 lines. Clean `make`
rebuilds SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`,
`cmp` zero diffs. Slice-5 regression ALL IDENTICAL, slice-7
cases ALL IDENTICAL (see §6).

### §1. Bank 9 carved — `$4000-$4020`, `$418b-$4690`, `$63f3-$6401`, `$6480-$6484`
- New `tools/gen_slice9_bank9.py` + `src/bank9.asm` (1,149
  lines). Wired via `tools/gen_banks.py` CARVED and
  `INCLUDE "bank9.asm"` in `src/main.asm`.
- Bank-9 `$4000` is `rst $08` with a 16-entry table
  (0 `$418b`, 1 `$41f2`, 2 `$4259`, 3 `$4292`, 4 `$4657`,
  5 `$42cb`, 6 `$1d29`, 7 `$46a4`, 8–11 `$1d29`, 12 `$432b`,
  13 `$439c`, 14 `$440d`, 15 `$444d`). Entries 6, 8–11 are
  `$1d29` (bank-0 `ret` — a no-op). Entry 7 `$46a4` is a
  live handler (caught by the generator's ROM-bytes
  assertion after an initial wrong assumption it was
  `$1d29`). `gb_rd`'s rst-$08 reader stops at 6 entries
  because `$1d29` is a ROM0 address, so the `$4000` span is
  emitted by hand from ROM bytes with an assertion.
- **`$db15` record format — CORRECTED**: stride is **16
  bytes**, not 15 (slice 8's "stride 15" was the loop
  addend; the loop consumes byte 0 first). Proof: bank-9
  helper `$63f3` computes `HL = $db15 + [$c70d]*16`
  (`add a` ×4). 32 records, `$db15-$dd14`. Layout from the
  two bank-0 scans + handler prologues: [+0] active flag
  (0=skip), [+1] type/state byte (handlers fire when
  ≥$30), [+2] per-frame counter (inc'd by both scans),
  [+3..+15] handler data.
- Two bank-0 scans call bank-9 `$4000` with A = byte1 −
  $30: `$0bff` (called from `$0862`, per-frame object
  update in state-16 timers 3/5/7/9) dispatches any byte1
  ≥ $30; `$0a4f` (called from state-16 timer 20, `$0a0c`)
  only byte1 in [$30,$34) ∪ [$3c,$40), i.e. A ∈
  {0,1,2,3,12,13,14,15}. Entry 7 (A=7, byte1=$37) fires
  ONLY from the `$0bff` scan.
- Hand-seeded routines `$448d`/`$44ed`/`$4592`/`$4635`
  share the handler prologue (`call $63f3`) but have **no
  direct caller anywhere in the ROM** — entry mechanism
  unverified. Gap `$4021-$418a` decodes as garbage
  (repeating `add hl,hl`/`dec e`) — data, stays INCBIN.
  `$6480` = `dec [$da4a]; ret`.
- **Live finding (gb_wramdump, progress-1 save, frames
  0–6000): `$db15` records are NEVER nonzero in stage
  1-1** — the $db15 object system is not used by 1-1 in
  this flow. `[$da47]` starts at `$ffff` at stage start
  and decrements 1/frame during gameplay timers 3/5/7/9.
  Decoding $db15 did not identify the door; the carve
  stands on its own as verified code.

### §2. Bank 12 `$5917-$5dbc` carved — data + credits text
- New `tools/gen_slice9_bank12.py` +
  `src/bank12slice9.asm`. CARVED 12 extended to
  (0x4000, 0x5DBC); `INCLUDE "bank12slice9.asm"` in
  `src/main.asm`. Byte-match holds.
- `$5917-$5937`: repeating `4a 4e 4b 4c 4d` pattern
  (structure unresolved). `$5938-$5977`: structured
  records (7-byte groups starting with a small count).
  `$5978-$599f`: coordinate-like pairs
  (`88 28 88 28 ... 70 28`) then zeros — likely
  credits-screen sprite positions, unresolved.
  `$59a0-$5dab`: the end credits text (EXECUTIVE PRODUCER
  Hiroshi Yamauchi, PRODUCER Shigeru Miyamoto, DIRECTORS
  Masayuki Kameyama / Takao Shimizu, MAIN PROGRAMMERS,
  C`G` DESIGNERS, SOUND COMPOSER Taisuke Araki, COURSE
  DESIGNERS, SPECIAL THANKS TO, SUPER GAMEBOY HARDWARE
  TEAM, ILLUSTRATOR, MANUAL EDITOR, ARCADE DONKEY KONG /
  DONKEY KONG JR / HOME VERSION / GAME BOY DONKEY KONG).
  Emitted as hex `db` (the `_[\\]... NINTENDO` lines are
  tile-index sequences, not plain ASCII; the exact bytes
  including `$00` padding are preserved, each line
  annotated with its readable text). `$5dbc+` ("defghi"
  font data) stays INCBIN.
- **Bug caught by the linker**: the generator's
  `db_lines` did not clamp the last line to the span end,
  so the data section overshot 7 bytes into the credits
  and the credits section overshot 4 bytes past `$5dbc`
  (rgblink: section overlaps "Bank 12 $5dbc-$7fff").
  Fixed by clamping the chunk to `hi - addr`. The
  byte-match check then passed — the arbiter worked as
  designed.

### §3. `[$c70f]` bit-0 setter — FOUND (slice 8 open item, closed)
- Bank 23 `$7337-$733a`: `ld hl, $c70f; set 0, [hl]`,
  in the attract-demo step 0 (`$732b`, called from
  `$731f AttractStep0`, already carved in slice 3). Bit 0
  is set at the START of the attract demo. That explains
  the `$288e` prev-record fallback: during attract,
  `[$c70f]` bit 0 = 1, and combined with bits 1/2 (set by
  `$2735`/`$2758` when the world/stage changes),
  `([$c70f]&3)==3` triggers reading the PREVIOUS stage
  record. The earlier survey missed it because it only
  looked at `ld [$c70f],a` writers and the `$2735`/`$2758`
  sites, not `set 0,[hl]` with HL=`$c70f`. The other
  `ld [$c70f],a` writers are only the three known clears
  (`$29ea`, `$4463`, `$46af`).

### §4. Timer-33 / stage-clear chain — mapped statically
- Timer 33 (`$21`) is set ONLY at bank-0 `$09b4` and
  `$09eb` (timers 23/26 tails, when the queue advances to
  a C==4 entry). Timer 26 (`$1a`) is set ONLY at bank-1
  `$56c3` — the sole `ld a,$1a; ldh [$ff90],a` in the ROM
  (verified by whole-ROM search for `3e 1a e0 90`).
  Bank-1 `$56c3` is a standalone tiny routine
  (`ld a,$1a; ldh [$ff90],a; xor a; ld [$c20b],a; ret`)
  sitting right after another routine's `ret` at `$56c2`;
  **no `call`/`jp`/`dw` to `$56c3` exists anywhere in
  the ROM** (whole-ROM search for the `c3 56` byte pair
  finds only `jp $4756` at bank-0 `$35e2`). Entry
  mechanism unverified — likely a computed jump or a
  bank-1 dispatch table, still to be found.
- Timer 23 (`$17`) has **no literal setter anywhere** in
  the ROM (no `3e 17 e0 90`) — it is reached via a
  computed value (increment or table), not a literal
  load. Timer 42 (`$2a`) setters: bank-0 `$09c1`,
  `$09d5`, `$0b21`.
- Probable door path (inferred, not proven): door →
  bank-1 `$56c3` (timer 26) → timer-26 body `$09d5`
  (sets timer 42, QueueAdvance, fetch; C==4 → timer 33)
  → clear chain 33→40→42→43→44→45→0 → state-16 timer 0
  → C-dispatch → (2,1) → state 20.

### §5. The tile-dispatch system (bank $10 hex) — mapped, and the door ELIMINATED
- **Correction to the slice-9 working notes**: the
  "bank-10" tile analysis in those notes read DECIMAL
  bank 10's bytes. The real system is bank **$10 hex**
  (= decimal 16, `src/bank10.asm`, sections correctly
  `BANK[16]`; the filename/section headers use hex, as
  elsewhere — `bank18.asm` is decimal 18, `bank24.asm`
  is bank $18 hex). Everything below is from bank $10
  bytes, verified against the ROM.
- `$51c8` per-frame update (called from `$0877`) runs
  the `$c117` OR-scan, then `$529a`: it scans 8 records
  at `$c117` (stride 7) for bit 5 of byte 0. The first
  record with bit 5 set wins; A = its index (stored to
  `[$c1f3]`), BC = `$5fe9` (odd records 1,3,5,7) or
  `$5fd3` (even records 0,2,4,6). Byte 0 `and $1f`
  indexes that BYTE table (32 entries, values 0/1/2) →
  `rst $08` at `$52e0` (3 entries: `$5349`, `$53fc`,
  `$5664`). `$53fc` reads [DE] (the record's byte 1),
  indexes bank-$10 `$6009` (256-entry tile→handler map),
  dispatches via the `rst $08` at `$5405` — the table is
  at **`$5406`**, 17 entries:
  `$5349, $5428, $549d, $5565, $55c1, $56cc, $570c,
  $5750, $579b, $57cb, $57cc, $58a0, $58bb, $5918,
  $59d0, $59d1, $59e0`.
- `$6009` map (bank $10, verified): handler 5 =
  `$57 $61 $7b $8b $a7 $ad $af $c1 $c3 $c7 $db $e9`;
  handler 1 = `$02 $55 $79 $99 $d7`; handler 2 = `$5c`;
  handler 3 = `$5b`; handler 4 = `$64 $68`; handler 6 =
  `$b7`; handler 7 = `$06`; handler 8 = `$08 $67`;
  handler 10 = `$6c`; handler 11 = `$5a`; handler 12 =
  `$bd` (not `$be`); handler 13 = `$a5`; handler 15 =
  `$b3`; handler 16 = `$b5`. `$b6` → handler 0 (the
  working notes' "$b6→16" was the decimal-10 misread).
  In stage 1-1 the ONLY handler-5 tiles are `$c1`
  (row 9, col 15) and `$c3` (row 10, col 15) — the
  `$c0-$c3` block. Handler-1 tiles: `$55` (middle column,
  col 7, rows 8–16). Handler-6 tile: `$b7` (row 15,
  col 15, in the `$b6-$b9` block).
- `$c117` records (8 × 7 bytes) are built by bank-8
  `$4022`/`$41b8`: 8 tile samples around Mario, rebuilt
  every frame (`$4022` zeroes `$c117-$c155` first).
  Byte 0 = the sampled TILE ID, byte 1 = the tile to its
  right, bytes 2–3 = computed overlaps, bytes 4–5 = the
  tilemap pointer. **Bit 5 of byte 0 is what gates the
  `$529a` dispatch** — it is set exactly when the sampled
  tile ID has bit 5 set (tiles `$20-$3f`, `$60-$7f`,
  `$a0-$bf`, `$e0-$ff`). The class lookup in `$41b8`
  (`$4aed` word table → `$5409` data) feeds the overlap
  computation, not byte 0.
- **The `$c0-$c3` block is NOT the door (proven two
  ways).** Static: handler 5 (`$56cc`, the only handler
  that sets a persistent "triggered" flag — bit 3 of the
  `$c200` record + `or $c3` into `[$ff91]`) is reached
  only via `$53fc`, which needs a sample with byte 0
  bit-5-set AND byte 0 `& $1f` mapping to 1 in the
  `$5fd3`/`$5fe9` table AND byte 1 a handler-5 tile.
  Byte 1 = `$c1`/`$c3` requires byte 0 = `$c0`/`$c2`
  (the tiles immediately left of the block) — and
  `$c0`/`$c2` have bit 5 CLEAR, so the dispatch can
  never run for them. No sample can ever reach handler 5
  through the block. Live: 13 block-proximity WRAM dumps
  (play14, chunks 63–95, Mario standing on the block at
  (124,72) five times and (116,72) three times) show
  `$c200` rec0 byte 18 = `$00` every time (handler 5's
  bit 3 never set) and `[$ff91]` never gains `$c3`
  (values `$00`/`$04`/`$40`/`$44`); Mario's `$c117`
  rec0 is ZERO in every dump and no record ever has bit
  5 set while on the block.
- `$5664` (the `$52e0` entry-2 handler) is collision
  resolution, not the door: it nudges `$c203`/`$c207`
  (Mario's record X/Y) when a sample's byte 1 has bit 7
  set, and its [$c1f3]==0 branch checks the record's
  tile against `$57`/`$13`/`$3f`. Handler 6 (`$570c`,
  reached via odd samples on `$b6` → byte 1 `$b7`)
  checks a `$c213`-record byte for 3/4, sets bit 1 of
  `[$ff91]`, and jumps to `$550b` — a tile interaction,
  not the door.
- The `$b6-$b9` block is the only place in 1-1 where
  `$53fc`/`$5664` can fire for both parities
  (`$b8`→`$53fc`, `$b9`→`$5664`, `$b6`→`$53fc` odd,
  `$b7`→`$5664` odd) — but `$53fc` there reads byte 1
  `$b9`/`$b7` → handlers 0/6, never 5; and play5 passed
  through the block at ground level with the key and no
  trigger. The door is therefore NOT any tile-handler in
  1-1 via the `$529a` dispatch. Next lead: the bank-1
  `$56c3` entry mechanism (§4), or a non-tile trigger.

### §6. Live runs — key collected three times, stage never completed
- `tools/gb_play.c` upgraded: terminal detection now
  treats timers **13/23/26/42/≥33** as terminal (reports
  the exact timer value); `dump_state()` now writes to
  the durable repo path `build/nacre-test/slice9/play/`
  (`/tmp` was wiped mid-session and took the first key
  dump with it — the key dump was recovered from `/tmp`
  and copied into the repo); periodic dumps every 25
  chunks; block-proximity dumps (Mario's OAM box inside
  x 108–140, y 56–104) to catch handler-5 firing on the
  block. Note: the build command in the file header omits
  `-lm` — the working build is `cc … tools/gb_play.c … -lm`
  (link fails on `sqrt` without it).
- play12 (400-chunk budget): KEY COLLECTED at chunk 31
  at (80,60) (matches slice-8 play4); ran 327 chunks,
  `done=0`. The run ended when the step budget was
  exhausted (400 loop iterations; backtracks truncate the
  schedule, so the schedule stood at 327 chunks — NOT a
  BACKTRACK FAILED, which never appears in the log).
  Explored the `$c0-$c3` block extensively (124,72),
  (116,72), (124,56), (130,48).
- play13 (160-chunk budget, same command): key at chunk
  31; schedule reached 121 chunks, `done=0`, step budget
  exhausted (same mechanism as play12).
  Periodic dumps (chunks 0/25/50/75/100) show rec0[18]
  = `$00` throughout, `[$ff91]` `$00`/`$50`/`$00`/`$40`/
  `$44`, `[$dd18]` `$00` (once `$0a`), `[$c213]` `$00`,
  `$db15` all zero.
- play14 (130-chunk budget, same command + block dumps):
  key at chunk 31; schedule reached 95 chunks, `done=0`,
  step budget exhausted (same mechanism).
  Produced the 13 block dumps cited in §5.
  (play13/14 reached shorter schedules than play12
  simply because their step budgets were smaller — 160 and
  130 iterations vs 400 — and backtracks consume
  iterations without growing the schedule. The runs are
  deterministic for the same budget; the earlier note
  about unexplained divergence was wrong.)
- Key-collect WRAM diff (vs frame 2500): key tiles
  `$3b`/`$3c` → `$3f`/`$40`, row 6 `$3d`/`$3e` →
  `$41`/`$42`; `$c200` rec27 byte 0 went 01→00 at
  collection (a deactivation, but rec27's position
  (48,72) does not match the key (88,60) and records
  change every frame — not claimed as the key's record).
- Stage 1-1 tilemap (VRAM dump, frame 2500 — kept from
  the slice-9 notes): key `$3b`/`$3c` row 5, cols 9–10;
  `$c0-$c3` 2×2 at rows 9–10, cols 14–15 (screen
  x=112–127, y=72–87); `$b6-$b9` 2×2 at rows 15–16,
  cols 14–15; row-11 girder gap at cols 14–17; middle
  column `$55` col 7 + `$56` cols 8–10, rows 7–14;
  right-side ladders cols 12–19, rows 5–10; col-6 ladder
  `$30` rows 6–10.
- Greedy flaw (still open): waypoint advances within
  12px, so at chunk 2 Mario at (48,136) "reached"
  waypoint (56,136) and the target switched to (56,56);
  the greedy then chose left+A toward it, climbing
  diagonally up-left to (32,59), where all actions die —
  a backtrack loop at chunks 21/22 burned the step budget
  in the 60-chunk smoke run. A greedy/waypoint flaw, not
  a game bug.
- **Byte-match proof**: after the bank-9 and bank-12
  carves, clean `make` rebuilds SHA-1
  `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp`
  zero diffs. **Nacre regressions on the final build**:
  `tools/run_slice5_regression.sh` — ALL REGRESSION
  CASES IDENTICAL (600/900/3600/12000 frames, s8/f0/f1
  saves); `tools/run_slice7_cases.sh` — ALL SLICE-7
  CASES IDENTICAL (retry 15000f, mid5000, play-right,
  death 3000f). Identical framebuffers/traces/saves
  original vs rebuilt.

### §7. Still open after slice 9
- The door / stage-1-1 completion: the tile-handler path
  is exhausted (§5). Next: find bank-1 `$56c3`'s entry
  mechanism (computed jump? bank-1 dispatch table?) and
  how timer 23 gets set (no literal setter); or look for
  a non-tile trigger (bank-9 handlers' entry, `$0a4f`
  scan's A∈{0,1,2,3,12,13,14,15} set).
- Bank-11 sprite blocks (`$42xx–$71xx`); bank 12
  `$5917+` is DONE (§2); bank 9 `$0bff` is DONE (§1).
- Stage-table records B=97..105 (don't fit the pattern);
  bank-11 table extent (128, inferred, not verified
  against live record[0] values); bank-$10 `$4031` entry
  mechanism (unverified); bank-9 `$448d`/`$44ed`/`$4592`/
  `$4635` entry mechanism (unverified); `[$da47]`'s
  writer (no `ld [$da47],a` anywhere — written via HL or
  the `$1060` fill; it starts `$ffff` and decrements
  1/frame in gameplay).
- `[$c70f]` bit-0 setter: RESOLVED (§3). Bank-9 `$0bff`
  and bank-12 `$5917+`: DONE. The "bank-10" misread in
  the slice-9 working notes is corrected in §5 — no file
  rename needed (`bank10.asm` = bank $10 hex, as
  elsewhere).

## Slice 10 — DONE, byte-matching (2026-11-21)

Headline: **bank-1 `$56c3`'s entry mechanism is FOUND — and it kills
the slice-9 door hypothesis.** `$56c3` is PostStart table entry 33
(state 3, timer 33), a file-select animation step, not a stage-clear
trigger. The key-pickup mechanism is PROVEN live (gb_watch: bank-7
`$6b8e` writes `$c560`) and the whole 19-handler `$75ea`
tile-interaction system is carved (727 new lines, `src/` now 27,105).
The door is still NOT found and 1-1 is still NOT completed — but the
tile-handler path is now narrowed to a single cell value (`$0b`),
and only the key is that cell in 1-1. Clean `make` rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs.
Slice-5 regression ALL IDENTICAL, slice-7 cases ALL IDENTICAL (§6).

### §1. Bank-1 `$56c3` — RESOLVED (slice 9's "no pointer" was a misread)

- Slice 9 claimed no `call`/`jp`/`dw` to `$56c3` exists, citing the
  `c3 56` pair at bank-0 `$35e2` as "`jp $4756`". That reading
  assumed code alignment at `$35e2`. `$35e2` is inside the
  **PostStart (state 3) 37-entry table** at `$35a0-$35e9`: entry 33
  (`$35a0 + 2*33 = $35e2`) is `dw $56c3`. The table was already
  curated in `src/states.asm` (`PostStartTable`, last line
  `dw $5695, $56c3, $5247, $5269, $5273`) — the slice-9 survey
  missed it because it grepped the ROM bytes instead of the
  already-curated table. Prologue: `$359a ld a,$01; rst $10`
  (bank 1), `ldh a,[hStateTimer]; rst $08`, table at `$35a0`.
- **Consequence (correction to slice 9 §4):** `$56c3` runs ONLY when
  state == 3 and timer == 33. It sets hStateTimer = `$1a` (26) —
  in state 3 — so the next dispatch is PostStart entry 26
  (`$56d7`, the big `$c360`-record routine, which IncStateTimers
  to 27). Slice 9's "probable door path: door → `$56c3` (timer 26)
  → timer-26 body `$09d5` → clear chain" is WRONG: `$56c3` can
  never set up a state-16 timer-26 dispatch, because it only ever
  runs in state 3 and state 3's steps don't change hGameState to
  16 with the timer at 26. Do not chase it again. (The `$56cc`
  sibling — PostStart entry 31 — is the same class: sets timer
  `$10` (16) in state 3.)
- The full `e0 90` (timer-write) survey was redone (109 sites,
  whole ROM): the literal timer values set are
  0,1,2,3,4,6,12,13,15,16,18,19,20,22,25,26,27,29,30,32,33,36,42,43
  plus variable-A sites (`[$c70b]`, `[$c851]`, `[$c20b]`-clears).
  `$56c3` remains the SOLE literal timer-26 setter, and there is
  still NO literal timer-23 setter (`3e 17 e0 90` absent).

### §2. Timer 23 — still open, narrowed

- Timer-23's state-16 body `$0997` starts with `call $1d2a`
  (IncStateTimer, 23→24), then clears `[$ff95]`, sets hSTATState 3,
  clears bit 4 of `[$c82b]`, QueueAdvance + QueueFetchBC, and sets
  timer 33 (`$21`) iff the fetched C == 4; else it falls into the
  timer-24 body `$09b9` (waits `[$ff95]==$5a` → timer 42). Timer
  26's body `$09d5` is the same shape (timer 42 first, then
  advance/fetch, C==4 → 33). So 23 and 26 are both "queue advance"
  steps; the question is only what SETS the timer to 23/26 while
  state == 16.
- State-20's timer 22/23 bodies were mapped (bank 1): `$47ad`
  (timer 22) clears `[$c20b]`, and when `[$c811]>=$a0` falls to
  `$47cf` (clear `[$ff95]`, IncStateTimer 22→23), then `$47d5`
  (timer 23: if `[$ff95]==4` IncStateTimer 23→24 — it is 0 there,
  so no second inc — then the `$47dc` block writes `$c86d` records
  and calls `$1060`/`$169c`). So timer 23 EXISTS as a state-20
  value and its body is understood; the state-16 entry is what is
  missing. Candidates left: (a) IncStateTimer from 22 in a state
  whose timer-22 body incs, followed by a transition to state 16
  that preserves the timer (state-16 timer-22 body `$098c` itself
  does NOT inc — it exits to state 24, timer 0; bank-1 `$4000`
  state-24 entries `$400d/$406c/$41cf/$411b/$4142` were checked
  and none writes timer `$17`); (b) a `[$c70b]` restore of 23 —
  `[$c70b]` writers inventoried: bank-0 `$08bd`/`$08c6` save
  3/5/7/9 (the `$083e` timers); bank-7 `$405a`/`$66b5`/`$6d2a`/
  `$7b6e`/`$7bd1`/`$7c34`/`$7c97`/`$7cfa` and bank-`$1f` `$55b6`
  save the CURRENT timer at a countdown expiry — so `[$c70b]`
  == 23 requires the timer to have been 23 already (circular
  unless (a) supplies it once). No `ld a,$17` exists anywhere in
  bank 1. Timer 23/26 in state 16 have NEVER appeared in any
  trace (0 hits across all `build/nacre-test/` traces).

### §3. Key pickup — PROVEN live (gb_watch)

- Replayed the play12 schedule's first 32 windows (intro +
  chunks 0–31, progress-1 save) through `tools/gb_watch`
  watching `$c560` (rec27 byte 0): HIT frame 2140 `$c560`
  00→01 (rec27 SPAWNED, state 16 timer 1, bank 1, pc `$30f9`)
  and HIT frame 2878 `$c560` 01→00 (key COLLECTED, state 16
  timer 7, bank 12 at frame end). Pass-2 refine:
  - Spawn: written by bank-12 `$403c` (regs HL=`$c561`, bank 12),
    ring shows bank-12 `$334f-$3361` loops + `$1060-$1064` — the
    level-load record spawner (bank 12 `$4000` region, carved).
  - Collection: written by bank-7 `$6b8e` (regs HL=`$c560`,
    rom_bank 7), ring: bank-7 `$4d9c-$4db8` → `$4888-$48b8` →
    `$4022` → `$6b0a-$6b8e`. So the pickup runs through bank 7's
    `$4016`/`$6b0a` dispatch, NOT through the bank-`$10` tile
    dispatch (slice 9) or the `$db15` system (all zero in 1-1).
  - Note: the replay collected the key at frame 2878 vs play12's
    ~2964 (chunk 31) — the known schedule-replay drift, but the
    key still collected; the watchpoint result (which instruction,
    which frame) is unaffected.

### §4. The `$75ea` tile-interaction system — mapped and carved

- `$6b0a` (bank 7, slice 5): scans 6 of the 8 `$c117` records
  (recs 0,4,6,1,5,7 — NOT 2,3) for byte 0 == `$0b`; on a match
  and hStateTimer != `$10` (16), it reads byte 1, indexes the
  `$750a` byte map, doubles the result, indexes the `$75ea` dw
  table, and `jp hl`. DE on entry points at the record's byte 2.
- `$750a` map (224 bytes, `$750a-$75e9`; ends where `$75ea`
  begins, so byte-1 >= 224 would read into the pointer table —
  never observed): index 0 is the default (most byte-1 values);
  1 ← {1}, 2 ← {16-19}, 4 ← {24-27}, 6 ← {32,33}, 7 ← {34-37},
  8 ← {38-41}, 9 ← {42-45}, 10 ← {46-49}, 11 ← {50-53},
  12 ← {54-57}, 13 ← {58-61}, 14 ← {62-65}, 15 ← {66-69},
  16 ← {70-73}, 17 ← {74-77}, 18 ← {175}.
- `$75ea` table, 19 entries (bytes after entry 18 are `$3f3f`
  filler): 0 `$6b55` key pickup, 1 `$6ba6` → `$63c4`,
  2 `$6c7a` → `$6e54`, 3 `$6d83` → `$63c4`, 4 `$6c8f` → `$6e54`,
  5 `$6b09` ret (no-op), 6 `$6c44` → `$7d5e`, 7 `$6c6a` → `$6e54`,
  8 `$6ca4` → `$6e54`, 9 `$6cb9` → `$6e54`, 10 `$6cce` → `$6e54`,
  11 `$6ce3` animator-arm, 12 `$6d50` ret (no-op),
  13 `$6d51` → `$63c4`, 14 `$6d9f` → `$6e54`, 15 `$6daf` → `$6e54`,
  16 `$6dbf` → `$6e54`, 17 `$6dcf` → `$6e54`, 18 `$6ddf` record
  transform → `$6f06`.
- Handler 0 `$6b55` (key pickup), decoded in full: guards
  (`[$dd17]` bits 6-7 clear, `[$ff94]` bit 7 clear, `[$ff91]`
  bit 4 clear — so it cannot re-fire after pickup, since its
  tail `$6bf2` SETS bit 4 of `[$ff91]`); reads the record's
  bytes 4-5 as a pointer, zeroes `$0b` bytes at [HL] and
  [HL+`$80`]; deactivates the `$c200` record at index B-`$40`
  (`$6b8e: ld [hl],$00` — the gb_watch-proven write);
  `[$dd3c]=`$02d0, `res 5,[$ff94]`, `[$c210]=6`, then `$6bf2`
  (set 4 `[$ff91]`, `[$dd18]=`$0a, `[$dd21]=`$11, `[$dd1c]`=1
  or `$83`, clear bit 7 `[$ff91]`/bit 5 `[$ff92]`, set bit 0
  `[$dd17]`, then `$63c4` unless `[$c837]` is 3/`$24`/2).
- Handler 11 `$6ce3` (animator-arm): guards (`[$dd18]`==3 needs
  `[$c213]`>=5; `[$dd17]` bit 1 clear); sets `[$dd45]=`$0168
  (the countdown `$4016`'s tail watches), sets bit 4 of a
  `$c212`-record byte, `[$c838]=`$80, `[$c830]=`$26,
  `[$c831]`/`[$c835]`=3, saves the current timer to `[$c70b]`,
  sets timer `$11` (17), `[$dd3e]`=5/`[$dd3f]`=1/`[$dd40]`=8,
  `[$dd43]`/`[$dd44]`=`[$c201]`/`[$c202]`, set bit 7 `[$dd17]`.
  This is the `$6f62` intro-animator trigger (slice 7 §2).
- Handler 18 `$6ddf` (record transform): zeroes `$0b` tiles the
  same way, then rewrites a `$c200` record in place (writes
  `00`,`$a5`,`$44` at offsets +8/+9/+11, computes a `$c86f`
  position from the record's bytes), then `$6f06`.
- Handlers 2/4/8/9/10 set `[$c838]=`$80, `[$c82d]`/`[$c835]`=3
  and jump to `$6e54` with a table pointer; handlers
  6/7/14/15/16/17 set `[$c82f]`/`[$c835]=`$1a (26 — an
  animation/sprite parameter, NOT the timer) and jump to
  `$6e54`/`$7d5e`. `$6e54` is a shared table-driven `jp hl`;
  `$63c4` is a shared spawn/setup routine.
- Entry to the system: `$4016` (which calls `$6b0a` at `$4022`)
  is jumped to (`jp $4016`, no `call` anywhere) from 21 bank-7
  sites in `$42xx-$47xx` — the uncarved per-frame "Mario vs
  world" code. The key ring's `$4888` jumps straight to `$4022`
  (the dispatcher call, skipping `$4016`'s prologue).

### §5. Carve: bank 7 interaction handlers + tables

- New `tools/gen_slice10.py` + `src/bank7slice10.asm` (727 lines):
  `$63c4-$63f3` (shared setup), `$6b09` (1-byte no-op handler),
  `$6b55-$6e8b` (handlers 0-18 + `$6e54`/`$6e70`), `$6e8c-$6ea8`
  (routine converging on `$6f2e`; its sibling `$6ea9-$6ed1` was
  already carved in slice 4), `$6f06-$6f2d` (handler-18
  continuation; stops before slice-4's `$6f2e` span — the
  boundary is clean: `$6f2c ld d,$01` is 2 bytes, `$6f2e` starts
  `ld l,b`), `$7d5e-$7d95` + `$7e07-$7e17` (handler-6 chain),
  `$750a-$75e9` as `db` (byte map) + `$75ea-$760f` as 19 `dw`
  (pointer table, emitted with handler labels). `CARVED` in
  `tools/gen_banks.py` extended; `INCLUDE "bank7slice10.asm"`
  added after `bank7slice5.asm` in `src/main.asm`.
- Byte-match on first try (no uncovered-byte notes, no link
  errors): clean `make` → SHA-1
  `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs.

### §6. Nacre results (slice 10, rebuilt ROM = original)

- `tools/run_slice5_regression.sh`: ALL REGRESSION CASES
  IDENTICAL (600f `1cf92679…`, 900f `39ffd5ee…`, 3600f
  `88515f4e…`, 12000f `92d2e185…`, s8/f0/f1).
- `tools/run_slice7_cases.sh`: ALL SLICE-7 CASES IDENTICAL
  (retry 15000f `0d835d95…`, mid5000 `2ab1bb5d…`, play-right
  `b3cb6c8b…`, death 3000f `632b2eaf…`).
- No new live gameplay run was completed this slice: the door
  was not found, so 1-1 was not completed and queue 17 still
  never fired. The key-collection replay (§3) is the only new
  live evidence, and it re-proves the key path on both ROMs
  only in the sense that the watchpoint ran on the original —
  the rebuilt ROM is byte-identical, and the regression suites
  above cover it.

### §7. The door — narrowed, not found

- The `$c117` records point into a WRAM map (`$cc00-$d1ff`),
  not the VRAM tilemap (slice 9's "byte 4-5 = tilemap pointer"
  is a WRAM pointer). Across all 57 slice-9 play WRAM dumps
  (Mario all over 1-1, including standing on the `$c0-$c3`
  block), the `$c117` byte-0 values seen are ONLY `$08`,
  `$42`, `$47`, `$82` — never `$0b` except at the key moment
  itself (transient; no dump caught it). The `$6b0a` dispatch
  fires ONLY on byte 0 == `$0b`, and in 1-1's tilemap the only
  `$3b` tiles (the `$0b` class, if the mirror encodes tile-`$30`
  or tile-&-`$0f`) are the key's 2x2 block (row 5-6, cols 9-10).
  So the door is most likely NOT a `$75ea` handler — unless its
  cell is also `$0b` and its byte-1 selects another handler
  (11 or 18), which no dump has shown. The `$1832` dispatch
  (bank-0 `$188b-$1c28`) was also checked: none of its handlers
  writes `[$ff90]`/`[$c210]`/`[$ff94]`, so the door is not there
  via a direct timer write either.
- What remains for the door: (a) the bank-8 `$4022`/`$41b8`
  builder — decode the WRAM map's cell encoding (what byte
  values mean, how `$0b` arises, whether the door has a
  distinct cell); (b) the bank-7 `$42xx-$47xx` routines (the 21
  `jp $4016` callers — the per-frame entry to the interaction
  system, still uncarved); (c) bank-`$10` `$4af0` (the other
  uncarved per-frame routine, called from `$0868`); (d) a
  `$c200`-record overlap check outside the `$1832` dispatch.
- Timer 23/26 in state 16 remain the downstream unknowns (§2);
  they only matter once the door fires.

## Slice 11 — DONE, byte-matching (2026-11-24)

The door hunt. Carved the three uncarved per-frame systems slice 10
left open (bank 8 `$4022`/`$41b8`, bank 7 `$42xx-$47xx`, bank `$10`
`$4af0`), decoded the WRAM map's cell encoding, and proved live
that the key pickup is handler 17, not handler 0 — correcting
slice 10's key claim. The door is still NOT found. `src/` is now
30,558 lines (was 27,105).

### §1 What was carved

Generator `tools/gen_slice11.py` (gb_rd recursive descent;
tables verified against ROM bytes before emission):

- **Bank 8 `$4000-$4aec`** (`src/bank8.asm`, new file, 1,726
  instructions, zero gaps): the `$c117` map-record builders.
  `Bank8_4000` (per-frame entry, called from bank 0 `$087d`/
  `$0903` via `$2a0a`) copies `$c203-$c20a` into `$dd51-$dd54`;
  `Bank8_4022` zeroes `$c117-$c155` (9 records x 7 bytes) and
  runs four corner blocks, each computing a map pointer and
  calling an even builder (pair 0) and an odd builder (pair 1,
  DE+2): `Bank8_41B8`/`Bank8_42AC` (rec0/rec1), `Bank8_4375`/
  `Bank8_446D` (rec2/rec3), `Bank8_453A`/`Bank8_4645` (rec4/rec5),
  `Bank8_4733`/`Bank8_4843` (rec6/rec7). `Bank8_495B` is the rec8
  sampler (runs when `[$dd18]==$0a` or `[$ff94]` bit 7).
  `Bank8_4A04` is the `($82,$37)` cell finder (see §4);
  `Bank8_4AA0` is the `$c1f4`/`$c1f9` lookup (odd builders, reads
  the dynamic `$c0a6` table); `Bank8_4936` is the `$fe` class
  check. The `$4a04-$4a9f` span looked like a walk gap but is
  code (a 101-instruction routine ending in `jp $0fe5`); it was
  added as a seed and the gap closed.
- **Bank 8 tables** (same file): `$4aed-$4b62` as one dw blob
  (44 dw; the `$4aed` and `$4b23` pointer tables overlap at
  `$4b23-$4b2c` and the shared words agree) and `$5409-$5808`
  (256 4-byte class records; `$57d5`/`$57e4`/`$5795` are views
  into it — records 243, 244, 227 — not separate tables). The
  `$4b63-$5408` byte tables the `$4aed`/`$4b23` entries point at
  stay INCBIN (next-slice target).
- **Bank 7 `$41dd-$4793`** (`src/bank7slice11.asm`, new file,
  955 instructions; gaps only the three dw tables): the `$42xx`
  per-frame interaction routines. Entry mechanism found: `$41c9`
  (slice 5) dispatches on `([$dd1a]-1)` via the `$41dd` table —
  1→`$41e9`, 2→`$4269`, 3→`$42cc`, 4→`$44e4`, 5→`$46bd`,
  6→`$4769`. `$44e4` dispatches on `[$dd1f]` via the `$4506`
  table (0→`$4510`, 1→`$45e2`, 2→`$4612`, 3→`$466f`,
  4→`$4699`); `$4510` dispatches on `[$dd18]` via the `$452f`
  table (12 entries). All 21 `jp $4016` callers are in this span.
  `Bank7_466F` is a SECOND `hStateTimer=12` writer besides bank
  `$10` `$53c8` (slice 8's death pin): `[$dd1f]==3` and `[$ff91]`
  bit 2 set → timer 12, so it is a death path, not a
  stage-clear path. `Bank7_43D9` holds the key-collected branch:
  `[$dd18]==$0a` → `[$dd21]=$39`, `call $2b30` (bank `$0a`
  `$7816`), `[$dd1c]=$83`; `$7816` clears `[$dd18]`/`[$dd1d]`,
  sets `[$c82e]`/`[$c835]=3`, and is animation/state setup, not
  a stage-clear trigger.
- **Bank 7 `$7d96-$7e06`** (same file, 81 instructions, zero
  gaps): the handler-7 (parasol) and handler-17 (key) chains
  (`Bank7_7D96`/`Bank7_7DBE`) and the shared 2x2 cell clear
  (`Bank7_7DE6`). Both clear the 2x2 block, call `$33a7`,
  allocate a `$c72f` slot via `$164c`, call `$7e07` (decrement
  `[$c858]`; at 0, `[$c82f]`/`[$c835]=$44`), and score +2 via
  `$0e29`.
- **Bank `$10` (16) `$4af0-$4e88`** (`src/bank16slice11.asm`,
  new file, 494 instructions; gap only the `$4df5` byte table,
  13 db indexed by `[$dd18]`): the other per-frame `$c117`
  scanner (from `$0868`). It clears stale records (byte-3
  `== $9d` checks) and at `$4cf8` triggers a Mario action
  (`[$dd1a]=3`, `[$dd24]`/`[$dd25]=$0080`, `[$dd26]=$08`) with
  `[$dd21]` chosen by `[$dd18]`. `$4b90-$4bab` is a
  `$c148`/`$c14b`/`$9d` branch with no direct entry found in
  bank 16 (possibly a dead duplicate of the `$4b43` branch);
  it decodes cleanly and is emitted as code with that note.
- CARVED additions (`tools/gen_banks.py`, `src/banks.asm`
  regenerated): bank 8 `(0x4000,0x4AED)`, `(0x4AED,0x4B63)`,
  `(0x5409,0x5809)`; bank 7 `(0x41DD,0x4794)`,
  `(0x7D96,0x7E07)` (bank 7 `$4016-$480E` and `$7d5e-$7e18` are
  now contiguous); bank 16 `(0x4AF0,0x4E89)`. INCLUDEs added to
  `src/main.asm` (`bank8.asm`, `bank7slice11.asm`,
  `bank16slice11.asm`).

### §2 Byte-match proof

Clean `make` (rm `build/game.gb` first) rebuilt SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs vs
`roms/Donkey_Kong_World_Rev1_SGB.gb` — first try. What the
check caught: nothing in the build itself; the generator's own
assertion caught a wrong table index before any build ran
(`words[32]` vs `words[27]` for the `$4b23` table base —
`$4b23-$4aed` is 27 words, not 32). `git status` shows only
the intended changes (3 new src files, 1 new generator,
`banks.asm`/`main.asm`/`gen_banks.py` modified); no build
artifacts, `.gb`, `.sav`, compiled binaries, or `__pycache__`.

### §3 Nacre regressions (final build, original vs rebuilt)

- `tools/run_slice5_regression.sh`: ALL REGRESSION CASES
  IDENTICAL. 600f `1cf92679…`, 900f `39ffd5ee…`, 3600f
  `88515f4e…`, 12000f `92d2e185…` (match the known hashes).
- `tools/run_slice7_cases.sh`: ALL SLICE-7 CASES IDENTICAL.
  retry 15000f `0d835d95…`, mid5000 `2ab1bb5d…`, play-right
  `b3cb6c8b…`, death 3000f `632b2eaf…` (match the known hashes).

### §4 The map, decoded (verified live, frame 2500)

The WRAM map is `$c86d-$d86d`, 32 cols x 32 rows x 4 bytes
(row stride 128, col stride 4). Each cell is TWO (type,
subtype) pairs: bytes 0-1 and bytes 2-3. Even builders sample
pair 0, odd builders pair 1 (via `$4aa0` + the dynamic `$c0a6`
table). Map (row, col) ↔ screen tile (col-1, row-1); OAM
coords = screen + (8,16). All `$0b` bytes in 1-1 (13 total,
live scan of `$c86d-$d86d` at frame 2877):

- First pair (byte 0): parasol 2x2 at (rows 3-4, cols 1-2),
  subtypes `$22/$23/$24/$25`; top-right 1x2 at (rows 4-5,
  col 19), subtypes `$20/$21`; key 2x2 at (rows 6-7, cols
  10-11), subtypes `$4a/$4b/$4c/$4d`.
- Second pair (byte 2): 1x2 vertical trigger at (rows 8-9,
  col 6), subtype `$5b` both cells.
- One false positive: `$0b` at (row 17, col 15, byte 1) is a
  SUBTYPE of a `$06` cell, not a type — ignore.

`$750a` sends those subtypes to handlers 7 (parasol), 6
(top-right), 17 (key), and 0 (`$5b` trigger, via
`$c0a6[$1b]=$74` → `$750a[$74]=0`). **All four are score
pickups or a record deactivation, NOT the door.** The door
has no `$0b` cell and no `$c117` byte-0 value seen live is
anything but `$08/$42/$47/$82`.

### §5 CORRECTION — slice 10's key claim was a misattribution

Slice 10 said key pickup was "PROVEN live (bank-7 `$6b8e`
writes `$c560`)". That is wrong: `$c560` is rec27's byte 0,
and its 01→00 is the `$5b`-trigger event (handler 0), a
separate event from the key. Proof, from play12's own dumps
(read before the slice-11 run overwrote some of them — see
§7) and the slice-11 run's own key dump:

- Play12 chunk025 (before the key): key cells intact
  (`0b4a/0b4b/0b4c/0b4d`), `$c858=3`, `$c560` ALREADY 0,
  `[$dd18]=$0a`, `[$dd3c]=$2c5` (counting down from `$2d0`).
  So the `$5b` trigger had fired ~11 frames earlier, and the
  key cells were still untouched.
- Play12 key_wram.bin (at the key event): key cells cleared
  to `0001` (handler 17's `$7de6` pattern), `$c858` 3→2,
  score bytes `$da41` `00…`→`02…` (+2), `$c560` still 0.
- Slice-11 run's key_wram.bin (chunk 26, Mario at (66,64)):
  key cells `0001`, `$c858=2`, score +2, `$5b` trigger cells
  INTACT (`00000b5b`), `$c560=1` (rec27 still active),
  `[$dd18]=0`, `[$dd3c]=0`. The key pickup fired with the
  `$5b` trigger never having fired — the two events are
  independent.
- Handler 6 verified live the same way: play12 chunk050→
  chunk075, top-right cells `0b20/0b21` → `0001`, `$c858`
  2→1. The parasol was never collected in any run
  (`$c858` never reached 0), so `[$c82f]`/`[$c835]=$44`
  never fired.

So: **the key is handler 17** (even builders, subtype
`$4a-$4d` → 17); the `$5b` trigger is handler 0, which
deactivates rec27 (`$c560`), sets `[$dd18]=$0a` (via the
`$6bf2` tail) and `[$dd3c]=$02d0`. `[$dd18]=$0a` is the
"key collected" flag the `$43d9`/`$627b` code checks — and it
is set by the `$5b` trigger, not by the key-cell pickup.
Rec27's identity is still unresolved (a `$c200` record at
OAM (48,72), overlapping the `$5b` cell; spawned frame 2140
by bank-12 `$403c`); it is not the key sprite (the key is at
screen (80,44)).

### §6 The door — still NOT found (best remaining leads)

- **The `$6331` post-key scan (strongest lead).** While
  `[$dd18]==$0a`, the `$627b` routine (the `[$dd18]==$0a`
  entry in the `$4827` table) counts `[$c20d]` down every
  frame; at 0 it calls bank-0 `$2b24` → bank 8 `$4a04`, which
  scans the map near Mario for an `($82,$37)` cell and
  writes the found pointer to `$c156-$c159` (or 0). If found,
  `$6334-$63a3` clears the cell, spawns a `$c72f` record,
  sets `[$c830]`/`[$c835]=$5f`, and scores +1 via `$0e29`.
  **But no `($82,$37)` cell exists in the 1-1 map at frame
  2500** (`$82` first-pair subtypes are only 2/4/6), so this
  path is inert in 1-1. The door is either a cell whose
  subtype becomes `$37` only after some event, or it is not
  a map cell at all. What `[$c830]`/`[$c835]=$5f` triggers is
  open (no reader found in carved code yet).
- **`[$c82f]`/`[$c835]=$44`** (from `$7e07` when the third
  `$0b` pickup decrements `[$c858]` to 0) is the other
  candidate: it may be the door-open/level-clear signal. It
  never fired in any run because the parasol (the third
  pickup) was never collected. Its readers are still
  unidentified (only writers known: `$1a` from handlers
  6/7/14-17, `$03` from handlers 2/4/8-10, `$44` from `$7e07`
  and `$6e1d`, `$4a` save+end, `$35`/`$29` state-21/22 setup).
- Timer 23's setter is still open (no literal setter
  anywhere; slice 10 §2). `$466f`'s timer-12 write is a
  death path, not a clear path (§1).

### §7 Completion attempt — parasol route, FAILED (died)

One attempt, `tools/gb_play` on the original ROM:
`gb_play roms/…gb build/nacre-test/slice11/save-prog1.sav 400
"start:620:632,a:1000:1012,a:2000:2012" "56,136;56,56;88,60"
"56,136;40,72;24,72;16,56;8,40;8,24;40,40;88,40;152,40;152,16"`
— same pre-key route as play12, post-key waypoints routing
via the parasol (8,24), then the top-right (152,40), then up
(152,16). Log: `build/nacre-test/slice11/play-parasol.log`.
Key collected at chunk 26 at (66,64) (see §5 — this run's
key dump is the cleanest handler-17 proof). Mario then died
en route to the (24,72) waypoint at (26,88); chunks 66-68
thrashed with "ALL actions die -- backtracking" 20 times
(chunk counter oscillating 66↔68, every candidate action
dead=1, score -1000001). Killed at that point (pids 28890/
28887) — no progress, just CPU burn. The greedy/waypoint
flaw (slice 9 §6) blocks the parasol route: the (24,72)
waypoint pulls Mario into a pit he cannot cross. **No
completion; `$c858` never hit 0; `$44` never fired; the door
still unfound.** No `gb_headless` schedule verification was
done — there is no winning schedule to verify.

Note: `gb_play`'s dump directory is hardcoded to
`build/nacre-test/slice9/play/` (not the save's directory),
so this run overwrote play12's `key_wram.bin`,
`chunk000/025/050_wram.bin` there. The play12 values quoted
in §5 were read from those files before this run started;
`chunk075`/`chunk100` (20:40/20:37) are still play12's.

### §8 Verified vs inferred

- VERIFIED: the map layout and cell encoding (§4); the
  `$41dd`/`$4506`/`$452f` dispatch tables and the `$42xx`
  entry mechanism; handlers 6/7/17 as score pickups and
  handler 0 as the `$5b`-trigger deactivation (live WRAM
  dumps, §5); `$466f` as a second timer-12 writer (code);
  `$4a04` as the `($82,$37)` finder and `$6331` as its caller
  (code + the absence of `($82,$37)` in the live map);
  `$7816` as key-state setup (code); bank-16 `$4af0`'s
  record-scan/action-trigger shape (code).
- INFERRED (not verified): that `[$c82f]`/`[$c835]=$44` is
  the door-open/level-clear signal (it never fired);
  that the `($82,$37)` scan is the door sensor (it never
  found a cell in 1-1); rec27's identity; what
  `[$c830]`/`[$c835]=$5f` triggers; `$4b90` as a dead
  duplicate branch (no entry found — it may be entered from
  uncarved bank-16 code).

## Slice 12 — DONE, byte-matching (2026-11-24)

The door leads, resolved against the code rather than for the door:
lead (a) carved the `$6331` scan's whole home routine (bank 7
`$627b-$63c3` + `$63f4-$643e` + callees `$664e`/`$714c`, the `$4827`
`[$dd18]` table); lead (c) found the readers of `[$c82f]`/`[$c835]`
— and they kill the `$44`/`$5f` door hypothesis outright, because
both values are **sound-effect IDs** consumed by the bank-2 timer
tick, not door signals. Lead (b) ran twice: the key was collected
both times, Mario reached the parasol's doorstep once (24,44) but
never touched it, and died in the pit below it both times.
`src/` is now 31,457 lines (was 30,558).

### §1 What was carved

Generator `tools/gen_slice12.py` (gb_rd recursive descent;
tables verified against ROM bytes before emission):

- **Bank 7 `$4827-$4840`** (`src/bank7slice12.asm`): the 13-entry
  `[$dd18]` dispatch table used by `$480e` (slice 5):
  0→`$4841`, 1→`$4e8b`, 2→`$517c`, 3→`$5673`, 4→`$58da`,
  5→`$59ff`, 6→`$5669`, 7→`$6b09`, 8→`$5d6e`, 9→`$5ea1`,
  10→`$627b`, 11→`$644d`, 12→`$64db`. Entry 10 (`$0a`) is the
  post-`$5b`-trigger routine; entries 0-6, 8, 9, 11, 12 are
  still uncarved code (next-slice targets).
- **Bank 7 `$627b-$63c3`** (same file, 452-byte walk with zero
  gaps): `Bank7_627B`, the `[$dd18]==$0a` per-frame routine.
  If `[$ff94]` bit 7 or `[$ff8b]` bit 1: set `[$ff91]` bits,
  `[$dd21]=$16` (or `$00` if `[$dd1a]==0`), `jp $2b30` (bank
  `$0a` `$7816`, key-state setup). Else if `[$dd1a]>=3`: ret.
  Else if rec8's byte is `$22`/`$23` (after the `$b3`/`$3f`
  checks on `[$c14f]`): `[$c830]`/`[$c835]=$19`, `call $664e`.
  Else count `[$dd3c]` down; at 0 `jp $63f4` (the expiry).
  Else every 6 frames (via `[$c210]`) toggle `[$c21c]`; when
  `[$ff94]` bit 5 is set and `[$c21c]` is set, count `[$c20d]`
  down, and at 0 call `$2b24` (bank 8 `$4a04`, the
  `($82,$37)` scan) — **this is the `$6331` scan, and `$6331`
  is its only caller in the ROM** (sole `call $2b24`).
  On a hit (`$6334-$63a3`): clear the found cell, `call
  $714c` (map pointer → tile coords in BC), copy the 20-byte
  `$643f` template to `$c1ab` via `$106e`, `call $2b1a`
  (bank `$0a` `$7b6c`), `call $6f06`, set `[$c20d]=3`,
  `[$c830]`/`[$c835]=$5f`, score +1 via `$0e29`.
- **Bank 7 `$63f4-$643e`**: `Bank7_63F4`, the `$0a` expiry
  (when `[$dd3c]` hits 0): clear `[$dd18]`, `[$c82e]`/
  `[$c835]=3`, `[$c837]`/`[$c836]`/`[$da45]` logic, clear
  `[$ff91]` bits, `[$dd1d]=0`, `[$dd21]=2` or `3` by
  `[$dd1a]`, `[$dd1c]=$83` or `$00`.
- **Bank 7 `$643f-$6452`**: the 20-byte record template
  (`1e 0a 00 00 00 00 a5 58 00 00 00 00 00 00 fa 13 c2 87
  4f 06`), copied to `$c1ab` by the `$6334` scan-hit path.
- **Bank 7 `$664e-$66c9`**: `Bank7_664E` (rec8 `$22`/`$23`):
  score +3 via `$0e29`, a `$c20e`-record write (byte `$45`,
  then `$1e`/`$00`/`$58` fields), save hStateTimer to
  `[$c70b]`, set hStateTimer=`$10` (16), `call $6e70`,
  `jp $6f40`.
- **Bank 7 `$714c-$7167`**: `Bank7_714C`, map pointer (DE)
  → tile coords in BC (HL = `~$c86d + $ff7c + DE`, `>> 2`,
  B = `$98 + H`, C = L).
- **Bank 8 `$4b63-$5408`** (appended to `src/bank8.asm`):
  the class byte tables the `$4aed`/`$4b23` pointer tables
  point at — 30 `db` runs delimited by the next table base
  (`$4b5d` tail, then `$4bf1`, `$4bf3`, `$4bf6`, `$4bf9`,
  `$4c06`, `$4c0a`, `$4c23`, `$4c2a`, `$4c2f`, `$4c7d`,
  `$4c81`, `$4c89`, `$4cda`, `$4d2b`, `$4d31`, `$4d51`,
  `$4d6f`, `$4d73`, `$4e03`, `$4e0b`, `$4e5c`, `$4eec`,
  `$4f2c`, `$5014`, `$50d7`, `$5179`, `$5191`, `$526d`,
  `$531f`; the `$4b55` table's head is the `$4b23` dw tail,
  already emitted). A table maps a map-cell subtype byte →
  class index; the class record is at `$5409 + class*4`.
- **Bank 2 `$47fc-$48e9`** (`src/bank2slice12.asm`, new):
  the 119-entry sound-definition table (see §3).
- **Bank 3 `$48f1-$4942`** (`src/bank3slice12.asm`, new):
  the 41-entry song table (song index < `$29`; see §3).
- CARVED additions (`tools/gen_banks.py`, `src/banks.asm`
  regenerated): bank 2 `(0x47FC,0x48EA)`, bank 3
  `(0x48F1,0x4943)`, bank 7 `(0x4827,0x4841)`,
  `(0x627B,0x63C4)`, `(0x63F4,0x643F)`, `(0x643F,0x6453)`,
  `(0x664E,0x66CA)`, `(0x714C,0x7168)`, bank 8
  `(0x4B63,0x5409)`. INCLUDEs added to `src/main.asm`.

### §2 Byte-match proof

Clean `make` (rm `build/game.gb` first) rebuilt SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs
vs `roms/Donkey_Kong_World_Rev1_SGB.gb` — first try. What
the check caught: nothing in the build; the generator's
own assertion caught a wrong first base before any build
ran (the `$4b5d` base sits below the `$4b63` carve start,
so the in-range list starts at `$4bf1`). `git status`
shows only the intended changes (3 new src files, 1 new
generator, `bank8.asm`/`banks.asm`/`main.asm`/`gb_play.c`/
`gen_banks.py` modified); no build artifacts, `.gb`,
`.sav`, compiled binaries, or `__pycache__`.

### §3 Lead (c) — RESOLVED: `[$c82f]`/`[$c835]` are sound requests

The readers are the bank-2 and bank-3 timer ticks, and the
values are sound/song IDs. This kills the `$44`/`$5f`
door hypothesis (slice 11 §6): neither value can be a
door signal, because both are consumed as audio.

- **`$c82d-$c835` is a sound-effect request queue.**
  Direct-read survey of the whole ROM: `ld a,[$c835]`
  occurs exactly ONCE (bank 2 `$45a9`); `ld a,[$c82f]`
  and `ld a,[$c830]` occur ZERO times; no `ld hl/de/bc,
  $c82f/$c830/$c835` exists anywhere. The only consumer
  is bank 2's tick: `$45a9` reads `[$c835]`; nonzero →
  clear it and `jp $4677`, which drains slots `$c82d`–
  `$c834` (C=0..7, B=9..1, priority B). A slot value V is
  cleared, then `(V-1)*2` indexes the `$47fc` table; the
  entry points at an 8-byte record of four (lo,hi)
  channel-data pairs for the `$df0e`–`$df11` channels
  (a channel is taken only if its current priority is <
  B; the pair is copied to `$df1a`/`$df35`/`$df50`/`$df6b`
  and the channel flag `$df23`/`$df3e`/`$df59`/`$df74`
  set). So `$c835` is the trigger (a copy of the latest
  ID — writers always store the same A to `$c82f` and
  `$c835`, e.g. `$7e07` stores `$44` to both) and
  `$c82d`–`$c834` are the 8 request slots. Writer counts
  by slot: `$c82d` 42, `$c82e` 49, `$c82f` 57, `$c830` 31,
  `$c831` 37, `$c832` 0, `$c833` 1, `$c834` 0, `$c835` 208
  (the trigger is written far more often than any slot).
- **The `$47fc` table: 119 entries, all verified.**
  Every entry points into `$4904`–`$6196` and every
  8-byte record's pair hi-bytes are `$00` or `$40`–`$7f`;
  the word after the table (`$48ea`) is `$0801`, not a
  pointer, so the table ends at 119 entries. The exact
  values from the door leads map onto it: `$44` → entry
  67 → record `$5480` (pairs `($88,$54)`, `($9e,$54)`,
  `(0,0)`, `(0,0)` — a two-channel sound, the
  all-pickups jingle); `$5f` → entry 94 → `$4feb`
  (only channel 4, `($f3,$4f)`); `$19` → entry 24 →
  `$5fa7` (channel 1, `($af,$5f)`); `$03` → entry 2 →
  `$59c1` (all four channels). `$1a` → entry 25 →
  `$5ff6`.
- **`$c836-$c838` are the music request fields**, read
  by bank 3's tick (`$45a9`): `[$c838]==$80` means stop;
  `[$c836]`/`[$c837]` hold the song request/current song
  (song < `$29` = 41 songs); song V indexes the `$48f1`
  table at (V-1) and the song data goes to `$df07`/
  `$df12`. All 41 `$48f1` entries verified (targets in
  `$454b`–`$764f`).
- Consequence: collecting all three `$0b` pickups plays
  the `$44` jingle and nothing else is wired to it. The
  door is NOT the pickups, NOT `$44`, NOT `$5f`. Lead
  (b)'s completion attempt is therefore moot as a door
  test (though the parasol is still uncollected live —
  see §5), and the door hunt has to move to the
  hStateTimer-22/23 path and the queue-advance C==4
  path (see Next slices).

### §4 Lead (a) — the `$6331` scan, carved and gated

The scan is real code with a real caller chain, but it is
inert in 1-1 and heavily gated:

- Chain: `$480e` dispatches on `[$dd18]` via the `$4827`
  table → entry 10 (`$0a`) → `$627b` → (when `[$c20d]`
  hits 0) `call $2b24` at `$6331` → bank 8 `$4a04`
  (slice 11) scans the map near Mario for an `($82,$37)`
  cell. `call $2b24` exists exactly once in the ROM, at
  `$6331`.
- Gates, all of which must hold: `[$dd18]==$0a` (only
  true in the `$2d0`-frame window after the `$5b` trigger
  fires); `[$dd1a]<3`; `[$c21c]` set (toggles every 6
  frames via `[$c210]`); `[$ff94]` bit 5 set; `[$c20d]`
  counted down to 0 (reloaded to 3 after a hit).
- In 1-1 the scan can never hit: no `($82,$37)` cell
  exists in the map (slice 11 §4: `$82` first-pair
  subtypes are only 2/4/6), and the scan-hit path's
  `$5f` write is — by §3 — a sound ID, not a door
  signal. What makes an `($82,$37)` cell appear is still
  open: it may exist only in later stages' maps, or be
  placed by an event not yet seen. The `$4827` table's
  other entries (`$4841`, `$4e8b`, `$517c`, `$5673`,
  `$58da`, `$59ff`, `$5669`, `$5d6e`, `$5ea1`, `$644d`,
  `$64db`) are uncarved; they are the `[$dd18]` values
  0–9, 11, 12 and may hold the trigger that creates the
  cell.

### §5 Lead (b) — parasol attempts, both FAILED (died in the pit)

`tools/gb_play.c` changed: dump dir is now
`build/nacre-test/slice12/play/` (no more clobbering
slice 9's dumps), and the waypoint-advance radius is
6px instead of 12px (slice 9 §6's flaw: at 12px Mario at
(48,136) "reached" (56,136) while still on the ground and
the greedy climbed diagonally up-left to (32,59)).
Honest verdict on the fix: it did NOT fix the flaw, it
moved it. With 6px the pre-key route got SLOWER (key at
chunk 88, not 31 — five backtracks before the key, Mario
stalling at the ladder top around (55,88)/(72,94) where
all actions die), and post-key Mario still dies in the
same left pit. The flaw is structural, not a radius:
waypoints are points, the greedy has no notion of
ladders or ledges, and the parasol hangs over a pit with
no floor. Both runs used the rebuilt `gb_play` on the
original ROM with the progress-1 save
(`build/nacre-test/slice6/save-prog1.sav`), pre-key
waypoints `(56,136);(56,56);(88,60)`:

- **parasol2** (post-key `(56,56);(32,56);(24,48)`,
  log `build/nacre-test/slice12/play-parasol2.log`):
  key collected chunk 88 at (83,63); post-key waypoint
  (56,56) reached; Mario reached (34,40), then (24,44)
  — one step right of the parasol box (screen x 0–15,
  y 16–31; Mario at OAM (24,44) is screen (16,28)) —
  then fell (16,60) → (6,79) → (9,88) → (12,86) where
  all actions die. Killed at that point, after chunk
  104's all-die loop at (12,86).
  Chunk-100 WRAM dump (Mario at (34,40)): parasol cells
  INTACT (`0b22/0b23/0b24/0b25`), `$c858=2`, key cells
  cleared. So Mario was adjacent to the parasol but
  never overlapped it. Chunk-050/075 dumps show the
  `$5b` trigger had fired during the pre-key thrash
  (`[$dd18]=$0a`, `[$dd3c]` 508 → 133) — before the key
  was collected, confirming again that the two events
  are independent.
- **parasol3** (post-key `(56,56);(40,48);(24,44)`,
  log `build/nacre-test/slice12/play-parasol3.log`):
  key collected chunk 88 at (83,63) (deterministic —
  identical to parasol2); post-key Mario went left along
  the bottom (4,77) → (4,88) → (13,77) → (24,88) →
  (43,77) → (45,88), then chunk 136/137 looped "ALL
  actions die -- backtracking" 29 times at (33,74)
  (every action dead=1, i.e. timer 12 seen in every
  15-frame child). Killed in that loop. No completion;
  `$c858` never hit 0; `$44` never fired live.
- The parasol needs a precision jump into its cells
  (OAM x 8–23, y 32–47) from the row-5 girder's left
  end, over a pit that kills Mario on a miss. The
  15-frame-chunk greedy cannot hit it. Next attempt
  needs a hand-written schedule or a jump-aware search,
  not another waypoint tweak.

### §6 Nacre regressions (final build, original vs rebuilt)

- `tools/run_slice5_regression.sh`: ALL REGRESSION
  CASES IDENTICAL. 600f `1cf92679…`, 900f `39ffd5ee…`,
  3600f `88515f4e…`, 12000f `92d2e185…`, s8 `92d2e185…`,
  f0 `3390d763…`, f1 `1cf92679…` (match the known hashes).
- `tools/run_slice7_cases.sh`: ALL SLICE-7 CASES
  IDENTICAL. retry 15000f `0d835d95…`, mid5000
  `2ab1bb5d…`, play-right `b3cb6c8b…`, death 3000f
  `632b2eaf…` (match the known hashes).

### §7 Verified vs inferred

- VERIFIED: the `$4827` table (13 entries, read from ROM
  bytes) and the `$627b` routine's shape including the
  `$6331` scan call and its gates (code); the `$664e` /
  `$714c` / `$643f` contents (code); the bank-8 class
  tables' run structure (pointer-table bases, code);
  the `$47fc` (119) and `$48f1` (41) tables and their
  entry→record mappings incl. `$44`→67→`$5480`,
  `$5f`→94→`$4feb` (ROM bytes + the carved tick code
  that indexes them); that bank 2 `$45a9` is the sole
  direct reader of `[$c835]` and that `[$c82f]`/
  `[$c830]` have zero direct readers (whole-ROM survey);
  the key collection at chunk 88 in both runs and the
  parasol cells intact at chunk 100 (live WRAM dumps);
  the `$5b` trigger firing before the key (live dumps).
- INFERRED (not verified): that no INDIRECT reader of
  `[$c82f]`/`[$c835]` exists elsewhere — the direct-read
  survey is exhaustive, but a `[hl]`-via-computed-pointer
  read cannot be ruled out by byte search alone; the
  positive evidence (exact consumer + table entries for
  the exact values `$44`/`$5f`/`$19`/`$03`) is what
  carries the "sound ID" conclusion, not the absence
  survey. That `$44` is "the all-pickups jingle" (the
  record shape says 2-channel sound; its musical content
  was not listened to). That the parasol needs a
  precision jump (from Mario's fall path, not from a
  successful collection). The 6px-radius assessment
  (two runs' worth of evidence, not a proof about the
  greedy in general).

## Slice 13 — DONE, byte-matching (2026-11-24)

The timer-22/23 door lead, resolved; the `$4827` table's
remaining entries carved; and the `($82,$37)` survey extended
from 4 stages to every loadable stage. The door is still not
found, but the two mechanisms this slice was asked to trace
are now nailed down, and the `$6331` scan's preconditions are
known to never co-occur in any surveyed stage. `src/` is now
36,027 lines (was 31,457).

### §1 What was carved

Bank 7, the `$4827` `[$dd18]` dispatch table's remaining
entries (generator `tools/gen_slice13.py`, new file
`src/bank7slice13.asm`, 4,568 lines; `INCLUDE`d in
`src/main.asm` after `bank7slice12.asm`):

- Entry 0 `$4841-$4ed6` + its `jp hl` table `$4ed7` (2 dw:
  `$4edb`, `$50b6`).
- Entry 1 `$4edb-$5082` (table-entry routines; the `$4ed7`
  table's targets).
- Entry 2 `$50a0-$521e` + its `jp hl` table `$521f` (5 dw:
  `$5229`, `$5409`, `$5520`, `$55bf`, `$5633`).
- Entries 3/6 `$5229-$5681` + its `jp hl` table `$5682`
  (9 dw: `$5694`, `$56c9`, `$56e5`, `$5736`, `$5761`,
  `$57bf`, `$5863`, `$5874`, `$58be`).
- Entry 4 `$5694-$58ee` + its `jp hl` table `$58ef` (3 dw:
  `$58f5`, `$5946`, `$59bd`).
- Entry 5 `$58f5-$5a19` + its `jp hl` table `$5a1a` (3 dw:
  `$5a20`, `$5c04`, `$5c54`).
- Entry 8 `$5a20-$5d49` + the `$5d4a-$5d6e` data block (36
  bytes, `db` — decodes as garbage: `$fd`/`$fc` bytes,
  self-referential `jr`) + `$5d6e-$5f32`.
- Entry 9 `$5f45-$627a` + its `jp hl` table `$5f33` (9 dw:
  `$5f45`, `$5f77`, `$5fec`, `$602d`, `$605f`, `$6088`,
  `$60ae`, `$615b`, `$616e`).
- Entry 11 `$644d-$645b` (dispatch via the `$645c` table,
  4 dw: `$6464`, `$6486`, `$64ae`, `$64af`) + entry 11/12
  routines `$6464-$64e9` (entry 12 `$64db` is an interior
  label of this span) + its `jp hl` table `$64ea` (3 dw:
  `$64f0`, `$6524`, `$654c`) + entry 12 routines
  `$64f0-$6571`.
- Shared subroutines `$66ca-$67a0` (`$66ca` called from
  `$4861`/`$57bf`; `$6732` inside, called from
  `$4fe2`/`$522c`/`$540c`) and `$695b-$6b08` (`$69ab`
  inside; `$695b` jumped/called from `$4ec0`/`$5bd2`/
  `$5dbe`/`$64ab`).

Every entry routine ends in `jp hl` through a `dw` table
immediately after it, indexed by `[$c213]*2` (or
`[$dd1d]*2` for the `$4ed7`/`$521f` tables): `ld a,
[$c213]; add a; ld c,a; ld b,$00; ld hl,$TABLE; add hl,bc;
ld a,[hl+]; ld h,[hl]; ld l,a; jp hl`. Walk from the 11
entry seeds + the 8 tables' targets: 4,693 instructions,
0 `rst $08` sites.

NOT carved (left INCBIN): `$5083-$50a0` — real code
(`ld hl,$c11b`; pointer check; `cp $08`/`$0e`; `jp $4ea8`)
with NO found entry (no `call`/`jp`/`dw` to `$5083`
anywhere in the ROM; the `$5095` block after the `jp
$4ea8` is likewise orphaned). Also still INCBIN:
`$6581-$664e`, `$67a1-$695b`, `$7001-$714c`,
`$71ba-$750a`, `$7610-$77a9`.

Template overlap (found by this slice, fixed here):
entry 11 (`$644d`) overlaps the slice-12 `$643f` record
template — the template is 20 bytes (`$643f-$6452`,
copied to `$c1ab` by `$6370-$6378`, `ld c,$14`) and
entry 11's dispatch head (`$644d-$6452`: `ld a,[$c213];
add a; ld c,a; ld b,$00`) is its last 6 bytes. So the
template is shortened to 14 bytes (`$643f-$644c`) in
`src/bank7slice12.asm` and `tools/gen_slice12.py`, and
entry 11 is emitted here as full code (`$644d-$645b`).
The 20-byte copy still reads the same 20 bytes;
byte-match arbitrates. `tools/gen_banks.py` CARVED
updated accordingly (template `(0x643F, 0x644D)`,
entry 11 `(0x644D, 0x645C)`).

### §2 Byte-match proof

Clean `make` (`rm build/game.gb` first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero
diffs vs `roms/Donkey_Kong_World_Rev1_SGB.gb`. First-try
pass. What byte-match caught: nothing this slice — but
it arbitrated the template/entry-11 overlap (the build
would have failed on overlapping sections had the
template stayed 20 bytes).

Nacre regression on the final build, original vs
rebuilt identical: slice-5 suite — 600f `1cf92679…`,
900f `39ffd5ee…`, 3600f `88515f4e…`, 12000f `92d2e185…`,
s8/f0/f1 all `[OK]`, "ALL REGRESSION CASES IDENTICAL".
Slice-7 suite — retry 15000f `0d835d95…`, mid5000
`2ab1bb5d…`, play-right `b3cb6c8b…`, death 3000f
`632b2eaf…`, all `[OK]`, "ALL SLICE-7 CASES IDENTICAL".

### §3 Timer 22/23 — FOUND (verified static + live)

Timer 22 (state 16) is set ONLY by bank-7 `$7b6e`/`$7bd1`/
`$7c34`/`$7c97`/`$7cfa` (`ld [hl],$16`, HL=`$ff90`), the
tails of the `$75ea` handler continuations: `$7b14`
(handler 2, tile `$a5`), `$7b77` (tile `$a6` — entry
mechanism UNVERIFIED, no `ld hl`/`jp`/`call` to it
anywhere in the ROM), `$7bda` (handler 4, tile `$a7`),
`$7c3d` (handler 8, tile `$eb`), `$7ca0` (handler 9,
tile `$ec`). Each saves the current timer to `[$c70b]`
first. Handler 10's HL=`$7689` is a bare `ret` (no timer
set). Fire condition: Mario touches a `$0b` map cell
whose subtype maps via `$750a` to handlers 2/4/8/9
(subtypes 16–19, 24–27, 38–41, 42–45). In 1-1 no such
cell exists. Timer-22 body `$098c` exits to state 24,
timer 0 — a stage-exit, not a queue advance.

Timer 23 (state 16) has NO literal setter anywhere in
the ROM (survey `tools/survey13_timers.py`, pattern
`3e XX e0 90`). Its only path is the `$0a2c` `[$c70b]`
restore in timer-20's body. Timer 20 is reached via the
17/18/19 animator chain (`$176b` 48-frame `[$ddb4]`
countdowns inc 18→19→20), entered via handler 11's
animator-arm (subtypes 50–53) which saves the current
timer to `[$c70b]` at `$6d2a`. For the restore to yield
23, `[$c70b]` must be 23 — but every `[$c70b]` writer
saves the current timer, and the timer can only be 23
in state 16 via this same restore (circular) or in
state 20 via `$47ad`'s inc. Remaining UNVERIFIED
candidate: a bank-7 handler firing while state==20 and
timer==23, saving 23 to `[$c70b]`; whether the `$42xx`
per-frame routines (which reach the handlers) run
during state-20 timer 23 is unverified.

`[$c70b]` writer inventory, complete
(`tools/survey13_c70b.py`): 11 sites — bank 0
`$08bd`/`$08c6` (save 3/5/7/9 in the `$083e`
joypad-watch steps); bank 7 `$405a`/`$66b5`/`$6d2a`
(save current timer, set timer `$11`=17); bank 7
`$7b6e`/`$7bd1`/`$7c34`/`$7c97`/`$7cfa` (save current
timer, set timer `$16`=22); bank 31 `$55b6`. Readers:
bank 0 `$0a2c` (timer-20 restore), bank 1
`$4e0f`/`$5bce`, bank 7 `$6fc4`, bank 8 `$75df`. No
`ld hl,$c70b` sites exist. No `ld [$ff90],a` sites
exist.

Live watch (`tools/gb_watch`, progress-1 save,
5000 frames, original ROM): `ff90=16` (timer 22): 0
hits. `ff90=17` (timer 23): 0 hits. `c70b` (any
change): 0 hits. With a Start press at 2600–2612
(6000f run): `[$c70b]` 00→09 at frame 2600, written by
bank-0 `$08c6` (state 16 timer 9, `$083e` path,
AdvanceState 16→17) — confirms the pause path saves
only 3/5/7/9. Watch tool sanity-checked working (c85c
watch found writes, frame 1088). All-traces survey:
state-16 timers seen across all `build/nacre-test/`
traces are only {0,1,2,3,4,5,6,7,8,9,10,12,27,28,29,
30,31,32} — never 13–26 (except 27), never 33–45.

### §4 C==4 entry condition — FOUND (verified static)

Queue survey (`tools/survey13_queue.py`, bank-12 table
at `$4f97`, 331 (C,B) pairs): C histogram {1:101,
2:101, 3:68, 4:35, 20:26}. **Every one of the 35 C==4
entries is immediately preceded by a (1,B) load entry.**
C==4 indices: 3, 6, 9, 12, 25, 38, 51, 64, 77, 90, 103,
116, 129, 142, 155, 168, 181, 194, 207, 220, 233, 246,
259, 272, 285, 298, 302, 305, 308, 311, 315, 318, 321,
324, 329. Preceding (1,B) B values: 0,1,2,3,7,11,15,19,
23,27,31,35,39,43,47,51,55,59,63,67,71,75,79,83,87,91,
92,93,94,95,96,97,98,99,100.

Timer-23/26 bodies `$0997`/`$09d5`: advance qidx,
fetch, C==4 → timer 33 (`$09b4`/`$09eb`); else fall to
timer-24 body `$09b9` (waits `[$ff95]`==`$5a` → timer
42). After real 1-1 completion qidx 16→17 = (2,1),
C==2 → the clear chain is **23→24→42→43→44→45→0
WITHOUT timer 33**. The timer-33 detour fires only
after completing one of the 35 stages whose (1,B) entry
is followed by (4,x). Timer 40 (`$0b21`): timer=`$2a` +
advance. Timer 42 (`$0b45`): world/stage 9,9 → timer 0;
else Select-path + timer `$2b` (43).

Queue/stage indexing (clarified): (1,B) B is the
stage-DATA index via the bank-5 pointer table (`$24e7`
reads `$4000+[$c829]*2`; `$0d1a` stores B to `[$c829]`
then calls `$24e7`). (2,B) B indexes the bank-$18
(bank 24) display table `$4934` (world/stage). In
observed flows data index = display B + 4 (e.g. (2,0)@14
displays 1-1 → (1,4)@16 loads data 4 = 1-1's data).

### §5 `($82,$37)` survey — every loadable stage

Progress survey (`tools/survey13_run_all.sh`,
`tools/survey13_progmaps.py`): progress 0–24 → data
0,4,…,92, 3 dumps each (frames 2800–3600). Found
`($82,$37)` cells in data 44 (world 5-1, 100 cells,
rows 2–5/7–9/11–14/15–17) and data 80 (world 8-5, 22
cells). The `$5b` trigger cell (second-pair `$0b`,
subtype `$5b`) exists in exactly one of those 24
stages: data 4 (world 1-1, rows 8–9 col 6). No surveyed
stage has both.

Full survey (`tools/survey13_run_full.sh`,
`tools/survey13_patch_rom.py`, `tools/survey13_fullmaps.py`):
TEST ROMs with a patched `$5e99` progress→queue table
(bank 1, 25 16-bit entries) so each progress value
points at the queue entry leading to a chosen (1,B)
stage; 77 remaining stages B=0..100 (B=101..105 have
no (1,B) load entry and are never loaded). **Complete:
all 101 loadable stages surveyed** (24 progress + 77
full; every stage produced a valid loaded map). One
hitch: batch 3 (B99/B100) first failed — the patch
tool requires exactly 25 queue indices and the runner
passed 2; fixed by padding the list to 25 with the
last Q, re-ran, both loaded fine.

`($82,$37)` cells (first pair, verified by direct
hexdump `82 37 00 00`): data 44 (world 5-1, 100 cells),
data 45 (32), data 49 (world 5-6, 10), data 50 (16),
data 80 (world 8-5, 22), data 82 (21). **Six stages
total.** `$5b` trigger cells (second-pair `$0b`,
subtype `$5b`): data 4 (1-1, 2 cells), data 6 (1),
data 15 (3), data 26 (2), data 41 (3). **Five stages
total.** **No stage has both.** Subtype `$37` maps to
class 2 (same class record `04 03 04 04` as subtypes
`$02`/`$04`/`$22`/`$4a`) via the `$4aed` table — it is
a class-2 terrain variant, not a distinct class.

`[$dd18]` values written by the carved `$4827`-entry
code are 0–9, `$0e`, `$16` — never `$0a`. The only
`$0a` setter in the ROM is the `$6bf2` tail (handler 0,
the `$5b` trigger). So `[$dd18]==$0a` happens only via
the `$5b` trigger cell. Combined with the survey: the
`$6331` scan needs a stage with BOTH a `$5b` trigger
and a `($82,$37)` cell near Mario, and no surveyed
stage has both — the scan is inert in every surveyed
stage.

### §6 What byte-match caught

Nothing this slice (first-try pass). The template /
entry-11 overlap (§1) was found by reading, not by the
build — had the template stayed 20 bytes, the build
would have failed on overlapping sections.

### §7 Verified vs inferred

VERIFIED: timer-22 setters (bank-7 `$7b6e`/`$7bd1`/
`$7c34`/`$7c97`/`$7cfa`) and their handler/tile mapping;
timer-23 has no literal setter; the `[$c70b]` writer
inventory (11 sites); the C==4-preceded-by-(1,B) rule
(all 35); the 23→24→42→43→44→45→0 clear chain after
1-1 (no timer 33); the `($82,$37)` and `$5b` cell
locations in every stage surveyed live (direct hexdump
+ map renders); subtype `$37` is class 2; the `$4827`
entries' code and tables (byte-match); the template /
entry-11 overlap and its fix.
INFERRED: the timer-23-via-`[$c70b]`-restore path needs
a bank-7 handler firing in state-20 timer 23 — whether
the `$42xx` routines run then is unverified; the
`$5083` code's entry mechanism (orphaned); what
subtype `$37` terrain IS visually (class 2, same as
ordinary ground — its distinct role is unknown).
## Slice 14 — DONE, byte-matching (2026-11-24)

The stage-clear trigger, attacked on its three remaining
leads — and all three closed WITHOUT finding it, but each
closure is now nailed down with live proof, and the survey
that follows them points at a concrete new lead. The door
is still not found. `src/` is now 36,165 lines (was 36,027).

### §1 What was carved

Generator `tools/gen_slice14.py` (new), two new files
`src/bank0slice14.asm` and `src/bank7slice14.asm`,
`INCLUDE`d in `src/main.asm` (bank-0 file after
`bank0slice7.asm`, bank-7 file after `bank7slice13.asm`).
`tools/gen_banks.py` CARVED gains bank 7 `(0x4000,
0x4016)` and `(0x5083, 0x50A0)`; `src/banks.asm`
regenerated. The raw bank-0 A2 INCBIN in `src/main.asm`
is split around the carve: `$0df4-$0f08` (A2a) and
`$0f74-$0fc0` (A2b).

- Bank 7 `$4000-$4015`: the SECOND entry into the `$4016`
  per-frame system (see §3). `call $67a1` (still uncarved),
  then `[$ff91]` bit 7 → `$41c9`; `[$ff8a]` bits 4-5 →
  `$41c9`; else `jp $4085` (inside the carved `$4016`
  span). `$4013` (`jp $41c9`) is dead code: unreachable
  fall-through after the unconditional `jp $4085` at
  `$4010`.
- Bank 7 `$5083-$509f`: the orphaned code slice 13 left
  INCBIN, now carved (see §4). `$5083`: `ld hl,$c11b`;
  deref rec0's map pointer; `cp $08` / `cp $0e`, `ret z`
  either way; `and $c0` (result discarded — the `jp
  $4ea8` is unconditional); `jp $4ea8` (interaction-end
  cleanup). `$5095`: `ld bc,$0080; add hl,bc; ld a,[hl];
  cp $08; ret z; jp $4ea8`.
- Bank 0 `$0f09-$0f14`: the `$4016`-system trampoline.
  `ld a,$07; rst $10; call $4000` (bank 7's `$4000`
  above); `ld a,$10; rst $10; jp $4000` (bank 16's
  `$4000`, the state-24 dispatch — state 24 always runs
  bank 1 here, because its sole writer selects bank 1
  first).
- Bank 0 `$0f15-$0f38`: the SRAM stage-record writer,
  called ONLY from the timer-23/26 bodies (`$09a6` /
  `$09de`). It counts the C==2 / C==`$15` queue entries
  before qidx (via `$0f39`), enables SRAM (`call $1ec0`),
  writes 4 nibble-split bytes from `[$c711]` to SRAM
  `$a190+4*count`, disables SRAM (`jp $1ec9`). This is
  what the game does WHEN a stage clears — but its
  callers (timer 23/26) are themselves unreachable via
  known paths (see §3).
- Bank 0 `$0f39-$0f60`: the queue counter — scans the
  bank-12 `$4f97` table from qidx, counts C==2 / C==`$15`
  entries, returns count-1 in A. Called only from `$0f15`.
  (The `$29c0` forward and `$29ee` backward scans do the
  same count over the same table; all three have no other
  callers — `$29c0`/`$29ee` have NO caller at all, see §5.)
- Bank 0 `$0f61-$0f73`: peek-next-queue-entry — qidx++,
  `call` bank-1 `$4cbe`, qidx--. Called only from `$4783`
  (state-20 timer 6/20 body `$476c`, when `[$c207]==$50`).

### §2 Byte-match proof

Clean `make` (rm `build/game.gb` first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero
diffs vs `roms/Donkey_Kong_World_Rev1_SGB.gb`.

What byte-match caught (my own error): the split A2a
INCBIN length was written `$15` instead of `$115`
(`$0f09-$0df4=$115`). The build zero-filled the gap
`$0e09-$0f08`: 252 differing bytes, including the header
global checksum at `$14e-$14f` (a consequence, not a
cause — rgbfix recomputes it from the content). Fixed the
length, rebuilt, SHA-1 matches.

### §3 The timer-23 verdict: unreachable in both states (VERIFIED)

Static trace (all byte searches whole-ROM, redone this
slice):

- State-16 timer 23's ONLY entry is the `$0a2c` `[$c70b]`
  restore in timer-20's body. The restore can only yield
  a value some writer saved, and every writer saves the
  CURRENT timer: bank 0 `$08bd`/`$08c6` (save 3/5/7/9 in
  the `$083e` joypad-watch steps), bank 7 `$405a`/`$66b5`/
  `$6d2a` (save current, set timer 17 — `$66b5` sets 16),
  bank 7 `$7b6e`/`$7bd1`/`$7c34`/`$7c97`/`$7cfa` (save
  current, set timer 22), bank 31 `$55b6` (save current,
  set timer 16). So the restore can yield only
  {3–10, 18, 19}. 23 is not among them. No literal
  timer-23 setter exists anywhere in the ROM (whole-ROM
  `3e XX e0 90` survey redone: values set are 1, 2, 3, 4,
  6, 12, 13, 15, 16, 18, 19, 20, 22, 25, 26, 27, 29, 30,
  32, 33, 36, 42, 43).
- Timer 20 IS reachable — via state 24: entry 4 (`$4142`)
  flows to `$4197`, which sets state 16, timer 20 (`$419d`
  literal 20, the ONLY literal-20 setter). But no state-24
  entry writes `[$c70b]`, and timer-20's body doesn't write
  it before the `$0a2c` restore — so the restore yields
  exactly what the timer-22 tail saved (a gameplay timer
  3–10 or 18/19), never 23.
- State-20 timer 23 is the SAME body as timer 8 (`$47d5`):
  reached only by IncStateTimer from 22, which needs the
  19–26 chain, which needs `[$c70f]` bit 0 set at the
  state-20 step-0 tail (`$2829`: bit 0 → timer 19, bit 2 →
  timer 15). Bit 0 is set ONLY by bank-23 `$7337` (attract
  start) — and no `[$c70b]` writer can run during state 20
  at all: all bank-7 writers are downstream of `$4016`,
  entered ONLY from state-16 timers 3–10 (via `$0f09` /
  `$0868`, the ONLY `call $0f09` / `call $6f62` sites in
  the ROM) and 18/19 (via `$6f62`); no state-20 timer body
  calls `$0868` / `$0862` / `$0f09` / `$0f15` / `$6f62`
  (grep of `src/bank1.asm` + `src/bank0slice3.asm`, zero
  hits); bank 31's writer sits in an unentered routine
  (no `call`/`jp`/`ld hl` to `$5590` anywhere; bank 31 is
  selected at exactly ONE site, `$2aa7`, gated on
  `[$ddad]!=0`, calling only `$7e44`).
- The `$7337` bit-0 set is wiped before any state-20 visit
  can read it — pinned live, see §6: the attract demo
  always ends via state-30 timer 2 (`$06a5`, 5-frame
  `$defb` countdown) → `jp $01fb` soft reset →
  `ClearRAMAndInit` memsets WRAM `$c000-$def6`, which
  covers `[$c70f]`.

Live proof (`tools/gb_headless` traces +
`tools/gb_watch` write watchpoints, original ROM):

- Play 12000f (progress-1 save, start + 11 A-presses +
  hold-right): state-16 timers {0–10, 12, 27–32},
  state-20 timers {0, 1, 15, 16, 17, 18}. Timer 23:
  zero hits in any state. `[$c70b]==00` in all 1453 trace
  lines. fb
  `f8818e6cad26d507857d0a4499306a37a0320af661c3859f2ada7c3c6c68ef4f`.
- Idle/attract 30000f: states {0, 2, 16, 17, 18, 20, 30},
  state-20 timers {0, 1, 15, 16, 17, 18} only — never 19+.
  No state 24. No timer 23. `[$c70b]==00` in all 6464
  trace lines. fb
  `0b8b12b6b3787d088c3f2458b325ae96d4cd7c488a48c0e6638c14ba15279d80`
  (matches the slice-7 idle-30000f hash).
- `gb_watch` (`tools/gb_watch.c`, new this slice: two-pass
  write watchpoint; pass 1 frame-steps, pass 2 cycle-steps
  the hit frame and logs the writing instruction + 128-entry
  ring): `ff90=17` / `c70b=17` → 0 hits on BOTH flows;
  `c70b` any-change on idle → 0 hits (no `[$c70b]` writer
  fires at all in 30000 attract frames). `c70f` watch on
  idle 8000f: 2 hits — 00→01 at frame 1477 by pc `$733a`
  bank 23 (the `$7337` set, state 30 timer 0, CONFIRMED),
  01→00 at frame 5831 by pc `$1057` bank 23 (the
  `ClearRAMAndInit` memset, BC=`$17e8` = `$1ef7-$70f`
  exactly, state 30 timer 2 — the soft-reset wipe,
  CONFIRMED).
- The first state-20 visit after attract start (frame
  7282) is a demo-stage visit (B=200, `[$c861]`=1): timer
  stays 1 — BOTH `[$c70f]` bits clear at the tail (bit 2
  never set because the demo branch skips `$2758`).

Corollary (open, NOT solved): the clear chain's entries
also look unreachable via known paths — timer 33 is set
only in the timer-23/26 bodies, timer 42 only in the
timer-24/26/40 bodies. The 33→40→42→43→44→45→0 chain's
ENTRY is now the open question, not timer 23. Do not
present the clear chain as understood.

Residual caveat (honest limit): computed jumps (`jp hl`
from tables in uncarved banks) cannot be exhaustively
excluded by byte search alone — but no evidence supports
one: all known `jp hl` tables are carved and none contains
`$4016` / `$41c9` / `$6f62` / `$480e`.

### §4 The `$5083` verdict: orphaned dead code, NOT the trigger (VERIFIED)

Re-searched whole ROM for `83 50` / `95 50` (`dw` /
`call` / `jp` `$5083` / `$5095`), `21 83 50`, `21 95 50`,
`cd/c3 83 50`, `cd/c3 95 50`: the only hits are bank-11
`$5022` / `$502c`, data bytes inside bank 11's
sprite/animation data pointing at bank-11 `$5083` /
`$5095` (a different address space — coincidence, not an
entry). `$5083` is preceded by `jp $4ea8` at `$5080`, so
no fall-through entry either; `$5095` is unreachable even
from `$5083` (the `$5092 jp $4ea8` is unconditional). It
never writes hStateTimer, `[$c70b]`, or the queue — it
only returns or jumps to the `$4ea8` interaction-end
cleanup. Carved here so it stops being INCBIN.

### §5 Item-3 survey: outside the `$4827`/`$75ea` system

- `$c560` has ZERO direct-access sites in the ROM (no `ld
  a,[$c560]` / `ld [$c560],a` / `ld hl,$c560`) — it is
  reached via computed pointers only (the `$c117`-record
  system). The slice-10 "key pickup writes `$c560`"
  conflation is already corrected (slice 11 §5); the
  key-collected flag's address is a computed-pointer
  target, not a directly-addressed byte.
- `[$dd18]` is read at 66 sites and written at 52 sites
  whole-ROM. Outside bank 7: bank 8 reads `$41aa` /
  `$644a` / `$65fc` / `$68b8`, write `$6f26`; bank 9 reads
  `$657c` / `$6f6a`; bank 10 reads `$4f7d` / `$757f`,
  writes `$4ff2` / `$5021` / `$5ca8` / `$759a` / `$7825`;
  bank 16 reads in the uncarved gaps (`$40b0` / `$460f` /
  `$4669` / `$4bef` / `$4c85` / `$4cbc` / `$4ce1` /
  `$4d2e`); bank 31 reads `$437b` / `$4590` / `$4723` /
  `$4766` / `$4a40` / `$561b` / `$656d` / `$7662` /
  `$7d88`, writes `$4b56` / `$76df` / `$770e`.
- Bank selects (`ld a,$XX; rst $10`): bank 8: 18 sites,
  all bank 0 (state-16 timer bodies + the `$2a45-$2b2a`
  cluster); bank 9: 3 (`$0862`, `$0a52`, `$2641`); bank
  10: 7 (`$22b6`, `$2342`, `$2a53`, `$2b1e`, `$2b36`,
  `$3312`, `$33fe`); bank 31: 1 (`$2aa7`).
- The lead: the `$2a0a` per-frame routine (called from
  `$086e` / `$096e`, inside the state-16 gameplay tick)
  copies `$c200` records to `$c0f7` and dispatches —
  `$2a45` → bank 8 `$5efe` table → bank 10 `$7730`;
  `$2a9c` → bank 31 `$7e44` → bank 8 `$7526`. So banks
  8/10/31 run EVERY frame during 1-1 gameplay. Handler 17
  (key pickup, `$7dbe` chain) creates a `$c200` record
  (type `$02`, byte from `[$d9a2]+4`, bit 2 set) then `ld
  a,$02; jp $0e29` (score) — the key pickup's output feeds
  exactly this per-frame dispatch. The door mechanism, if
  outside `$4827`/`$75ea`, most plausibly lives in bank 8
  `$7526` / bank 10 `$7730` and their `[$dd18]` state
  machines. Frame-end bank samples support it: bank 8 in
  142/1453 play frames and 1594/6464 idle frames; bank 10
  in 18 idle frames; bank 31 in 20 idle frames.
- Orphaned like `$5083`: the `$29c0` forward and `$29ee`
  backward queue scans (C==2/`$15`, same `$4f97` table as
  `$0f39`) have NO caller anywhere in the ROM (no `call` /
  `jp` / `ld hl` / `dw`); the `$29b6` block's head decodes
  as garbage, suggesting the real entry is `$29c0` — still
  uncalled. The `$29dc` retreat (clears `[$c70f]`) is
  therefore also unreachable; it is NOT what clears bit 0
  in attract (the soft-reset memset is, §3).

### §6 Nacre results

- `tools/run_slice5_regression.sh`: ALL REGRESSION CASES
  IDENTICAL (600/900/3600/12000/s8/f0/f1, framebuffer hashes
  match original vs rebuilt).
- `tools/run_slice7_cases.sh`: ALL SLICE-7 CASES IDENTICAL
  (retry 15000f, mid5000 5000f, play-right 5000f, death
  3000f).
- Slice-14 live traces (original ROM, `gb_headless`,
  `GB_WATCH=c70b,c82b,c860,c861`): play-12000f and
  idle-30000f, hashes in §3; traces in
  `build/nacre-test/slice14/trace-play-orig.txt` and
  `trace-idle-orig.txt`. `gb_watch` results in §3.
  Traces and framebuffer dumps are in
  `build/nacre-test/slice14/` (not in the tree state:
  `git status` shows only the slice files + `PROGRESS.md`
  changes).

### §7 Verified vs inferred

VERIFIED: timer 23 unreachable in both states (static
trace + 42000 live frames + write watchpoints); the
`$7337` set / soft-reset wipe mechanism (both writes
pinned to instruction + frame); `$5083` orphaned (whole-ROM
re-search); `$0f15` SRAM writer + its callers; `$4016`
system entries (only `$0f09` / `$6f62`); bank-31 writer
unentered; byte-match + both regression suites.
INFERRED (not proven): that the door mechanism lives in
bank 8 `$7526` / bank 10 `$7730` — it is the best
remaining lead (per-frame execution + `[$dd18]` sites +
the handler-17 `$c200`-record link), but the door-tile
handler and the clear-chain entry are both still
unidentified. The `$0f15` record's role ("what the game
does WHEN a stage clears") is read from its code and
callers, not observed live — no run has reached timer
23/26.

## Slice 15 — DONE, byte-matching (2026-11-24)

The `$2a0a` per-frame dispatch, carved whole — decimal bank 10
`$7730` and its tables, bank 8 `$7526` / `$6443` / `$65fc` /
`$68b8` / `$6f26`, and the bank-0 `$2b48` dispatch table itself,
which was mis-decoded as code. The timer-13 mechanism is now
fully mapped — and closed as the 1-1 clear-chain entry: two
`$2b48` handlers set it, both gated on a record flag no 1-1
record carries, and its body resolves to timer 1 or 12, never
to 23/26/33/42. The door is still not found. `src/` is now
38,720 lines (was 36,165).

### §1 What was carved

Generator `tools/gen_slice15.py` (new), two new files
`src/bank0a.asm` (decimal bank 10 — NOT `src/bank10.asm`,
which is hex bank `$10` = decimal 16, the death-path bank)
and `src/bank8slice15.asm`, `INCLUDE`d in `src/main.asm`
(bank-8 file after `bank8.asm`, bank-10 file after
`bank10.asm`). `tools/gen_banks.py` CARVED gains the bank-8
ranges below plus a new key 10; `src/banks.asm`
regenerated. The bank-0 `$2b48` table is spliced into
`src/bank0slice3.asm` in place (237 garbage lines replaced
by 96 table lines; the generator's splice is idempotent).

- Decimal bank 10 `$4ff2-$4ffe`, `$5021-$5084`,
  `$5c4f-$5cf7` (the three remaining `[$dd18]` spans; the
  last holds the `$5c97`/`$5c4f` timer-13 routine and its
  `$5cd8` entry-53 handler, plus the `$5cf8` 8-entry dw
  table — entries 0-3/6-7 point into uncarved
  `$5d08-$5e97`, entries 4-5 are `$0000` dead slots),
  `$759a-$75af` (the `[$dd18]` writer tail),
  `$7730-$7814` (the record pre-dispatch, incl. the
  `$77d4` / `$77f2` continuations), `$7815` (lone 1-byte
  `ret`), `$7816-$787c` (the spawn routine, reached via
  the bank-0 `$2b30` trampoline), `$787d-$789e` (the two
  overlapping 20-byte spawn templates, one section —
  see §5), `$7c57-$7caf` (the `$c0c7`-list insert/remove),
  `$7e50-$7ead` (the 94-byte `$7730` transition table),
  `$7eae-$7f43` (25 6-byte transition records).
- Bank 8 `$5e37-$5efd` (the record linker, via the bank-0
  `$2b0e` trampoline) + `$5efe-$5f5b` (its 94-byte B table),
  `$5f5c-$5f6a`, `$609d-$60e8`, `$6110-$611e`,
  `$6274-$6282`, `$63b5-$63ef`, `$6443-$6466` +
  `$6467-$646c` (6-entry dw table) + `$6473-$6667` (incl.
  `$65fc`) + `$6668` (1-byte `ret`, the entry-8 handler),
  `$67bd-$67cb`, `$68b8-$68ee` (proximity trigger),
  `$69af-$69bd`, `$6a25-$6a33`, `$6abb-$6ac9`,
  `$6d8a-$6da9` + `$6daa-$6db5` (6-entry dw table) +
  `$6db6-$6f64` (the `$6daa` routines, the `$6ecd` /
  `$6f26` timer-13 setter, and the `$6f56` handler) +
  `$6f65-$6f7a` (11-entry dw table) + `$6f7b-$7291`,
  `$7310-$74f3` (bare `ret` + the `$7311` sprite-frame
  routine), `$7526-$7587` (the `$2a0a` per-frame tail) +
  `$77da-$7819` (32-entry dw table), `$7602-$7629` +
  `$7685-$76b5` (shared subroutines, `jp`'d to from
  `$5ff6`/`$651f`/`$72d1` and `$7600`), `$76e3-$7740`
  (94-byte table) + `$7741-$7746` (3-entry dw table) +
  `$7747-$77d9` (sprite triple tables).
- Bank 0 `$2b48-$2c61`: the `$2a0a` dispatch table, 94
  entries x 3 bytes (bank, lo, hi), carved as data. Entry
  checks (read from the ROM, not the old decode): 0 →
  bank `$0a` `$47a3`, 1 → bank 8 `$5f5c`, 3 → bank 8
  `$7310`, 6 → bank 8 `$6443`, 34 → bank 8 `$6d8a`, 37 →
  bank 8 `$6f56`, 53 → bank `$0a` `$5cd8`, 63 → bank `$0a`
  `$705f`, 64 → bank `$0a` `$4000`, 65 → bank `$0a`
  `$41c2`, 66/67 → bank `$0a` `$33e3`/`$33ef` (targets in
  ROM0 address space), 93 → bank `$1f` `$7bf6`. Banks
  used: `$08`, `$09`, `$0a`, `$1f`.

### §2 The `$2a0a` dispatch, statically

`$2a0a` (bank 0, already curated) iterates `[$dd7b]`
0–7 over the `$c0c7` list (8 groups x 6 bytes); per
record it copies 32 bytes from `$c200+idx*32` to `$c0f7`
and dispatches on `[$c103]` (copied record byte 12)
bit 3: clear → bank `$0a`, `B=$5efe[[$c105]]`,
`jp $7730`; set → the `$2b48` table (`A=[$c105]`,
`HL=$2b48+A*3`, bank=`[HL]`, `rst $10`, `jp hl`,
return `$2a72`). On return, if `[$c0f7]!=0` and
`[$c103]` bit 5 is clear → bank 8 `jp $7311`; then the
record is copied back. Loop end `$2a99`: `[$dd7b]++ &
7`; if `[$ddad]!=0` call bank-31 `$7e44`; then bank 8
`jp $7526` (per-frame tail). Called from `$086e`/`$096e`
(state-16 timers 3/5/7/9 and timer 13).

- `$7730` (bank `$0a`) is a pre-dispatch, not a handler:
  guards (`[$ff93]` bit 5, B bit 1, the `$5e37` linker
  call, `[$dd9e]==0`, linked record byte 14 `==$3f` and
  byte 19 `$02`/`$05`, `[$dd9f]` bit 7), then the table
  rewrite: `[$c105]` indexes `$7e50` → V;
  `HL=$7eae+V*6`; byte0→`[$c0f9]` unless `$ff`;
  byte1→`[$c116]` unless `$ff`; `[$c102]=0`;
  `[$c104]`=old `[$c105]`; `[$c105]`=byte2;
  `[$c10a]`=byte3; `jp hl` (almost always `$77d4`,
  except record 11 → `$77f2`, the record-KILL path:
  zeroes `$c0fc-$c101`, `[$dd9e]=0`, clears bit 4 /
  sets bit 3 of `[$c103]`, removes the record from the
  `$c0c7` list via `$7c88`, re-inserts via `$7c57`).
  ALL `$7730` exits jump to `$2a59` — the `$2b48`
  dispatch — so `$7730` can rewrite `[$c105]` (the
  `$2b48` index) before the real handler runs.
- `$5e37` (bank 8, the linker) scans `$c220` records
  1–32 for a link candidate: byte 0 nonzero, byte 12
  bit 3 clear, byte 14 `!=$21` (with a `$3f` + byte-20
  special case), a ROM-bit test at `$5e00+(byte14-2)`,
  and proximity windows vs `[$c0fa]`/`[$c0fe]`. On
  match it sets bit 4 of the found record's byte 12 and
  stores the link in `[$dd9e]`/`[$dd9f]`. This is the
  ONLY `[$dd9e]` setter besides the level-load `$ff`
  fill (see §4).
- `$7816` (bank `$0a`, the spawn routine, via the bank-0
  `$2b30` trampoline from bank-7 `$43d9`) is how a spawn
  becomes a `$2a0a`-dispatched `$c200` record: it clears
  `[$dd18]`/`[$dd1d]` (the `$7825` `[$dd18]` site),
  copies a 20-byte template (`$787d` or `$788b`, by
  `[$ff94]` bit 5) to `$c1ab`, positions the record at
  Mario Y−16 / X+4, and inserts into the `$c0c7` list
  via `$7c57`.
- `$7526` (bank 8, the `$2a0a` tail) loops over `$c22c`
  records (stride 32): byte 0 bit 2 set → byte 2 (or
  byte 1 `& $7f` if byte 2==`$3f`), `*2` → the `$77da`
  dw table → a nested table indexed by the byte at
  DE+`$11` `& $0f` — a sprite/animation-data processor.
- `$7311` (bank 8) is the post-handler sprite-frame
  routine: scales `[$c0fc]`/`[$c0fd]`/`[$c100]`/`[$c101]`
  by `[$c103]&3`, indexes `$76e3` by `[$c105]` (or
  `[$c104]&$7f` when `[$c105]==$3f`) → `$7741` dw table
  → sprite data, then stamps into the WRAM map (base
  `$c86f`), with a `[$c105]==$3b` special case; ends
  `jp $2a85` (back to the `$2a0a` copy-back loop).

### §3 Timer 13: mechanism mapped, unreachable in 1-1 (VERIFIED)

Static (whole-ROM byte surveys) + live (see §4):

- Timer 13 has exactly TWO `$2b48`-dispatch setters,
  both gated on `[$c109]` (copied record byte 18) bit 3:
  entry 34 → bank 8 `$6d8a` (`bit 3,[$c109]`; set →
  `[$c10a]=5`, `jp $6ecd`) and entry 53 → bank `$0a`
  `$5cd8` (`bit 3,[$c109]`; set → `[$c10a]=7`,
  `jp $5c4f`). Both tails are the same shape:
  position a sprite record (`[$c201]=$46`), then
  `[$c213]=5`, `[$dd1a]=0`, `[$dd18]=$07` (the `$6f26` /
  `$5ca8` `[$dd18]` sites), `[$dd21]=$ff`,
  `[$ff91]|=$c0`, `[$dd2b]=$09`, `[$dd2c]=$0b`,
  timer=13, `res 2,[$c103]`, `[$c102]=0`, `[$c0f9]=$0a`,
  `[$c116]=1`, `ret`. The ONLY `jp $6ecd` in the ROM is
  bank 8 `$6d98` (inside `$6d8a`).
- `[$c109]` bit 3 is a per-record "armed" flag. Its
  setters are tiny routines: bank `$0a` `$4add` /
  `$4d58` (`set 3,[hl]; ret`) and bank 31 `$6ca9` — all
  inside the uncarved bank-`$0a` handler set / bank 31.
  What arms a record (which handler, on what event) is
  the next carve's question; the flag is TESTED by 17
  handlers across banks 8/`$0a`/31.
- Timer-13's body `$0968` (state-16 table entry 13)
  contains no timer write: it runs `$2a0a`, bank-16
  `$5a11`, bank-8 `$4000`, bank-16 `$4e89`, then `$0f95`.
  `$5a11` was walked this slice (909 instrs, NOT carved
  — it is bank 16's Mario animation/state machine, with
  seven `rst $08` tables dispatching on `[$c213]` /
  `[$c21a]`): its routines set ONLY timers 1 and 12.
  `$4e89` (26 instrs, walked) is a position nudge
  (`[$c207] += 2` or `$fe` by `[$c133]`/`[$c141]` bit
  tests) with no timer write. So timer 13 resolves to
  timer 1 (resume gameplay) or 12 (death) — never to
  23/26/33/42. Even in a stage WITH a 34/53 record,
  timer 13 would not start the clear chain.
- The other literal timer-13 setters (whole-ROM
  `3e 0d e0 90` survey, 8 sites): bank 1 `$51fc` (a +4
  clamp inside the `$51ca` save/cutscene routine — NOT
  state-16 gameplay; timer 9 + 4 = 13 is the only way
  that clamp yields 13, and it runs in the bank-1
  `$51xx` region, not the gameplay path), bank 16
  `$555b` / `$564d` (real code, `[$c213]=3` then
  timer=13; entries unidentified — no absolute
  call/jp references to either), bank 16 `$59ab` and
  bank 31 `$7845` (sites confirmed as bytes only;
  context not fully decoded), bank 31 `$4b6e` (the same
  `$09`/`$0b`/`$0d` routine shape; bank 31 is selected
  at exactly ONE site, `$2aa7`, gated on `[$ddad]!=0`).
  None of these is a 1-1 door lead.
- No `[$c105]`=34 or 53 record exists in 1-1: live
  byte-14 values over frames 2900–3050 are
  {0,1,2,3,6,7,32,45,72} (see §4). VERDICT: timer 13 is
  NOT the clear-chain entry for 1-1 — same verdict
  class as timer 23, but now with the entry mechanism
  identified. A `[$c105]`=34/53 record type may exist in
  other stages' record sets; that is where the mechanism
  could fire.

### §4 Live findings (1-1 key-pickup run, original ROM)

Replay: the first 32 windows of play12's SCHEDULE
(chunks 0–31) + seed
`start:620:632,a:1000:1012,a:2000:2012`, via
`gb_wramdump` (30 dumps, frames 2900–3050, every 5) in
`build/nacre-test/slice15/play/`. The replay drifted
vs play12 (slice-8 drift, both directions): in play12
the key was collected at chunk 31 (~frame 2964); here
the `$5b` trigger fired at frame 2878 and the key was
collected ~frame 2965–2970.

- Key collection: the key cells (`0b4a/0b4b/0b4c/0b4d`,
  map rows 6–7, cols 10–11) intact through frame 2965,
  cleared to `0001` by frame 2970; `[$c858]` 3→2; Mario
  at (85,67). The key was collected with `[$dd18]==0`
  (cleared ~frame 2904, before the key) — the key does
  NOT need `[$dd18]==$0a`.
- The `$5b` trigger firing is PINNED live (`gb_watch`,
  `dd18=0a`, 2900 frames): single hit frame 2878, written
  by bank-7 `$6bfd` (the `$6bf2` tail, `ld [$dd18],a`
  with A=`$0a`), ring
  `$4888→$4022→$6b0a→$6b55` (handler 0) → `$6bf2`.
  State 16 timer 7.
- `[$dd18]` timeline in the replay: `$0a` at frame 2900
  (set frame 2878), `$00` at 2905–2985, `$0a` again at
  2990–3045 (still `$0a` at 3045, `[$dd3c]` frozen at
  `$3402` from frame 3035 — Mario idle after the press
  spec ends at frame 3009; the `$627b` countdown stalls
  when `[$dd1a]>=3`). The 2904 clear is a bank-7 `$42xx`
  routine setting `[$dd18]=0` as Mario's state changed
  (Mario at (59,89), far from the key) — NOT the key.
  The 2990 `$0a` re-set is UNEXPLAINED (the `$5b` cells
  are cleared by then; parasol/top-right map to
  handlers 7/6, not 0; Mario at (73,63) is far from all
  `$0b` cells). Open loose end, not the door.
- `$5e37` link formation is PINNED live (`gb_watch`,
  `dd9e=1e`, 3050 frames): single hit frame 3022,
  written by bank-8 `$5ee8` (C=`$1e`=30, i.e. rec30
  `$c5c0`, byte14=`$48`), ring showing the `$5e37` scan
  loop, the proximity checks, then the link path `$5ec8`
  (set bit 4 of the found record's byte 12,
  `[$dd9f]`/`[$dd9e]`=D/C). State 16 timer 7. The link
  cleared by frame 3028 (`$dd9e` `$1e`→00 — by `$5ebd`
  on a later no-link pass, or `$77f2`; not pinned
  which).
- `$c200` record byte-14 values seen live in 1-1:
  rec0 (Mario) `$00`/`$01`/`$02`/`$03`/`$06`, rec1
  `$20`, rec26 `$07`, rec28/31 `$2d`, rec30 `$48`.
  NEVER `$22` (34) and NEVER `$3f` (63). `[$dd9e]` is
  `$00` at every frame end (links form and clear
  mid-frame only). In 1-1 the `$2a0a` dispatch actually
  uses: `$7730` (pass-through — `[$dd9e]==0` at entry,
  exits before the table rewrite), `$2b48` entries **1**
  (bank 8 `$5f5c`), **7** (bank `$1f` `$40e1`), **32**
  (bank `$1f` `$48e3`), **45** (bank `$1f` `$49b0`),
  **72** (bank `$1f` `$58e2`), and bank-8 `$7311`
  post-handler. Bank `$1f` is almost entirely uncarved
  — it holds the per-frame record behavior actually
  firing in 1-1.
- CORRECTION to slice 14: handler 17 creates a `$c72f`
  slot record, NOT a `$c200` record. The `$c200`
  record enters the `$2a0a` loop via `$7816`→`$7c57`
  (insert into the `$c0c7` list). The `$c72f` slots are
  consumed by `$169c`-family code. `$33a7` (called by
  `$7dbe`) is a map-pointer→tile-coords computation, not
  a record creator.

### §5 Byte-match proof

Clean `make` (rm `build/game.gb` first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero
diffs vs `roms/Donkey_Kong_World_Rev1_SGB.gb`.

What the generator's assertions caught (my own errors,
all fixed before the first clean build — the byte-match
itself passed on the first try once the generator was
right):

- The `$7813-$7815` "gap bytes" misread: `$7813`/`$7814`
  are the operands of the `$77f2` routine's `jp $2a59`
  at `$7812-$7814`; only `$7815` is a lone `ret` byte.
  The carve is `$7730-$7814`, not `$7730-$7812`.
- The `$7e50` table has NO `$ff` sentinel (values 0–24;
  `$ff` lives in the `$7eae` records' byte 0/1, meaning
  "don't change `$c0f9`/`$c116`"). The `$5efe` table
  values are {0,1,2,3,`$83`}, with no `$fa`/`$0a` tail.
  Both `$ff`/`$fa` claims came from the pre-slice notes
  and were wrong; the generator now asserts the real
  shapes.
- The `$77da` table entry 13 is `$79ae`, outside the
  assumed `$7896-$7944` range (31 of 32 entries are in
  range; the assertion now checks plausible bank-8
  addresses).
- The `$6467` table is 6 dw = `$6467-$6472` (hi `$6473`),
  not `$646d`: the first CARVED range left its last 3
  entries INCBIN and rgblink refused the overlap.
- The two spawn templates overlap (`$787d` vs `$788b`,
  14 bytes apart, 20 bytes each — bytes `$788b-$7890`
  are shared), so they are one `$787d-$789e` section
  with two entry labels, not two sections.
- `$2b48` entry 0 is bank `$0a` `$47a3` (not bank 2
  `$4773`) and entries 66/67 are bank `$0a`
  `$33e3`/`$33ef` (not bank 0) — the opcode misread
  (`$0a` is `ld a,[bc]`, `$02` is `ld [bc],a`).

### §6 Nacre results

`tools/run_slice5_regression.sh` and
`tools/run_slice7_cases.sh` on the final build, original vs
rebuilt identical in every case (framebuffer hash + state
trace + save):

- Slice 5: 600f `1cf92679…`, 900f `39ffd5ee…`, 3600f
  `88515f4e…`, 12000f `92d2e185…`, s8 `92d2e185…`, f0
  `3390d763…`, f1 `1cf92679…` — ALL REGRESSION CASES
  IDENTICAL.
- Slice 7: retry 15000f `0d835d95…`, mid5000
  `2ab1bb5d…`, play-right 5000f `b3cb6c8b…`, death 3000f
  `632b2eaf…` — ALL SLICE-7 CASES IDENTICAL.

All eight slice-5 and four slice-7 hashes match the
previously recorded values exactly.

### §7 Completion attempt: NO-GO (decision, not a block)

No door/clear-chain entry was found, so there is no new
lead to attempt a completion on. The parasol route
remains blocked by the greedy/waypoint flaw (slice 12
§5), and collecting the parasol would only play the
`$44` jingle anyway (slice 12 §3). No `gb_play`
completion run was burned this slice; a run should
target a NEW lead (the bank-`$1f` handlers, or a
hand-written parasol schedule), not the same waypoints.

### §8 What the next slice should do

- **Bank `$1f` `$2b48` handlers (entries 7/32/45/72:
  `$40e1`, `$48e3`, `$49b0`, `$58e2`) + bank-8 `$5f5c`
  (entry 1)** — the handlers actually firing every
  frame in 1-1, almost entirely uncarved. After that:
  the decimal-bank-`$0a` `$2b48`-handler set
  (`$4000-$7072`, 2401 instrs already walked — incl.
  the `[$c109]`-bit-3 setters `$4add`/`$4d58` and the
  `$5cf8`-table routines `$5d08`/`$5d48`/`$5d86`/`$5d9f`/
  `$5e88`/`$5e97`) and bank-16 `$5a11`/`$4e89` (the
  timer-13 body / Mario animation machine, 909 + 26
  instrs walked).
- The door/clear-chain entry remains the open question.
  The `$6d8a`→timer-13 mechanism needs a `[$c105]`=34
  record and the `$5cd8`→timer-13 mechanism a
  `[$c105]`=53 record; what arms a record (`[$c109]`
  bit 3) and which stages spawn 34/53 records are the
  questions the bank-`$0a` handler-set carve answers.

## Slice 16 — DONE, byte-matching (2026-11-24)

The per-frame `$2b48` handlers actually firing in 1-1, carved whole
— bank `$1f` entries 7/32/45/72 (+73), bank-8 entry 1's missing
table + routines, the FULL decimal-bank-`$0a` handler set, and
bank-16 `$5a11`/`$4e89`. `src/` is now 43,750 lines (was 38,720).
Clean `make` rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs.
Slice-5 regression ALL IDENTICAL, slice-7 cases ALL IDENTICAL (§6).
The door is still not found — but the carved handlers are now
proven NOT to be it (§4), and the `$2b48` table is 54/94 carved.

### §1 What was carved

Generator `tools/gen_slice16.py` (new; gb_rd recursive descent;
tables verified against ROM bytes before emission). Four new files:
`src/bank31.asm` (797 lines, 616 instrs), `src/bank8slice16.asm`
(262 lines, 306 instrs), `src/bank0aslice16.asm` (2,536 lines,
2,304 instrs), `src/bank16slice16.asm` (1,329 lines, 1,094 instrs).
`tools/gen_banks.py` CARVED gains key 31 + the bank-8/10/16 ranges;
`src/banks.asm` regenerated; INCLUDEs added to `src/main.asm`.

- **Bank `$1f` (decimal 31), the firing handlers**
  (`src/bank31.asm`): entry 7 `$40e1` (jp-hl head via `[$c10a]`)
  + the `$40f0` table (3 dw: `$40f6`, `$411e`, `$4142`) +
  routines `$40f6-$414d`; entry 32 `$48e3-$4931` (the only
  non-dispatch head of the four); entry 45 `$49b0` + the `$49bf`
  table (2 dw: `$49c3`, `$49fd`) + routines `$49c3-$4a94`;
  entry 72 `$589c` + the `$58ab` table (2 dw: `$58af`, `$58dc`)
  + routines `$58af-$58e1`; entry 73 `$58e2` + the `$58fe`
  table (8 dw) + routines `$590e-$5a3b`; shared callees
  `$7ca1-$7ce1` (incl. `$7cb8`), `$7d83-$7db8`, `$7e07-$7e43`,
  `$7e7e-$7ea5`, `$7f01-$7f5e` (incl. `$7f0a`/`$7f32`/`$7f39`).
- **Bank 8, entry 1's missing pieces**
  (`src/bank8slice16.asm`): the `$5f6b` `[$c10a]` table (8 dw:
  `$6473`, `$5f7b`, `$609d`, `$7310`, `$63b5`, `$6646`, `$63f0`,
  `$60e9`; the head `$5f5c-$5f6a` was carved in slice 15) + the
  three uncarved table routines `$5f7b-$609c` (290 bytes, the
  big movement routine with the `$6038` shared tail),
  `$60e9-$610f`, `$63f0-$6442`. The other five targets were
  already carved in slice 15.
- **Decimal bank `$0a`, the whole handler set**
  (`src/bank0aslice16.asm`): `$4000-$46e2` (14 entry heads:
  64 `$4000`, 61 `$40dd`, 65 `$41c2`, 21 `$41ce`, 22 `$4203`,
  23 `$422c`, 24 `$4252`, 25 `$427b`, 39 `$42a0`, 40 `$4345`,
  41 `$43f6`, 42 `$44c3`, 43 `$458a`, 44 `$463e`) + the
  `$46e3-$47a2` byte table (db, 192 bytes — `$4000` reads it
  two ways, see §3) + entry 0 `$47a3-$4809` + the
  `[$c109]`-bit-3 setters `$4add`/`$4d58` + `$4dbe-$4e55`
  (entry 10) + entry 11 `$5192` + `$51e0-$5211` + entries
  13/14 `$522b`/`$532b` + entry 16 `$5412` + entry 17 `$568c`
  + entry 31 `$56db` + entry 33 `$57bb` + entry 36 `$5909` +
  the `$5cf8`-table routines `$5d08-$5d5d` / `$5d86-$5e09` /
  `$5e88-$5ec9` (entries 0–3/6–7; the `$5c4f-$5cf7` timer-13
  routine + `$5cf8` table were carved in slice 15) +
  `$60f3-$612d` + entry 55 `$63a3` + entry 58 `$6582` +
  entry 62 `$678c` + entry 84 `$69be` + entry 85 `$6af9` +
  entry 49 `$6d77` + entry 86 `$6e42` + entry 87 `$6f3d` +
  entry 63 `$705f` + shared routines `$7951-$79e9` /
  `$7ab8-$7b11` / `$7b3f-$7b6b` / `$7c24-$7c56` (`$7c57+` was
  carved in slice 15).
- **Bank 16 (`$10`), the `$5a11` machine**
  (`src/bank16slice16.asm`): head `$5a11-$5a17` (`call $5f6c`,
  dispatch on `[$c213]` via the `$5a18` table, 7 entries:
  `$5a26`, `$5a46`, `$5b3c`, `$5c02`, `$5d4e`, `$5e00`,
  `$5f13`) + the nested rst-`$08` tables `$5a4f` (5),
  `$5b40` (3), `$5c06` (8), `$5d52` (3), `$5e04` (5),
  `$5f17` (4) + their routines `$5a26-$5a4e`, `$5a59-$5b3f`,
  `$5b46-$5c05`, `$5c16-$5d51`, `$5d58-$5e03`, `$5e0e-$5f16`,
  `$5f1f-$5fd2` + the `[$c213]`-record routines
  `$4993-$49c3` / `$49c8-$4a17` / `$4a18-$4aee` + their
  `$49c4` dw table (2 entries: `$4a18`, `$4a61`) + the lone
  `$c9` ret at `$4aef` + `$4e89-$4eb1` (the position nudge).

### §2 CORRECTION — `$58e2` is entry 73, not 72 (slice 15 §8 slip)

Slice 15 §8 (and the slice-16 task text) said "entries 7/32/45/72:
`$40e1`, `$48e3`, `$49b0`, `$58e2`". The `$2b48` table itself
says otherwise: entry 72 is bank `$1f` `$589c`, entry 73 is
`$58e2`. The live `[$c105]` values seen in 1-1 were {7, 32, 45,
72}, so entry 72 = `$589c` is the firing one; entry 73 (`$58e2`)
is carved here too because it sits adjacent (its head starts
the byte after the entry-72 routines end at `$58e1`) and shares
the `[$c10a]` dispatch shape. Both heads are now carved, so the
slip costs nothing going forward.

### §3 The handlers, what they do (verified from code)

- **Entry 7 (`$40e1`)** is a 3-state `[$c10a]` machine.
  `$40f6`: `[$c0fc]`/`[$c0fd]` = `$6000`, `[$c112]` =
  `$10,$0c,$00,$02,$01`, `[$c10a]++`, set bit 2 of `[$c103]`.
  `$411e`: `call $2acd`, then if `[$dd92]` & `$c0`:
  `[$c0fc]`/`[$c0fd]` = `$00ff`, `[$c10a]++`, `[$c10c]`=4.
  `$4142`: dec `[$c10c]`; at 0, `[$c10a]`=0 and `jp $40f6`
  (restart the cycle).
- **Entry 32 (`$48e3`)** is record maintenance, not a
  trigger. It sets bit 5 of `[$c103]`, range-checks `[$c0fa]`
  against `[$10,$e0)`, clamps the `[$c0fc]`/`[$c0fd]` pointer
  to `$00c0` (unless its high byte has bit 7 set or its low
  byte is < `$c0`), then: if `[$c0fa]` < `$e0` it sets bit 0
  of `[$c109]` and returns; if `[$c109]` bit 0 is already
  set it calls `$7f32` (zero `[$c0f7]`/`[$c103]`, then the
  `$7f39` loop) and jumps to `$7f0a` (the `$c0c8`-list
  link-remove). This is the record-KILL path — it removes
  a record and its link, it never writes a timer or a
  sound ID.
- **Entry 45 (`$49b0`)** is a 2-state machine. `$49c3`:
  `SeedMul` (`$1d2f`) with A=2, sets `[$c0f8]` bit 0 from
  the result, `[$c100]`/`[$c101]` = ±`$20`, `[$c10a]`=1,
  `[$c112]` = `$10,$10,$00,$00,$50`. `$49fd` is the
  busiest routine in the carve: `[$dd98]`/`[$dd92]`
  checks, then `$7ca1`/`$7cb8`/`$7e07` (the link-record
  reader); its `[$dd18]==$0a` branch sets `[$c0f9]`=3,
  `[$c116]`=`$51` (the post-`$5b`-trigger state), while the
  else branch clears bit 0 of `[$c109]` with `[$c0f9]`=0,
  `[$c116]`=`$50`; its tail adjusts `[$c100]` by
  `$c0`/`$40`/`$20` by `[$c109]` bit 0 / `[$c0f8]` bit 0.
- **Entry 72 (`$589c`)**: `$58af` (`[$c10a]++`,
  `[$c0a6]+([ $c108]-$40)` = `$18`, res 5 `[$c103]`,
  `[$c0f9]`=0, `[$c112]` = `$0d,$0c,$03,$02,$80`);
  `$58dc` (set 5 `[$c103]`, ret — a 3-instruction no-op
  with a side effect).
- **Entry 73 (`$58e2`)**: `[$c109]` bit 4 set →
  `[$c0fe]`=`$ff`, ret; else `[$c10a]` dispatch over 8
  routines `$590e-$5a3b`. `$5934` runs the `$7d83`
  proximity check and then writes `[$c831]`/`[$c835]` =
  `$64` (sound 100 — a valid `$47fc` entry, < 119);
  `$59d2` writes `[$c0fe]`=`$ff` and jumps to `$7f39`;
  `$59eb` restores `[$c0fa]`/`[$c0fe]` from `[$c10d]`/
  `[$c10e]`.
- **Shared bank-31 routines**: `$7cb8` resets
  `[$c100]`/`[$c101]`, copies `[$c105]`→`[$c104]`,
  sets `[$c105]`=`$3f`, `[$c10a]`=2, `[$c0f9]`=D,
  `[$c116]`=E, sets bit 2 of `[$c103]`, calls `$7f0a`,
  jumps to `$7e7e` (the `$c0c7`-list insert). `$7d83` is
  a proximity check (carry = miss, computed from
  `[$c0fa]`/`[$c0fe]` vs Mario's `[$c203]`/`[$c207]`).
  `$7e07` reads a link record (`[$dd9f]` bit 4 / the
  `[$c108]`-derived `$c16b` table). `$7f39` is the shared
  grid-clear loop (scans 3 rows × 3 cols of a `$74`-stride
  table from the `[$c108]` pointer, zeroing bytes equal
  to `[$c1f3]`); `$7f32` zeroes `[$c0f7]`/`[$c103]` first,
  `$59e8` jumps straight to the loop.
- **Bank-8 entry 1 (`$5f7b`)** is the 290-byte movement
  routine: `[$dd98]`/`[$dd8c]`/`[$dd92]` checks, the
  `$6038` shared tail (angle/distance math into
  `[$c100]`/`[$c101]`/`[$c10c]`/`[$c110]`, `jp $6478`
  when the result is 0), and the `$5ff8` fallback
  (flips `[$c0f8]` bit 0, `[$c100]` = ±`$80`, `[$c10b]`
  ^= 7). `$60e9` and `$63f0` are its shorter siblings
  (the `$63f0` span ends at `$6442`, adjacent to the
  slice-15 entry-6 head).
- **Bank `$0a` `$4000` (entry 64)** recomputes `[$c10a]`
  from `[$c109]`/`[$c10b]` via the `$46e3-$47a2` byte
  table: when `[$c102]`==8 it reads a `[$c10a]`-indexed
  pair at `$46e7` (1-byte stride, overlapping entries)
  and writes the nibble-swapped pair into `[$c0fc]`/
  `[$c0fd]`/`[$c100]`/`[$c101]`; otherwise it scans the
  `$46e3` 8-byte records for a `[$c10b]`-derived match
  and stores the record's offset into `[$c10a]`. The
  table is emitted as one db blob — the two views
  overlap in the same 192 bytes, so no field claims.
- **The `[$c109]`-bit-3 arming question — narrowed, not
  solved.** The setters `$4add`/`$4d58` (`set 3,[hl];
  ret`, HL=`$c109`) have NO direct caller anywhere in
  the ROM: whole-ROM byte search for `call $4add`
  (`cd dd 4a`), `call $4d58` (`cd 58 4d`), `jp $4add`,
  `jp $4d58` finds zero hits. They are entered via a
  computed jump or a dispatch table, or they are dead —
  same class as slice 14's `$5083`. (Note: `$63d7` also
  reads `set 3, [hl]` but HL=`$c103` there — it sets
  the `$2a0a` dispatch flag, NOT the arming flag; do not
  confuse the two.) The flag IS tested by 10 more
  handlers carved here (bank `$0a` entries 10/13/14/17/
  31/55/58/62/84/86 at `$4e39`/`$522e`/`$532e`/`$568f`/
  `$56de`/`$63f7`/`$6585`/`$678f`/`$69c1`/`$6e45`, all
  `ld hl,$c109; bit 3,[hl]`), on top of the entry-34/53
  setters slice 15 found. What arms a record remains
  open; the third setter slice 15 named (bank 31
  `$6ca9`) sits in the still-uncarved `$5a3c-$7ca0`
  gap.
- **Bank-16 `$5a11` — slice 15's claim VERIFIED.**
  All 13 `ldh [$ff90],a` sites in the carved machine
  are literal `$01` (8 sites: `$5a43`, `$5b12`,
  `$5b39`, `$5bff`, `$5d30`, `$5dfd`, `$5f10`, `$5f69`)
  or `$0c` (5 sites: `$5c6e`, `$5d26`, `$5d46`,
  `$5f07`, `$5f46`) — timers 1 and 12 only, exactly as
  slice 15 said from its walk. Timer 13 therefore
  resolves to timer 1 (resume gameplay) or timer 12
  (death), never to 23/26/33/42. One open observation
  from the same machine: `$5d48` writes `$33` (51) to
  `[$c836]`, the music-request field — 51 exceeds the
  41-song `$48f1` table (slice 12 §3), so either `$33`
  is a special music value or the field's meaning is
  wider than "song index"; unverified, noted not
  claimed. `$4a0f` writes `$67` (103) to `[$c833]`/
  `[$c835]` — a valid sound ID.

### §4 Door / clear-chain entry — NOT in this carve (VERIFIED)

- **No carved handler writes a clear-chain timer.**
  Whole-carve grep: zero `ldh [$ff90],a` sites in
  `src/bank31.asm`, `src/bank8slice16.asm`, or
  `src/bank0aslice16.asm`; the only timer writes in
  the slice are bank-16 `$5a11`'s thirteen, all
  `$01`/`$0c` (§3). No handler sets timer 23/26/33/42.
- **The sound writes are sound IDs, not door signals.**
  Bank-31 `$5934` writes `$64` (100), bank-`$0a`
  `$583b` writes `$42` (66), bank-`$0a` `$6127` writes
  `$12` (18) — all valid `$47fc` sound-table entries
  (< 119), consumed by the bank-2 timer tick per
  slice 12 §3. Same verdict class as `$44`/`$5f`.
- **Completion attempt: NO-GO (decision, not a block).**
  Same as slice 15 §7 — no carved handler is the
  door-tile handler or starts the clear chain, so there
  is no new lead to attempt a completion on. No
  `gb_play` run was burned this slice.
- **`$2b48` status after slice 16: 54/94 entries carved.**
  Bank 8 is complete; bank `$0a` is complete except
  entries 66/67 (see below); bank `$1f` has 5 of 40.
  Still uncarved: bank 9 entries 26 (`$6574`), 56
  (`$6cce`), 89 (`$6d8b`); bank `$0a` entries 66/67
  (`$33e3`/`$33ef` — the table's bank byte says `$0a`
  but the targets are ROM0 addresses, so the dispatch
  would jump into bank-0 code with bank `$0a` mapped;
  whether that is a table quirk or a real path is
  unresolved); bank `$1f` entries 5 (`$4000`), 12
  (`$64ee`), 15 (`$414e`), 18 (`$41ec`), 19 (`$442f`),
  20 (`$4567`), 28 (`$46b1`), 30 (`$484b`), 35
  (`$4932`), 46 (`$4a95`), 47 (`$4cd5`), 48 (`$4da6`),
  50 (`$4e31`), 51 (`$503c`), 52 (`$79ec`), 59
  (`$5201`), 60 (`$53cb`), 68 (`$5455`), 70 (`$55c9`),
  71 (`$56b6`), 74 (`$5a3c`), 75 (`$5b42`), 76
  (`$4fb9`), 77 (`$5e73`), 78 (`$5f29`), 79 (`$616e`),
  80 (`$61a5`), 81 (`$64ef`), 82 (`$66a3`), 83
  (`$67bc`), 88 (`$68dc`), 90 (`$68eb`), 91 (`$6a89`),
  92 (`$7316`), 93 (`$7bf6`). The door, if it lives in
  a `$2b48` handler at all, is among these 40 — bank 9's
  three and bank `$1f`'s 35 are the next carve.

### §5 Byte-match proof

Clean `make` (rm `build/game.gb` first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero
diffs vs `roms/Donkey_Kong_World_Rev1_SGB.gb` — after the
bank-31/bank-8 carve, after adding bank `$0a`, and after
adding bank 16 (three verifying builds, all first-try
passes).

What the byte-match check caught: nothing this slice.
The one near-miss was caught by re-reading, not by the
build: the first `tools/gen_banks.py` CARVED edit for
bank 10 omitted the `(0x4D58, 0x4D5E)` range (the second
`[$c109]`-bit-3 setter), which would have left its bytes
INCBIN'd under the new section and failed the link on
overlap. It was fixed before the build ran. (Side note:
`tools/run_slice5_regression.sh` is not executable —
run it as `bash tools/...`; pre-existing, not slice-16.)

### §6 Nacre results

`tools/run_slice5_regression.sh` and
`tools/run_slice7_cases.sh` on the final build, original vs
rebuilt identical in every case (framebuffer hash + state
trace + save):

- Slice 5: 600f `1cf92679…`, 900f `39ffd5ee…`, 3600f
  `88515f4e…`, 12000f `92d2e185…`, s8 `92d2e185…`, f0
  `3390d763…`, f1 `1cf92679…` — ALL REGRESSION CASES
  IDENTICAL.
- Slice 7: retry 15000f `0d835d95…`, mid5000
  `2ab1bb5d…`, play-right 5000f `b3cb6c8b…`, death 3000f
  `632b2eaf…` — ALL SLICE-7 CASES IDENTICAL.

All eleven hashes match the previously recorded values
exactly. The play-right and death cases exercise the
carved `$2b48` handlers live (state-16 timers 3–10,
Mario moving and dying in 1-1) on both ROMs.

### §7 Verified vs inferred

VERIFIED: the `$58e2`-is-entry-73 correction (read from
the `$2b48` table bytes); the four bank-`$1f` heads +
their `[$c10a]` tables (ROM bytes + byte-match); entry
32 as the record-kill path (code — `$7f32`/`$7f0a`
bodies read, no timer write); the `$4add`/`$4d58`
no-direct-caller result (whole-ROM byte search, zero
hits for `call`/`jp` forms); the 10 bank-`$0a`
`[$c109]`-bit-3 test sites (code); bank-16 `$5a11`
setting only timers 1/12 (all 13 literal writes read
from the carved code); the sound-ID values `$64`/`$42`/
`$12` (valid `$47fc` entries); byte-match + both
regression suites on the final build.
INFERRED (not verified): that the door lives in one of
the 40 uncarved `$2b48` entries (it is the best
remaining lead, but no carved handler points at it);
that `$4add`/`$4d58` are entered via a computed jump
(the zero-hit byte search rules out direct calls, not
computed ones); what `$33` to `[$c836]` means (slice 12
said song < `$29`; 51 is out of range); the `$46e3`/
`$46e7` table's record structure (emitted as a db blob
with no field claims); the `$2b48` entries 66/67 ROM0
targets (table quirk vs real path, unresolved).

## Slice 17 — DONE, byte-matching (2026-11-24)

The `$2b48` table is now 94/94 carved — every entry has a
curated handler. Bank 9's three entries (26 `$6574`, 56
`$6cce`, 89 `$6d8b`) with callees, bank `$0a` entries 66/67
(`$33e3`/`$33ef`, RESOLVED as a real path, not a table
quirk), bank `$1f`'s remaining 35 entries in table order,
and bank 0 `$0f95-$0fa0` (the last unverified callee of
the timer-13 body `$0968`). Generator:
`tools/gen_slice17.py` (walks: bank 9 1,087 instrs, bank
31 6,316 instrs, bank 0 152 instrs; no `rst $08` sites
anywhere in this slice). Outputs: `src/bank9slice17.asm`
(1,364 lines), `src/bank31slice17.asm` (7,212 lines),
`src/bank0slice17.asm` (14 lines). `src/` is now 52,487
lines (was 43,750).

### §1 What was carved

- Bank 9, entry 26 `$6574-$6649`: head reads the `$6f9c`
  `[$dd18]` byte table, the `$66a3` `[$c10b]*3` records,
  the `$66a0` `([$c10e]>>1)` table and the `$6696`
  `[$c10a]` remap, then a shared tail at `$6616` (push
  `$6660`, compute the map pointer from `[$c0fa]`/
  `[$c0fe]`, `jp hl` through the `$664a` table — 8
  entries `$66b7, $66fb, $673f, $6783, $6f9b, $6f9b,
  $67c7, $680b`). `$6f9b` is a 1-byte `ret` (`$c9`) —
  table entries 4/5 are no-op returns. The `$6660`
  shared return routine and all table routines are
  carved (`$66b7-$684e` plus callees down to `$6c7e-
  $6ca9`).
- Bank 9, entry 56 `$6cce-$6d32`: head ends `jp hl`
  through the `$6d33` table (identical words to
  `$664a` — a second copy), plus the `$6490-$64ca`
  callee (writes sound `$6a` to `[$c82f]`/`[$c835]`,
  fills a record, `call $3337`, `call $33a7` — bank-0
  trampolines — ends `jp $169c`). Two 8-word
  signed-offset tables `$6d49` and `$6d5b` (same 8
  values, permuted; selected by `[$c10e]` bit 0,
  indexed by `[$c10b]*2`).
- Bank 9, entry 89 `$6d8b-$6d99`: 10-instr `jp hl`
  head through the `$6d9a` table — 2 entries
  (`$6d9e, $6de0`), not 10. The "entries 2–9" (`$0efa,
  $87c1, …`) are a misread of the `$6d9e` routine's
  code bytes (same trap as slice 16's `$58e2`
  correction): the word at `$6d9e` (`$0efa`) is the
  first two bytes of routine 0's `ld a,[$c10e]`
  (`fa 0e c1`), not a table entry. Routines `$6d9e-
  $6dd3` and `$6de0-$6e62` plus callees are carved.
  `$6dd4-$6ddf` is a 12-byte DATA blob (`00 20 ff e0
  00 40 ff c0 00 80 ff 80`), pointed to by `$6da5`
  (`ld hl,$6dd4`) — meaning unresolved. (See §5 for
  what the byte-match check caught here.)
- Bank 9 data: `$6696-$66b6` as one db blob (the
  `$6696` `[$c10a]` remap 8B, `$66a0` 3B, `$66a3`
  records 12B, `$66af-$66b6` 8B unresolved — overlapping
  views, no field claims, like slice 16's `$46e3`);
  `$6f9c-$6fab` as a db blob (`[$dd18]`-indexed, indices
  0–12, `$ff` at 12+).
- Bank 31 (`$1f`), all 35 remaining entries, each head
  plus its `[$c10a]` `jp hl` table and the table
  routines the walk reaches: 5 `$4000` (direct routine,
  bit-4 branch + `jp hl` via `$4053`, 3 entries), 12
  `$64ee` (1-byte `ret` — a no-op entry), 15 `$414e`
  (5), 18 `$41ec` (5), 19 `$442f` (direct routine, 147
  instrs), 20 `$4567` (3 — NOT 4: the 4th word `$403e`
  is routine 0's first instruction `ld a,$40`, and
  `$403e` is also entry 5's mid-routine `call $7f0a`,
  a coincidence, not an entry), 28 `$46b1` (4), 30
  `$484b` (direct, 144), 35 `$4932` (2), 46 `$4a95`
  (3 — entry 2 is entry 47's head `$4cd4`, shared),
  47 `$4cd5` (3), 48 `$4da6` (3), 50 `$4e31` (4), 51
  `$503c` (direct, 115), 52 `$79ec` (direct, 76), 59
  `$5201` (4), 60 `$53cb` (3), 68 `$5455` (2), 70
  `$55c9` (3), 71 `$56b6` (5), 74 `$5a3c` (direct, 41 —
  `[$c109]` bit-0 test, sound `$62`, `[$c213]`=1), 75
  `$5b42` (12 instrs, pushes `$5b55` as return, `jp hl`
  via `$5b5b`, 9 entries — `$5cf6` is a 1-byte `ret`,
  `$5cf7` the next routine), 76 `$4fb9` (96, `call
  $7d4c`), 77 `$5e73` (3), 78 `$5f29` (9 — 9th `$60de`),
  79 `$616e` (96, `call $7d4c`), 80 `$61a5` (direct,
  134), 81 `$64ef` (7), 82 `$66a3` (5), 83 `$67bc`
  (direct, 84), 88 `$68dc` (direct, 31), 90 `$68eb`
  (3), 91 `$6a89` (9 — 9th `$6e95`), 92 `$7316` (22
  entries, all plausible, increasing `$7351-$79dd`),
  93 `$7bf6` (direct, 61). Table lengths are
  (first-routine − base)/2 from the ROM bytes; every
  table entry was asserted as a decoded instruction
  start in the generator. Shared callees carved:
  `$7050`, `$723e`, `$7ea6`, `$7de4`, `$7bf6`. Data as
  db: `$6cc2-$6cc6` (5-byte template copied to `$dd81`
  by `$6c60`), `$6d8e-$6da1` (20-byte template copied
  to `$c1ab` by `$6c60`'s tail — byte 14 is `$aa`, byte
  18 is `$00`).
- Bank 0 `$0f95-$0fa0`: the scroll-clamp wrapper called
  from 8 state-16 timer bodies (and from timer-13's
  body `$0968`) — `push hl/bc; xor a; ld [$c706],a;
  call $152e; pop; ret`. Its callee `$152e` was carved
  in slice 6. Raw bank-0 A2b in `src/main.asm` split
  `$0f74-$0fc0` into `$0f74-$0f94` (`$21`) and
  `$0fa1-$0fc0` (`$20`) around it.
- Bank `$0a` entries 66/67: NO new carve — see §2.

### §2 Entries 66/67 RESOLVED: real path, already carved

The `$2a0a` dispatch reads the bank byte first and
switches bank before reading lo/hi (`$2a59-$2a71`).
Entries 66/67 say bank `$0a`, targets `$33e3`/`$33ef`
(ROM0 addresses). Since `$0000-$3fff` always maps ROM0
regardless of the bank register, the `$0a` switch is
harmless; `jp hl` lands at bank-0 `$33e3`/`$33ef`.
Those are already curated in `src/bank0slice3.asm`:
two trampolines in the same shape as the `$2b0e`/
`$2b1a`/`$2b24`/`$2b30`/`$2b3c` trampolines — `ldh
a,[$ff8c]; push af; ld a,$0c; rst $10; call $4e15`
(`$33e3`) / `call $4e35` (`$33ef`); `pop af; rst $10;
ret` — switch to bank 12, call, restore bank, `ret`
to `$2a72`. Bank-12 `$4e15`/`$4e35` are already carved
in `src/bank12.asm`: record-byte checks on `[$c106]`/
`[$c107]` + `$7e` offset (byte == `$8d`, second byte
== `$02`/`$04` for `$4e15`, `$06`/`$00` for `$4e35`);
on match `jp $33fb` (the third bank-0 trampoline:
switch bank `$0a`, `call $7ae5`, `call $7c88`,
restore, ret); otherwise `ret nz`. The mechanism is
proven statically end-to-end — every byte of the chain
is carved and byte-matched. Live firing was NOT
observed in 1-1 because no `[$c105]`=66/67 record
occurs there (live byte-14 values in 1-1 were
{0,1,2,3,6,7,32,45,72}) — that limit is recorded
honestly, not papered over.

### §3 CORRECTIONS to slice 15

- **Timer 13 has FOUR known `$2b48` setters, not two.**
  Slice 15's "exactly TWO" was wrong — it surveyed
  only the two then known; the bank-`$1f` set was
  uncarved then. The four, all setting `ld a,$0d;
  ldh [$ff90],a`:
  - Entry 34 (bank 8 `$6d8a`→`$6ecd`) and entry 53
    (bank `$0a` `$5cd8`→`$5c4f`) — slice 15, both gated
    on `[$c109]` bit 3.
  - **Entry 46 (bank `$1f`), table entry 1 `$4aee`:**
    `ld hl,$c109; bit 3,[hl]; jp z,$4b8c` — if set:
    `res 3,[hl]` (**disarms**), `[$c10a]=2`,
    `[$c201]=$46`, position math on `[$c207]`/`[$c203]`,
    `[$c213]=5`, `[$dd1a]=0`, `[$dd18]=$07`,
    `[$dd21]=$ff`, `[$ff91]|=$c0`, `[$dd2b]=$09`,
    `[$dd2c]=$0b`, **timer=13 at `$4b6e`/`$4b70`**,
    `[$c100]=0`, `res 2,[$c103]`, `[$c102]=0`,
    `[$c0f9]=$0a`, `[$c116]=1`, `ret`. If bit 3 clear:
    `$4b8c` countdown path (dec `[$c10c]`, negates
    `[$c100]`, toggles `[$c855]` bits, scans `$c22e`
    records).
  - **Entry 92 (bank `$1f`), table entry 15 `$780b`:**
    NOT gated on bit 3 — gated on **position**
    (`[$c203]<$6c` and `[$c207]-$48<$10`, i.e. Mario
    OAM Y<108, X in [72,88) — near the key niche) plus
    a `[$c10c]` countdown. On trigger: sets
    `[$c203]=$68` etc., **timer=13 at `$7845`/`$7847`**,
    `[$ff91]|=$c3`, set bit 7 of `[$ff92]`,
    `[$c836]=$80` (music-request field — out of the
    41-song range, like slice 16's `$33` to `[$c836]`;
    unverified meaning), sound writes `[$c82d]=$34`,
    `[$c82e]=3`, `[$c835]=3` (sound IDs 52 and 3, valid
    `$47fc` entries), `[$dd2b]=$18`, `[$c213]=6`,
    `[$dd21]=7`, `[$dd22]=$ff`, `jp $754e`.
- **`$6ca9` is NOT a callable subroutine — it is inline
  fall-through code inside `$6c60`.** Slice 15's
  "third setter" framing was wrong. The arming path is
  entry 91 state 4 (`$6c60`): `ld a,[$c109]; bit 2,a;
  jp z,$723e`; if bit 2 set: `res 2`, setup (`[$c10b]`,
  `[$c10d]`, `[$c110]`, copy 5 bytes `$6cc2`→`$dd81`),
  `[$c10c]=1`, `[$c10a]=5`, then `ld a,[$c109]; bit
  3,a; jp nz,$723e`; if bit 3 clear, fall through to
  **`$6ca9`: `ld hl,$c109; set 3,[hl]`** (then
  `[$c10b]=1`, `[$c1f4]=$50`, `[$c1f5]=2`, copy 20-byte
  template `$6d8e`→`$c1ab`, `call $106e`, `call $1097`,
  `[$c1f3]=B`). `$723e` is the already-armed/
  already-done branch (clears `[$c100]`, position
  checks, copies `$730a`/`$7306` records). Entry 91's
  return continuation `$5b55` (`ld hl,$c109; res
  3,[hl]; ret`) clears the flag on return.
- **What remains UNVERIFIED about arming:** whether the
  SAME record instance flows 91→46. `$6c60` arms bit 3
  on its own (type-91) record; `$4aee` consumes bit 3
  on its own (type-46) record. No link found: the
  `$7730` transition tables (`$7e50`/`$7eae`, bank
  `$0a`) rewrite `[$c105]` only to `$3f` (byte 2 of
  every record is `$3f`, except V=11 → `$36`/54) —
  never 46; `[$c105]`=91 cannot index the 25-entry
  `$7e50` table. The `$6d8e` spawn template's byte 14
  is `$aa` and byte 18 is `$00`, so the record `$6c60`
  spawns is NOT born as type 46 nor born armed. Live
  `[$c105]` values in 1-1 never include 46 or 91. The
  two halves are pinned; the connection is open.
- **`$4add`/`$4d58` STILL have no direct caller**
  (re-verified this slice): whole-ROM byte search —
  `$4add` pair: **zero hits anywhere**; `$4d58` pair:
  one hit, bank 29 `$54b4`, inside bank-29 data (bytes
  `58 b5 58 4d`, preceded by `$58` not `$cd`/`$c3`/
  `$21`, in a repeating `$58 xx` data pattern — not a
  call/jp/ld-hl/dw entry). No `$4add`/`$4d58` reference
  in the bank-31 or bank-9 walks either. They remain
  caller-less (dead or computed-jump entry, same class
  as slice 14's `$5083`).

### §4 Door / clear chain: verdict stands, no completion attempt

Whole-carve timer-write grep: bank 31 has exactly two
`ldh [$ff90],a` sites (`$4b70` and `$7847`, both
literal `$0d`=13); bank 9 has zero. No handler in this
slice writes timer 23/26/33/42. Timer 13's body `$0968`
contains no timer write; its callees are `$2a0a`
(dispatch), bank-16 `$5a11` (slice 16 verified: only
timers 1/12), bank-16 `$4e89` (nudge, no timer write),
bank-8 `$4000` (map builders), and bank-0 `$0f95`
(carved this slice — just the scroll-clamp wrapper
around `$152e`, **no timer write**). So timer 13 still
resolves only to timer 1 (resume) or 12 (death), never
23/26/33/42. The door/clear-chain entry is still NOT
found. No completion attempt was run this slice — no
new door lead to attempt one on (same NO-GO decision
as slices 15–16).

### §5 Byte-match proof

Clean `make` (rm `build/game.gb` first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero
diffs vs `roms/Donkey_Kong_World_Rev1_SGB.gb` — first
clean build after the §5 fix below.

What the byte-match check caught: the LINK caught it,
not the hash — the first build failed with `Undefined
symbol jr_009_6dd6` at `src/bank9slice17.asm(1082)`. The
generator had seeded `$6dd4` as a code entry; the bytes
there decode as `nop; jr nz,$6dd6; rst $38…` — garbage.
The real story: `$6dd4` is never jumped or called
(whole-walk reference search: zero hits); `$6da5`
does `ld hl,$6dd4` — a DATA pointer, like the
`$6cc2`/`$6d8e` templates. The fix: `$6dd4-$6ddf`
emitted as a 12-byte db blob, the `$6d9e` carve split
into `$6d9e-$6dd3` and `$6de0-$6e62`, the spurious seed
dropped. Lesson (same class as slice 16's `$58e2`
correction): a `ld hl,$X` reference is a data pointer,
not a code seed — only `call`/`jp`/`jr`/table targets
seed the walk. The generator now asserts every table
entry is a decoded instruction start, which would have
caught a table misread but not this one; the link error
did.

### §6 Nacre results

`tools/run_slice5_regression.sh` and
`tools/run_slice7_cases.sh` on the final build, original vs
rebuilt identical in every case (framebuffer hash + state
trace + save):

- Slice 5: 600f `1cf92679…`, 900f `39ffd5ee…`, 3600f
  `88515f4e…`, 12000f `92d2e185…`, s8 `92d2e185…`, f0
  `3390d763…`, f1 `1cf92679…` — ALL REGRESSION CASES
  IDENTICAL.
- Slice 7: retry 15000f `0d835d95…`, mid5000
  `2ab1bb5d…`, play-right 5000f `b3cb6c8b…`, death 3000f
  `632b2eaf…` — ALL SLICE-7 CASES IDENTICAL.

All eleven hashes match the previously recorded values
exactly.

### §7 Verified vs inferred

VERIFIED: the 66/67 mechanism (every byte of the
`$33e3`/`$33ef` → bank-12 → `$33fb` chain carved and
byte-matched; the `$0a` switch is harmless because
`$0000-$3fff` always maps ROM0); the four timer-13
`$2b48` setters (code read — `$4b70`/`$7847` are the
only two `ldh [$ff90],a` sites in the whole bank-31
carve, bank 9 has none); entry 46 disarming bit 3 on
entry and entry 92's position gate (code read);
`$6ca9` as inline fall-through inside `$6c60` (code
read — `$6c60`'s `jp nz,$723e` falls through to it);
`$5b55` clearing bit 3 on return (6 bytes read);
`$4add`/`$4d58` having no direct caller (whole-ROM
byte search, re-verified); the `$6dd4` data-blob
verdict (zero code references + garbage linear decode
+ `ld hl,$6dd4` data pointer at `$6da5`); the 25
`[$c10a]` table lengths (ROM bytes + generator
assertions); byte-match + both regression suites on
the final build.
INFERRED (not verified): that a 91-armed record ever
becomes a 46 record (no `[$c105]` rewrite to 46
exists, and 1-1 never shows 46/91 live — the two
halves are pinned, the connection is open); what the
`$6dd4` 12-byte blob means; what `$80` to `[$c836]`
(entry 92) and `$33` to `[$c836]` (slice 16) mean
(both out of the 41-song range); the `$6696`/
`$66a3`/`$6f9c` table field meanings beyond their
index registers (emitted as db blobs with index notes
only); that the door lives in one of the remaining
uncarved regions (the `$2b48` table is now exhausted
as a lead — see Next slices).

## Slice 18 — DONE, byte-matching (2026-11-24)

§1 **The 91→46 record-lifecycle link is DEAD — proven,
not merely unverified.** Static, whole-ROM: `$2b48`
entries 34 (bank 8 `$6d8a`), 46 (bank `$1f` `$4a95`),
53 (bank `$0a` `$5cd8`), 91 (bank `$1f` `$6a89`), 92
(bank `$1f` `$7316`). The `$7730` transition records
(`$7eae`, 25 records) rewrite `[$c105]` to `$3f` for
all except record 11 → `$36` — never 46. Direct
`ld [$c105],a` writers in the whole ROM: exactly 11
sites, values `$53`,`$37`,`$36`,`[$c104]&$7f`,`$34`,
`$21`,`$36` (bank 10) and `$0c`,`$0c`,`$5d`,`$34`
(bank 31) — none is 46. The one variable path, bank-10
`$7378` (`ld a,[$c104]; and $7f; ld [$c105],a`), then
dispatches via the `$7e3c` dw table indexed by
`$7dde[newtype]`; `$7dde[46]`=0 → `$7e3c[0]`=`$7815`
(a 1-byte `ret`, a no-op) — so even if it ran with
`[$c104]`=`$46`/`$c6`, the follow-up is a no-op. Its
containing routine (~`$7300`–`$75af`) has NO direct
caller anywhere in the ROM (whole-ROM search for
`78 73` — zero hits), the same orphaned class as
`$4add`/`$4d58`/`$5083`; entry mechanism unverified.
The `$7816` spawn routine copies 20-byte templates to
`$c1ab`, NOT to `$c200` (templates bank 10 `$787d`
byte 14=`$18`, `$788b` byte 14=`$cd`; bank 7 `$643f`
byte 14=`$fa`; bank 31 `$6d8e` byte 14=`$aa`) — none
spawns a `$c200` type-91 record. `$c200` records come
from the level-load spawner (bank 12 `$403c`). The
`$2a85` writeback WOULD persist a 91→46 rewrite if
one existed — none does.
Live (`tools/survey18_records.py`, slice-13 dumps, all
101 loadable stages): **type-46 records exist in exactly
ONE stage — B1, record 26, in all 3 dumps** (bytes e.g.
`01 74 02 68 00 00 00 45 80 00 80 01 85 00 2e 8f ce 5a
00 01 00 18 01 00 …`, byte 14=46, byte 18=0). Type-34:
B27, B59, B67, B95, B97. Type-53: B23, B31, B63, B75.
Type-92: NONE. Type-91: NONE in any of the 101 stages.
**No record in any surveyed stage has byte 13 in
{`$46`,`$c6`}** — the only values that could make
bank-10 `$7378` write `[$c105]`=46. Byte-18 bit-3-set
("armed") records exist but on OTHER types: type 66
(97 dumps), 67 (84), 6 (3), 75 (1) — bit 3 of byte 18
is a general flag, not exclusive to the 91-arming.
Dense B1 run (new, `build/nacre-test/slice18/B1/`,
6000f, dumps every 100 frames 2000–5900, 40 dumps):
type-46 record 26 present in EVERY dump, byte 18=`$00`
always, byte 13=`$00` always, state-16 timers 6/10
alternating, no 91 ever. `gb_watch` on B1, 6000f,
`ff90=0d` (timer-13 set): **0 hits** — timer 13 never
fires in B1 despite the type-46 record being dispatched
every frame. Honest residual: dumps cover stage loads
with Mario idle. A 91 record spawning mid-play from a
pickup/spawn routine is not covered by the dump survey,
but no surveyed spawn mechanism produces one, and no
code path rewrites to 46 at all.

§2 **Bank-11 sprite blocks — table extent 128 → 256,
VERIFIED (not inferred).** `$112c` indexes the table
by the FULL record byte 0 (C = byte 0, HL = `$4000` +
2*C, no masking), so the table must cover all 256 byte
values; live record byte-0 values across the 101
surveyed stages reach **229** (max; values seen
{0,1,108,110,112,113,160,164,174,192,226,227,228,229};
record byte-1 max 254). All 256 words (`$4000`–
`$4200`) are plausible pointers (`$4200`–`$7xxx`),
none points into `$4100`–`$41ff`, 35 are `$4200` in
bank 11 (99 in bank 29). Whole-ROM survey: ONLY banks
11 and 29 carry this table (256/256 plausible words);
bank 29's table differs in 220/256 entries. Bank 5's
252/256 is the stage-pointer table coincidence; bank
28's 190/256 is data. The 256 entries point at **176
distinct targets** in `$4200`–`$7948`; they partition
the range exactly (consecutive-target gaps sum to the
span — no gaps, no overlaps). Last block `$7948` runs
to `$7e3d` (bank 11's last non-`$ff` byte is at
`$7e3c`; `$7e3d`–`$7fff` is 451 bytes of `$ff` padding,
stays INCBIN). Banks 11 vs 29 `$4200`–`$7fff` share
only 1644/15872 bytes (separate sprite sets); their
`$4200` default blocks are byte-identical. Files:
`tools/gen_slice7.py` `emit_bank11` extended 128→256
dw (re-ran — `src/bank0slice7.asm` and `src/bank18.asm`
regenerated with zero diff); new `tools/gen_slice18.py`
emits `src/bank11slice18.asm` (176 `db` blocks, each
labelled `Bank11_SpriteBlock_XXXX` with its table-entry
owners listed); `tools/gen_banks.py` CARVED bank 11 now
`(0x4000, 0x4200), (0x4200, 0x7E3D)`; `src/main.asm`
INCLUDEs `bank11slice18.asm` after `bank11.asm`.
Block internal structure not decoded (plain `db`;
`$112c` shows 2×record[1] selects a sub-entry whose
first byte is a count and second byte `$f0`/`$f1`
marks flip variants). Bank 29's table + blocks NOT
carved this slice (next-slice target).

§3 **Bank-9 / bank-31 gaps carved, in task order.**
Whole-ROM byte-pair reference searches are too noisy
(mostly data in other banks); same-bank carved-code
references are the signal.
- Bank 9 `$684f-$6907` (185 bytes): three map-sample
  dispatch routines (`$684f`, `$6893`, `$68d7`), same
  shape as the `$664a`-table routines (slice 17):
  HL = DE + a signed offset, sample [HL] & `$c0`,
  jump to the carved `$6ae7`/`$6b8d`/`$6bbc`/`$6bf2`/
  `$6c34`/`$6c7e`/`$6cb7` routines. `$68d7` also writes
  `$c112-$c116` (`$10`,`$10`,0,0,`$a0`), sets bit 2 of
  `[$c103]`, clears `[$c102]`, then dispatches on
  `[$c10e]` bit 0 (`jp nc,$6ad5`). Entry mechanism for
  all three heads is UNVERIFIED (no call/jp ref
  anywhere in the ROM; the preceding spans end in jp,
  no fall-through). Alignment trap found: `$6891`–
  `$6892` are the `jp $6ae7` operand bytes, NOT code —
  a walk seeded at `$6891` misaligns by 2 (decodes
  `rst $38` + `ld l,d` garbage that coincidentally
  flows on). Correct continuation seed is `$6893`.
- Bank 31 `$4499-$4566` (205 bytes): a 3-entry dw
  table (`$449f`,`$44dc`,`$4540`) read by the carved
  `$4205-$4498` span's jp-hl dispatch (`ld a,[$c10a];
  add a; ld hl,$4499; ...; jp hl` at `$4491`), plus
  the three table routines. `$449f` sets `[$c103]`
  bit 2 and `[$c109]` bit 0, inc `[$c10a]`, `call
  $1d2f`, position math, `[$c0f9]`=`$2a`,
  `[$c116]`=`$51`. The earlier walk seeded at `$4499`
  misdecoded table words as code — the table base load
  at `$4491` is a data pointer, not a code seed.
- Bank 31 `$506c-$5200` (404 bytes): a 7-entry dw
  table (`$507a`,`$50e0`,`$510f`,`$5175`,`$519b`,
  `$51ce`,`$51e3`) read by the entry-51 handler's
  `ld hl,$506c` … `jp hl` at `$5064`, plus the seven
  routines (walk from `$506c` dies after 10 instrs —
  it is data, not code).
- Bank 31 `$6244-$64ed` (681 bytes): an 11-entry dw
  table read by the entry-80 handler's `ld hl,$6244`
  … `jp hl` at `$623c`, plus the eleven routines.
- Bank 31 `$6fde-$704f` (113 bytes): a 28-byte data
  table (`$6fde-$6ff9` — exactly `$1c` bytes, matching
  the `ld c,$1c` in the routine below), a countdown/
  state routine `$6ffa-$704a` (dec `[$c867]`,
  `[$c0fa]`+=4, dec `[$c10c]` with `$1e` reload,
  `[$c10a]`=1 or `$0c`, `[$c114]`=1 on the `[$c0a4]`==2
  path, then memcpy `$6fde`→`$c1c4` via `$106e` and
  `jp $6f89`), and a 5-byte countdown wrapper
  `$704b-$704f` (`dec [$c10c]; ret nz`) falling through
  into the carved `$7050` shared routine. `$6ffa`'s
  entry is unverified; `$704b`'s fall-through into
  `$7050` is structural (same countdown shape as
  `$708f`).
- Bank 31 `$708f-$723d` (430 bytes): only the head is
  code — `$708f-$70cd` (`dec [$c10c]; jp nz,$723e`;
  position math on `[$c213]` records; `[$c10a]`=4,
  `[$c114]`=2; `jp $723e`) plus the tiny state-setter
  `$70d0-$70de` (`[$c10a]`=1, `[$c10c]`=`$0f`,
  `[$c114]`=0). Remainder `$70df-$723d` stays INCBIN
  (mixed data: byte tables incl. ASCII-ish runs, plus
  two `[$c10c]`-countdown fragments at the tail with no
  verified seed). Alignment trap: `$70ce` is the `jp
  $723e` operand byte, NOT code — the tiny routine
  starts at `$70d0`, same trap as `$6891`. Entry for
  `$708f` unverified.
- Bank 31 `$7a12-$7bf5` (483 bytes): a 6-entry dw
  table read by the `$7934-$7a11` span's `ld
  hl,$7a12` … `jp hl` at `$7a0a`, plus the six
  routines.
All table lengths are the increasing-dw-run rule,
verified against the ROM bytes; every table entry is
asserted to be a decoded instruction start; every
carve's coverage is asserted byte-complete (no
uncovered bytes in range). Generator:
`tools/gen_slice18.py` extended with `emit_carve` /
`emit_dw_table` / `emit_db` helpers in the
`gen_slice17.py` pattern; new files
`src/bank9slice18.asm` (104 lines) and
`src/bank31slice18.asm` (1170 lines); INCLUDEs added
after the slice-17 files in `src/main.asm`. `src/`
now 55,633 lines (was 52,487 at slice start).

§4 **Door / clear chain: no new lead.** No completion
attempt run (NO-GO, same as slices 15–17 — the 91→46
link was the lead and is now dead). The `$7378`
routine and the `$708f`/`$6ffa` countdown routines are
newly-noted code whose roles are unverified; none
writes timers 23/26/33/42 (the `$708f` routine jumps
only to `$723e`, the `$6c60` armed-branch shared
routine; `$6ffa` jumps only to `$6f89`). The `$2b48`
table is DONE (94/94) and closed as a door lead;
timer 13 still resolves only to timer 1 or 12.

§5 **What byte-match caught.** (a) `gen_banks.py`
prints to stdout — running it bare does NOT update
`src/banks.asm`. The first build failed with a link
overlap ("Bank 31 `$625a-$64ed` `$6244`-table
routines" vs INCBIN "Bank 31 `$6244-$64ed`") because
`banks.asm` still held the old INCBINs; regenerate
with `python3 tools/gen_banks.py > src/banks.asm`.
(b) Hand-reflowing CARVED lines dropped entries:
across the fix attempts, `(0x7CE2, 0x7D83)`,
`(0x69AC, 0x6A08)`, `(0x6A9C, 0x6AC8)`, `(0x7E07,
0x7E44)`, `(0x6B8D, 0x6BE9)` were each lost once,
plus the dict's closing `}` — each surfaced as a link
overlap on the next build ("Bank 31 `$7ce2-$7d82`
entry-93 callee" vs INCBIN, "Bank 9 `$69ac-$6a07`
table-routine callee" vs INCBIN, and a syntax error).
All restored and verified by diffing the CARVED tuple
set against git: dropped — only the intended
`(0x4000, 0x4100)` bank-11 replacement; added —
exactly the 9 new ranges. Lesson: never reflow
CARVED lines by hand — insert tuples only, and diff
the tuple set after editing. Final build: `rm
build/game.gb && make` → SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp`
clean. Nacre regressions on the final build, original
vs rebuilt identical: slice-5 suite ALL IDENTICAL
(600f `1cf92679…`, 900f `39ffd5ee…`, 3600f
`88515f4e…`, 12000f `92d2e185…`, s8 `92d2e185…`, f0
`3390d763…`, f1 `1cf92679…` — all match the slice-17
reference hashes); slice-7 suite ALL IDENTICAL
(retry 15000f `0d835d95…`, mid5000 `2ab1bb5d…`,
play-right `b3cb6c8b…`, death 3000f `632b2eaf…` —
all match). `git status` clean of build artifacts /
`.gb` / `.sav` / binaries / `__pycache__`.

## Slice 19 — DONE, byte-matching (2026-11-24)

§1 **Bank-29 sprite-table selector: PINNED, statically and live.**
`$10d5` (bank 0) selects bank `$1d` (29) then jumps into the
`$10e3` iterator loop body, skipping the bank-`$0b` select at
`$10e0`; `$10dd` selects bank `$0b` (11) at `$10e0` and runs the
same loop. The selector is the call site itself — no runtime
flag. Static proof: whole-ROM pattern scan finds exactly ONE
`ld a,$1d; rst $10` in the ROM (bank-0 `$10d8`); `$10d5`'s
callers are ONLY state-16 transition steps (bank-0 `$09d2`,
`$0ab2`, `$0ae1`, `$0b12`, `$0b95`, `$0bde`) plus state-20 step 0
(`$2907`), while `$10dd`'s callers are everywhere (bank 1,
state-20 `$285a`, ...). So state-16 transition rendering uses
bank 29's sprite set; everything else uses bank 11's.
Live proof (`tools/gb_bank29.c`, new cycle-stepping probe —
frame-stepping cannot see these switches, the bank is restored
before the frame ends): 6000f Start+A run, original ROM:
**1,770 executions of `rst $10` with A=`$1d` at `$10da`** (first
at frame 1189, state 18 timer 28 — the state variable reads 18
while the CPU is still inside a transition step, the slice-3
mid-routine effect) vs **21,756 with A=`$0b` at `$10e2`**
(first at frame 10, title state 2); `$10d5` entered 1,771 times.
Rebuilt ROM reproduces the counts exactly (1770/21756/1771).
`gb_watch ff8c=1d` on the same run found 0 hits — NOT evidence
against the selector, just the frame-sampling limit (recorded so
it is not re-run as a disproof).

§2 **Bank 29 carved: table + 121 blocks.** 256 dw at `$4000`,
121 distinct targets in `$4200`–`$7d02`, partitioning the range
exactly; last block `$7d02` runs to `$7e94` (last non-`$ff` byte
at `$7e93`; `$7e94`–`$7fff` is `$ff` padding, stays INCBIN). 99
entries are `$4200`; the `$4200` default block is byte-identical
to bank 11's. Files: `src/bank29.asm` (256 dw),
`src/bank29slice19.asm` (121 `db` blocks, each labelled
`Bank29_SpriteBlock_XXXX` with its table-entry owners);
`tools/gen_banks.py` CARVED bank 29 now `(0x4000,0x4200),
(0x4200,0x7E94)`. Bank 29 is DONE except its `$ff` padding.

§3 **The `$7378` routine's entry mechanism: RESOLVED + live.**
`$7378` is not a routine head: the head is `$7369` (`dec
[$c10c]; ret nz; res 3,[$c103]; ld a,[$c104]; and $7f;
ld [$c105],a`, then the `$7dde`/`$7e3c` dw dispatch ending
`jp hl`). `$7369` is `[$c10a]`=4 of the 7-entry dw table at
`$7073` (`$7081`, `$7815`, `$70a6`, `$7297`, `$7369`, `$738f`,
`$7400`), read by the `$2b48`-entry-63 handler `$705f` (carved
slice 16: `ld a,[$c10a]; add a; ld hl,$7073; ...; jp hl`, gated
on `[$ff93]` bit 5 clear). Slice 18's "no direct caller" was
true but beside the point — the entry is via the jp-hl table,
the same pattern as bank 31's `$6a98` table. The whole
`$7073`–`$7599` span is carved here: the table, entry routines
`$7081`/`$70a6`/`$7297`/`$7369`/`$738f`/`$7400` (entry 1 `$7815`
was already carved, a 1-byte ret), data `$7290`–`$7296` (7
bytes, indexed by `[$c705]`) and `$74aa`–`$74b9` (16 bytes, two
8-byte records loaded via DE by the `$748f` routine). Note
`$7300` is NOT a routine head: it is the `$07` immediate byte
of `cp $07` at `$72ff` (slice 18's "~`$7300`" was approximate;
the real head is `$7297`, table entry 3). Live proof
(`tools/gb_pcwatch.c`, new bank-qualified PC probe — an
unqualified PC is ambiguous across banks: the first run
counted 2,765 `$7378` hits that were mostly bank 8's `$7378`):
stage B55, which survey 18 shows carries a `$2b48`-entry-63
record (byte 14 = 63), on the slice-13 batch-1 test ROM +
save, 5000f: **`$705f` 66×, `$7369` 8×, `$7378` 2×, all with
bank=10** (frames 1241–1259 and 3554–3557, state 18 timer 6).
Most `$7369` entries return early at `ret nz` (`[$c10c]`
countdown); only two reached `$7378`. B55's record byte 13 is
`$13`, so `$7378` wrote `[$c105]`=`$13` there, not 46 —
consistent with slice 18 (no record has byte 13 in
{`$46`,`$c6`}). Files: `src/bank10slice19.asm` (811 lines);
`tools/gen_slice19.py`.

§4 **Bank-31 `$70df`–`$723d` remainder: carved, entry RESOLVED.**
Slice 17 truncated the `$6a98` `[$c10a]` table at 9 entries
(`$6a98`–`$6aa9`); it is actually **19 entries**
(`$6a98`–`$6abd`): entries 9–18 are `$6ed6`, `$6ffa`, `$704b`,
`$708f`, `$70d0`, `$70df`, `$7161`, `$71bd`, `$7222`, `$722c`
— all increasing, all decoded instruction starts. Entries
10–13 (`$6ffa`/`$704b`/`$708f`/`$70d0`) were carved in slice 18
without noting they are table entries; entries 14–18 are
carved here (`$70df`–`$7144` code: sets `[$c109]` bit 4,
`[$ff93]` bit 5, memcpy `$7145`→`$c1c4`, `[$c10c]`=8,
`[$c10a]`=`$0f`, sound `$4e`, `[$c836]`=`$80`, then a
`$c260`-record scan rewriting `$5d` bytes; `$7161`–`$7211`
code: `[$c868]` toggle + `[$c213]`-record gates, `[$c10a]`=
`$10`/`$11`, sound `$73`, and the `$71bd` countdown branch;
`$7222`–`$722b` and `$722c`–`$723d` countdown tails), plus
entry 9 (`$6ed6`–`$6f88`, sharing the `$6e22` tail with entry 7)
and the memcpy data blobs `$6eba`–`$6ed5` (28 bytes, `ld
hl,$6eba` at `$6e9a`), `$7145`–`$7160` (28 bytes, `ld hl,$7145`
at `$70e9`) and `$7212`–`$7221` (16 bytes, ASCII
"bodyfkhmncpejgkli", 4×4 table indexed by `[$c113]`&3 at
`$71f2`). `tools/gen_slice17.py` TABLES31 entry 91 extended
9 → 19; re-running it changed ONLY the `$6a98` dw block
(verified by `git diff`). The `$79b5` `c2 09 72` byte triple is
NOT a `jp nz,$7209`: it is the tail of `ld bc,$c213` (`$79b3`)
+ `add hl,bc` (`$79b6`) in carved code. Files:
`src/bank31slice19.asm` (329 lines); `src/` now 58,564 lines
(was 55,633). Bank 31 now has only 978 bytes left in 26 small
gaps (largest: `$67f8`–`$68dc`, 228 bytes).

§5 **Door / clear chain: no new lead, no completion attempt
(NO-GO, same as slices 15–17).** None of the slice-19 carves
writes `hStateTimer` (`$ff90`) or a clear-chain timer
(23/26/33/42) — verified by grep over the new files: the
bank-31 routines write only `[$c10a]`/`[$c10c]`/sound IDs
(`$4e`/`$73`/`$03`, and `$80` to `[$c836]`, out of the 41-song
range like slice 16's `$33`/`$80` — role unverified); the
bank-10 routines write `[$c10a]`/`[$c10c]`/sound IDs
(`$3a`/`$3b`/`$42`) and `[$c105]` (the `$7378` rewrite, which
slice 18 already closed as a 46-path: `$7dde[46]`=0 → no-op,
and no record has byte 13 = `$46`/`$c6`). Bank 29 is data.
The door/clear-chain entry is still NOT found.

§6 **What byte-match caught.** Nothing this slice — first
build after all three carves + the `$6a98` table extension
matched on the first try (`rm build/game.gb && make` →
SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` clean).
Two near-misses recorded instead: (a) `gen_banks.py` CARVED
diff vs git was checked BEFORE building (dropped: only the
replaced `(0x6A98, 0x6AAA)`; added: exactly the 16 intended
ranges) — the slice-18 reflow lesson, applied. (b) The
`$7300` seed misaligns by 1 (it is an immediate byte, not
code); seeding `$7297` instead converges the walk. Nacre
regressions on the final build, original vs rebuilt identical:
slice-5 suite ALL IDENTICAL (600f `1cf92679…`, 900f
`39ffd5ee…`, 3600f `88515f4e…`, 12000f `92d2e185…`, s8
`92d2e185…`, f0 `3390d763…`, f1 `1cf92679…` — all match the
slice-17 reference hashes); slice-7 suite ALL IDENTICAL
(retry 15000f `0d835d95…`, mid5000 `2ab1bb5d…`, play-right
`b3cb6c8b…`, death 3000f `632b2eaf…` — all match).
`git status` clean of build artifacts / `.gb` / `.sav` /
binaries / `__pycache__` (probe binaries `tools/gb_bank29` /
`tools/gb_pcwatch` removed after use; only the `.c` sources
remain in `tools/`).

## Slice 20 — DONE, byte-matching (2026-11-24)

§1 **Bank 31 CLOSED — all 26 gaps carved (978 bytes).**
`tools/gen_slice20.py` (`emit_bank31`, `tools/gb_rd.py`
walks seeded only from `call`/`jp`/`jr`/table targets)
carved every remaining gap, verified against ROM bytes:
dw tables `$467f` (5 WRAM pointers `$dcd8,$dce8,$dcc8,
$dcf8,$dcb8`, indexed by 2*`[$c0a4]`), `$4fd3` (3 entries,
routines `$4fd9`–`$503b` contiguous), `$6188` (3 entries,
routines `$618e`–`$61a4`), `$67f8` (4 entries, routines
`$680e`–`$68db` contiguous); 14-byte records `$48c7` (2),
`$4c9c` (4), `$4d8a` (2), `$6152` (2, choice by
`[$c0f8]` bit 0), `$6b53` (2), `$6800` (1 — see §3);
other data `$4f9b`–`$4fb8` (30B blob), `$5407` (7B,
indexed by `[$c705]`), `$5445` (6B, 3x2B, indexed by
SeedMul), `$57a1` (32B, 16x2B pairs), `$6da2` (8B, no
reference found in carved code — plain db), `$6df6`
(4x5B records), `$6e84`–`$6e94` (12B memcpy template +
5B byte table), `$7306` (4x4B records), `$7371`/`$73d1`/
`$7434`/`$74d5` (3B each, SeedMul-indexed), `$775f`
(22B, 11x2B pairs), `$792e` (two 3B tables, choice by
`[$c0f8]` bit 0); code `$7db9`–`$7de3` (seeds `$7db9`,
`$7dcc`), `$7e44`–`$7e7d` (seeds `$7e44`, `$7e61`;
`$7e44` called from bank-0 `$2aaa`, `$7e61` jp'd to
from `$71ba`; includes the `jr $7e72` self-loop), and
`$7f5f` (1-byte `ret` — entry UNVERIFIED, could equally
be the first byte of the `$7f60` table) + the `$7f60`–
`$7fff` 160B 00/01 table (indexed by `[$dd18]`).
Bank 31 CARVED now covers `$4000`–`$8000` with zero
gaps (16,384/16,384 bytes). Files:
`src/bank31slice20.asm` (552 lines).

§2 **Bank 10 (decimal) CLOSED — all 34 gaps carved
(10,344 bytes).** `tools/gen_slice20.py` (`emit_bank10`
+ `emit_bank10_rest`) carved the whole `$480a`–`$705e`
span plus the `$75b0`–`$8000` tail: 19 dw dispatch tables
(`$480a` 16, `$4e56` 8, `$51a1` 2, `$524b` 5, `$534b` 4,
`$5421` 5, `$56b1` 4, `$56fb` 3, `$5894` 4, `$5918` 6,
`$5eca` 15, `$6414` 6, `$65a2` 7, `$67ac` 7, `$69de` 7,
`$6b08` 7, `$6d9a` 7, `$6e62` 7, `$6f66` 16, `$7d0e` 4,
`$7e3c` 10, `$7fb6` 8 signed offsets) — all read by
`$2b48`-entry handlers (`ld a,[$c10a]; add a; ld hl,
$TABLE; …; jp hl`) except `$7e3c` and `$7fb6` (see
below) — plus their routines and the interleaved
14-byte data records (each verified by an `ld hl`/`ld de`
reference from the walked routines), the `$75b0`–`$772f`
record routines (seeds `$75b0,$75c2,$75f7,$7706,$76ef`
plus the ten `$7e3c` entries; `$75c2`/`$75f7` entries
are computed `jp hl` targets from the `$759a` routine —
mechanism noted, not proven), `$789f`–`$7950`
(fall-through from the carved `$787d` routine),
`$79ea`–`$7aa9` + 14B record `$7aaa`, `$7b12`–`$7b3e`
(entry UNVERIFIED), `$7b6c`–`$7c23`, `$7cb0`–`$7d0d`
(reads the `$7d0e` table via `jp hl` and scans the
`$7d16` 72x4B records by `[$c80d]`), and the `$7f44`–
`$7fff` tail (padding + `$7fb6` offset table + byte
tables). Table entry counts were fixed by the partition
test (first entry == table base + 2*N, walk covers
[first entry, next carved range) exactly apart from the
noted data records). Two generator fixes during the
run: the `$6e70` carve missed `$6e95`–`$6e9c` because
`$6e95` is itself a `$6e62`-table entry (entry 3:
`ld hl,$c10c; dec [hl]; ret nz; …` flowing through
`$6ecc`) — seeded it; the `$7043` carve missed
`$7059`–`$705e` because `$7059` is a `$6f66`-table
entry (entry 2: `ld de,$00a0; jp $4a19`) — seeded it.
Bank 10 CARVED now covers `$4000`–`$8000` with zero
gaps (16,384/16,384 bytes). Files:
`src/bank10slice20.asm` (6,154 lines); `src/` now
65,092 lines (was 58,564 after slice 19).

§3 **What the byte-match check caught.** The first
build failed: SHA-1 `fa4b0ed6…`, `cmp` 24 differing
bytes. Three data pockets between a dw table and its
first routine had been missed in the survey (the
routines start after them, no jump targets them):
bank 10 `$5353`–`$535a` and `$56b9`–`$56c0` (both
`00 00 00 00 88 5e 97 5e`, no `ld hl`/call/jp reference
found in carved code — plain db) and bank 31
`$6800`–`$680d` (14-byte record `98 a0 e8 f0 e8 a0 98
f0 e8 f0 e8 a0 98 f0`, same repeating shape as the
other 14-byte records in the bank; `ld hl,$6800` at
`$446f` and `$67ca`, slice 17). All three added to
`tools/gen_slice20.py` as `emit_db`; rebuild matched
on the first try (`rm build/game.gb && make` →
SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`,
`cmp` clean). `tools/gen_banks.py` CARVED diff vs git
was checked BEFORE building (60 tuples added by
insertion only, 0 dropped — the slice-18 lesson,
applied; one splice case where the new tuple's
predecessor shared its line with the list's closing
`],`, handled by appending before the bracket).
`src/banks.asm` regenerated (180 INCBIN lines removed).
Nacre regressions on the final build, original vs
rebuilt identical: slice-5 suite ALL IDENTICAL (600f
`1cf92679…`, 900f `39ffd5ee…`, 3600f `88515f4e…`,
12000f `92d2e185…`, s8 `92d2e185…`, f0 `3390d763…`,
f1 `1cf92679…` — all match the slice-19 reference
hashes); slice-7 suite ALL IDENTICAL (retry 15000f
`0d835d95…`, mid5000 `2ab1bb5d…`, play-right
`b3cb6c8b…`, death 3000f `632b2eaf…` — all match).
`git status` clean of build artifacts / `.gb` / `.sav` /
binaries / `__pycache__` (only `.c` sources in `tools/`).

§4 **Door / clear-chain entry: still NOT found (NO-GO,
no new door lead).** No `ldh [$ff90],a` (hStateTimer)
write exists anywhere in the new carves, and no
reference to bank-1 `$56c3` (the inferred door path's
timer-26 setter). The four `ld [$c105],a` writes in
the new carves set states `$53` (83, at `$6274`),
`$37` (55, at `$632c`), `$21` (33, at `$7661`) and
`$36` (54, at `$7708`) — none is 46, consistent with
slice 18's DEAD 91→46 link. Note the trap, recorded
so it is not re-run as a lead: `$7651`'s `$21` is a
**`$c105` state** write, NOT timer 33 — timer 33 is
`$ff90`=`$21`, set only at bank-0 `$09b4`/`$09eb`
(slice 13 §4). `$7651` is a `$7e3c`-table entry (index
6), reached from `$7329` (`jp z,$7651`, slice 19's
`$7073`-region carve); it sets `[$c10a]`=1,
`[$c10f]`=1 and calls `$7c88`. No completion attempt
was run. Unresolved from this slice (inferred, not
verified): the `$7e3c` table's own reader (no
`ld hl,$7e3c` found in carved bank-10 code — the
`$7e3c` hit in `src/bank10slice19.asm` is hex bank 16,
a different bank); the `$7f5f` ret / `$4fff` / `$5212` /
`$7b12` routine entries (unverified); the `$703d`
6-byte data, `$5167` 3x14B records and `$7aaa` 14B
record have no `ld hl` reference in carved code.

## Slice 21 — DONE, byte-matching (2026-11-24)

§1 **Bank 9 CLOSED — all gaps carved except the `$ff` tail.**
`tools/gen_slice21.py` (walk: 7,356 instrs from 68 seeds, 0 `rst $08`
sites) carved every remaining gap; bank 9 CARVED now covers
`$4000`–`$6fab`, and the only remaining INCBIN is `$6fac`–`$8000`
(4,180 bytes, all `$ff` — the bank's last non-`$ff` byte is at
`$6fa7`). Files: `src/bank9slice21.asm` (5,971 lines);
`src/` now 71,189 lines (was 65,092 after slice 20).

**The `$4000` dispatch table is 197 entries, not 16 — slice 9
CORRECTED.** The `$4021`–`$418a` bytes slice 9 called data
("decodes as garbage") are the table's continuation, entries
16–196 (`$4001`–`$418a`, A = record byte1 − `$30`, bank-0 `$0bff`
dispatches any byte1 ≥ `$30`). Non-noop entries: 0 `$418b`, 1
`$41f2`, 2 `$4259`, 3 `$4292`, 4 `$4657`, 5 `$42cb`, 7 `$46a4`,
12 `$432b`, 13 `$439c`, 14 `$440d`, 15 `$444d`, 16 `$448d`, 18
`$44ed`, 19 `$4592`, 20 `$4635`, 24 `$46dc`, 35 `$46dc`, 39
`$4784`, 41 `$47c2`, 42 `$492e`, 44 `$4955`, 45 `$4691`, 64
`$49d7`, 65 `$4a92`, 74 `$4b52`, 76 `$4f15`, 103 `$4fbd`, 104
`$5044`, 105 `$5174`, 106 `$5251`, 107 `$533c`, 108 `$541d`, 109
`$5507`, 112 `$55e8`, 114 `$582e`, 117 `$5a04`, 118 `$5a49`, 119
`$5a8e`, 120 `$5ad3`, 178 `$5b18`, 179 `$5bf3`, 180 `$5cce`, 181
`$5ea1`, 185 `$4fbd`, 187 `$6021`, 188 `$6066`, 189 `$60ab`, 190
`$60f0`, 191 `$6139`, 196 `$63b1`; all other entries are `$1d29`
(bank-0 `ret`, a no-op). The table ends at `$418a` because `$418b`
is entry 0's routine start (partition test).
`tools/gen_slice9_bank9.py` updated (TABLE9 now built from the ROM,
197 words, each asserted `$1d29` or `$4000`–`$7fff`, spot-checked
0=`$418b`/16=`$448d`/196=`$63b1`); `src/bank9.asm` regenerated —
diff is header comments + 181 added `dw` lines only. **The
`$448d`/`$44ed`/`$4592`/`$4635` entry mechanism is RESOLVED:** they
are table entries 16/18/19/20, not orphans (slice 9's "no direct
caller" is closed by the table itself).

**Handlers `$4691`–`$63f2`** (all 50 table targets + callees):
`$4691`–`$48df` (entries 45 `$4691`, 24/35 `$46dc`, 7 `$46a4` —
entry 7's routine was never emitted by slice 9: its span ended at
`$4691` and `$46a4` sits past that boundary; the `$4691` boundary
is clean — `$468e` is `jp $169c`, `$4691` starts `call $63f3`),
`$492e`–`$49a0` (42), `$49d7`–`$4b4d` (64/65), `$4b52`–`$5a02`
(74/76/103/104/105/106/107/108/109/112/114), `$5a04`–`$63f2`
(117/118/119/120/178/179/180/181/187/188/189/190/191/196).
Data pockets, all `ld hl`-referenced (never code): `$48e0`–`$492d`
(read by `$4823`), `$49a1`–`$49d6` (read by `$4972`), `$4b4e`–
`$4b51` (read by `$4b6c`, 4 bytes `$f0 $f0 $96 $96`), `$6e63`–
`$6e69` (read by `$6e41`, 7 bytes `$a8 $f8 $a8 $f8 $a8 $a8 $f8`),
`$64cb`–`$6573` (169-byte opaque blob — no pointer to it anywhere
in the ROM; opens `06 00 8a ff 86 ff 8a ff`, then 7-byte groups, then
`($xx $82)` pairs), `$6d59`–`$6d5a` + `$6d6b`–`$6d6c` (`00 00`
padding), `$5a03` (1-byte `ret`, entry UNVERIFIED, same class as
`$6f9b`).

**The `$264a` pocket's entry is RESOLVED.** The `$6182`–`$63b1`
routines (`$6182`, `$61f4`, `$6266`, `$62cd`, `$6308`, `$636f`, all
record-builders ending `call $6485; jp $648b`, plus internal
16-byte copy loops `$61e9`/`$625b`) have no `call`/`jp` to them
anywhere in the ROM — but bank-0 `$264a` (already carved,
`src/decomp.asm`, the bank-9 level dispatch) `jp z`'s to all six
on `[$c725]` (7→`$62cd`, `$18`→`$6308`, `$27`→`$636f`, 0→`$6182`,
`$0c`→`$61f4`, `$23`→`$6266`). The entry mechanism was in carved
code all along; the slice-21 walk just had to seed from it.

**Helpers:** `$6402`–`$6411` (HL = `$c200` + `[$c70d]`*16, the
`$c200` analogue of `$63f3` — no caller found, entry UNVERIFIED),
`$6412`–`$643d` (push-bc pointer/bit routine, entry UNVERIFIED),
`$643e`–`$644a` (clear one byte at `$c0a6`+idx, entry UNVERIFIED),
`$644b`–`$647f` (`jp`'d to from `$5a46`/`$5a8b`/`$5ad0`/`$5b15`/
`$6063`/`$60a8`/`$60ed`), `$6485`–`$648a` (`inc [$da4a]` ×2;
called from `$61e3`/`$6255`), `$648b`–`$648f` (`inc [$da46]`;
`jp`'d to from the six pocket tails).

**`$2b48`-entry-89 region tails** (the slice-17 walk left each
span a few bytes short; all walk-covered routine continuations):
`$6962`–`$696a`, `$699a`–`$69ab`, `$6a08`–`$6a10`, `$6a40`–`$6a52`,
`$6a7d`–`$6a9b`, `$6ac8`–`$6ae6`, `$6b43`–`$6b4b`, `$6b7b`–`$6b8c`,
`$6be9`–`$6bf1`, `$6c21`–`$6c33`, `$6c5f`–`$6c7d`, `$6caa`–`$6cb6`.

**The `$6eb1` family, entry-UNVERIFIED:** `$6e94`–`$6eb0` (c=`$08`
scan variant), `$6ed9`–`$6f0b` (c=`$03`), `$6f0c`–`$6f33` (c=`$07`,
falls through to `$6f34`), `$6f65`–`$6f9a` (position-check helper),
`$6d6d`–`$6d8a` (the `$6d47` word's routine). All decode cleanly
and belong to the called `$6eb1` family, but no `call`/`jp` to any
of them exists anywhere in the ROM (whole-ROM byte search, zero
hits each), so all five are carved as code with entry UNVERIFIED
(same class as slice 18's `$684f`/`$6893`/`$68d7`).

**`$664a`/`$6d33` tables are 10 entries, not 8 — slice 17
CORRECTED.** Evidence: the `[$c10a]` writers in the carved bank-9
routines max out at 9 (`$6b63` writes 9; the `$6696` remap outputs
max 9), and the words at `$665a`–`$665d` / `$6d43`–`$6d46` are
`$684f`/`$6893` — the slice-18 map-sample routines, the same
family as the table routines. Both tables' readers index by
`[$c10a]`*2 with no bounds check (`$6642`/`$6d27`), so entries
8/9 are live. `tools/gen_slice17.py` updated (TABLES9 extended,
`$684f`/`$6893` added as walk seeds) and re-run — diff is only
the two table sections (bank-31/bank-0 files byte-identical).
The trailing words `$665e` (`$68d7`) and `$6d47` (`$6d6d`) are
NOT claimed as entry 10: no `[$c10a]`=10 writer exists in carved
code, so `$68d7`/`$6d6d` stay entry-UNVERIFIED (emitted as single
`dw` with that note). The 11-entry alternative stays open — a
live `[$c10a]` watch during a `$6574`/`$6cce` dispatch could
settle it.

§2 **Byte-match proof.** Clean `make` (`rm build/game.gb` first)
rebuilds SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero
diffs vs `roms/Donkey_Kong_World_Rev1_SGB.gb` — **first try, no
build failures.** `tools/gen_banks.py` CARVED diff vs git was
checked BEFORE building (36 tuples added by insertion only, 0
dropped — the slice-18 lesson, applied; the `(0x4000,0x4021)`
tuple was left untouched and `(0x4021,0x418B)` added beside it).
`src/banks.asm` regenerated (68 INCBIN lines left; bank 9's only
one is `$6fac`–`$7fff`). `git status` clean of build artifacts /
`.gb` / `.sav` / binaries / `__pycache__` (only `.py`/`.asm`
sources changed/added).

§3 **Door / clear-chain entry: still NOT found (NO-GO, no new door
lead).** Zero `ldh [$ff90],a` (hStateTimer) writes and zero
`[$c105]` writes in the whole new carve (grep over the 7,356-instr
walk — `tools/survey21_coverage.py`). No handler in bank 9 writes
a clear-chain timer (23/26/33/42), and no reference to bank-1
`$56c3` (the inferred door path's timer-26 setter). No completion
attempt was run. Two new open notes from this slice (inferred, not
verified): (a) the `$4000` table covers A 0–196, but bank-0 `$0bff`
dispatches any record byte1 ≥ `$30`, i.e. A up to 207 — A 197–207
would read handler bytes (`$418b`+ as `dw`) as table entries, which
is undefined behavior in the original ROM; whether record byte1 can
reach `$f5`+ live is unverified. (b) The `$68d7`/`$6d6d` entry
question above (11-entry alternative).

§4 **Nacre results.** `tools/run_slice5_regression.sh` and
`tools/run_slice7_cases.sh` on the final build, original vs rebuilt
identical in every case (framebuffer hash + state trace + save):
slice-5 suite ALL IDENTICAL (600f `1cf92679…`, 900f `39ffd5ee…`,
3600f `88515f4e…`, 12000f `92d2e185…`, s8 `92d2e185…`, f0
`3390d763…`, f1 `1cf92679…` — all match the slice-19/20 reference
hashes); slice-7 suite ALL IDENTICAL (retry 15000f `0d835d95…`,
mid5000 `2ab1bb5d…`, play-right `b3cb6c8b…`, death 3000f
`632b2eaf…` — all match).

§5 **Verified vs inferred.** VERIFIED: the 197-entry `$4000`
table (ROM bytes + partition test at `$418b` + spot checks);
`$448d`/`$44ed`/`$4592`/`$4635` as table entries 16/18/19/20;
the `$264a` pocket entry (bank-0 `$264a` `jp z` targets, already
carved); the `$664a`/`$6d33` 10-entry extent (max written
`[$c10a]` = 9 across all carved bank-9 routines + `$6696` remap
outputs); the `$48e0`/`$49a1`/`$4b4e`/`$6e63` data pockets (`ld
hl` references inside neighboring routines); the `$644b`/`$6485`/
`$648b` entries (`jp`/`call` sites in the new carve); byte-match
+ both regression suites on the final build. INFERRED (not
verified): the `$68d7`/`$6d6d` non-entry-10 verdict (rests on "no
`[$c10a]`=10 writer in carved code" — a spawn path outside bank 9
could still set 10); the `$64cb` blob's internal structure; the
`$48e0`/`$49a1` table record structures (emitted as plain `db`);
the entry mechanisms of `$6402`/`$6412`/`$643e`/`$6e94`/`$6ed9`/
`$6f0c`/`$6f65`/`$6d6d`/`$5a03` (clean decodes, zero callers found);
whether record byte1 can reach `$f5`+ live (the A 197–207 hole).

§6 **What the next slice should do.** Bank 9 alone filled this
slice, so the next bank is slice 22's job — **bank 4 first, not
bank 6.** Justification (surveyed this slice): bank 4 has two
concrete bank-0 entry points (`$2d2d` → `ld hl,$5f30`, `$356f` →
`ld hl,$67b0`, both after `ld a,$04; rst $10`, both 128-byte VRAM
copies via `$106e` — bank 4 is graphics/table data with known
readers, last non-`$ff` at `$76af`). Bank 6 is the run-1 stage
data (35 stage pointers from the bank-5 table, `$4000`–`$71a1`,
last non-`$ff` at `$7364`) — compressed level data that slice 4
already decided stays INCBIN as data, so carving it is mostly
emitting `db` with little new mechanism. Bank 4's `$5f30`/`$67b0`
copies (what tiles, for which screens) are the concrete next
question; bank 6 follows after. Also open: the `$68d7`/`$6d6d`
11-entry question (live `[$c10a]` watch) and the A 197–207 hole
(live record-byte1 values).

## Slice 22 — DONE, byte-matching (2026-11-24)

§1 **Bank 4 CLOSED — tile graphics data, not code.** `src/` now 72,096
lines (was 71,189 after slice 21). New files `src/bank4.asm` (906
lines, 875 tiles), `tools/gen_slice22.py`, `tools/survey22_bank4.py`.

**Survey (reproducible: `python3 tools/survey22_bank4.py`).** Bank 4 is
2bpp tile data, $4000-$76af = 14,000 bytes = 875 tiles of 16 bytes;
last non-`$ff` byte at `$76af`, `$76b0-$7fff` all `$ff` padding (stays
INCBIN). Evidence:
- Only two `ld a,$04; rst $10` sites exist in the whole ROM, both in
  bank 0, and both use bank 4 purely as a copy source, never as code.
  No `call`/`jp`/`jr`/table target into bank 4 exists anywhere; both
  mappings are transient copy windows (bank restored immediately
  after), so no bank-4 byte can ever execute. The immediate-bank
  survey (whole ROM: `ld a,imm; rst $10` sites) selects bank 4
  exactly twice; the 882 other `rst $10` bytes are mostly data
  (the `pop af; rst $10` bank-restores excepted, which restore the
  previously mapped bank and can never introduce bank 4).
- The bytes are tiles: `$4000` starts with a blank tile, then clean
  glyphs (tiles 1-7 render as digit shapes 0/1/2/3/4/5/6); `$5f30`
  and `$67b0` are 16-byte aligned (tiles 499 and 635). Opcode counts
  per 4 KiB are at noise level (ret 0-6, call 0-1, jp 0-6, no `jp
  (hl)`); `gb_rd` walks from `$4000`/`$5f30`/`$67b0` hit invalid
  opcodes (`$fc`/`$10`) within 102-1,393 instructions — linear
  decode of tile bytes, not code.
- **CORRECTIONS to the slice-22 task brief.** `$106e` is MemcpyC
  (copy C bytes), not MemcpyBC; and `$356f` is NOT a 128-byte copy
  via `$106e`: `LoadTilesFromBank4` (`$356f`, called from bank-1
  `$4e20`) does HL=`$67b0`, DE=`$8000`, BC=`$0300`, `call MemcpyBC`
  — 768 bytes = 48 tiles to VRAM `$8000`. Only the `$2d2d` copy is
  128 bytes via `$106e` (routine `$2cc1`, called from bank-0
  `$0e72`: HL=`$5f30`, DE=`$8480`, C=`$80`, `call $106e` — 8 tiles
  to VRAM `$8480`).
- The `$1832`-handler `ld hl,$5f30` sites (bank-0
  `$18aa`/`$1965`/`$198e`/`$1b72`) only STORE the address `$5f30`
  into the `$da71` pointer table (`$18cf` writes HL as a 16-bit
  value, it does not dereference it); which bank is mapped when
  that pointer is consumed is unresolved, and the `$10dd` consumer
  maps bank `$0b`/`$1d`, so those are NOT claimed as bank-4 reads.
  The only proven bank-4 reads are the two VRAM copies above.

**Carve.** `src/bank4.asm` emits `$4000-$76af` as `db`, one 16-byte
tile per line with a tile-number comment, split into five sections
at the two proven copy sources (`Bank4_Tiles_5F30`,
`Bank4_Tiles_67B0` labels on the 128-byte and 768-byte blocks).
No code is claimed anywhere in the bank. `tools/gen_banks.py`
CARVED gained `4: [(0x4000, 0x76B0)]` — diff checked BEFORE building
(insertion only, 0 dropped); `src/banks.asm` regenerated (bank 4's
only remaining INCBIN is the `$76b0-$7fff` `$ff` tail);
`INCLUDE "bank4.asm"` added to `src/main.asm`. What the byte-match
check caught: the generator's own assertion caught an arithmetic
slip in its docstring before any build ran (14,000 bytes = 875
tiles, not 14,256/891).

§2 **The `$68d7`/`$6d6d` 11-entry question — SETTLED live (slice 21
CORRECTED).** Slice 21 said the `$664a`/`$6d33` tables are 10 entries
because no `[$c10a]`=10 writer exists in carved code. That is now
overturned: `[$c10a]` DOES reach 10 live.
- `tools/gb_watch … c10a=0a`: 0 hits in 6000f of 1-1 gameplay
  (progress-1 save, Start+A+A); **3 hits in the 30000f idle attract
  run** (frames 7720, 25053, 25061, all state 18 timer 6).
- Pass-2 refine of frame 7720: the writer is bank-0 `$2a39`
  (`ld [de],a` in the `$2a38` 32-byte copy loop that copies a `$c200`
  record to `$c0f7` — `[$c10a]` is the record's byte 19). The value
  10 comes from stage data via that copy, not from any carved bank-9
  routine — which is why slice 21's carved-code writer search found
  nothing. At the write, HL=`$c234` (source byte `$c233`, record 1
  byte 19), A=`$0a`.
- The readers (`$6642`/`$6d27`) index by `[$c10a]`*2 with no bounds
  check (slice 21), and both trailing words are real routine starts
  with identical prologues (`ld hl,$c112; ld a,$10; ld [hl+],a; …`,
  `$68d7` in slice 18's `$684f` carve, `$6d6d` in slice 21). So the
  tables are **11 entries**, entry 10 = `$68d7` / `$6d6d`. Remaining
  gap (small): no direct observation of the entry-10 jump itself —
  that would need a PC watch on the `$6642`/`$6d27` dispatch; the
  live value + unbounded index + routine starts is the evidence.

§3 **Record byte1 `$f5`+ — SETTLED for sampled flows (slice 21's A
197-207 hole).** `tools/gb_wramdump` scans of `$db15` byte1 (32
records, dumps in `build/nacre-test/slice22/play/`):
- 1-1 run (6000f, progress-1 save, dumps every 500f): max byte1 =
  `$00` — `$db15` records are all zero in 1-1, as slice 9 found.
- Idle attract run (30000f, dumps every 1000f): genuine record
  byte1s max at `$b0` (176 → A = 128, inside the 197-entry table);
  values seen {`$42`, `$59`, `$5a`, `$5e`, `$7f`, `$b0`} (frames
  13000/14000/17000, state 18 timer 8).
- The only byte1 values ≥ `$f5` are the `$ff` fill at frame 16000
  (state 18, timer 29): 508 of the 512 `$db15-$dd14` bytes are `$ff`
  (only records 3/12 keep real byte1s, `$b0`/`$7f`) — a transient
  fill, not record data. And `$0bff`'s only caller chain is `$0862`
  ← `$0841` (a state-16 timer step: `$083e` IncStateTimer, `call
  $0862`, `jp $1528`), so the fill in state 18 is never dispatched
  on. **Verdict: the A 197-207 hole is not reachable via live
  records in the sampled flows** (1-1 + 30000f attract) — stated
  for those flows, not as a universal impossibility.

§4 **Door / clear-chain entry: still NOT found (NO-GO, no new door
lead).** Bank 4 has no code, so it writes no hStateTimer (`$ff90`)
and no `[$c105]`; nothing in this slice touches the clear chain.
No completion attempt was run (same NO-GO as slices 15-21). Slice
22's contribution to the door hunt is the two slice-21 notes closed
above (§2/§3), not a new lead.

§5 **Byte-match proof.** Clean `make` (`rm build/game.gb` first)
rebuilds SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero
diffs vs `roms/Donkey_Kong_World_Rev1_SGB.gb` — **first try, no
build failures.** `git status` clean of build artifacts / `.gb` /
`.sav` / binaries / `__pycache__` (only `.py`/`.asm` sources
changed/added).

§6 **Nacre results.** `tools/run_slice5_regression.sh` and
`tools/run_slice7_cases.sh` on the final build, original vs rebuilt
identical in every case (framebuffer hash + state trace + save):
slice-5 suite ALL IDENTICAL (600f `1cf92679…`, 900f `39ffd5ee…`,
3600f `88515f4e…`, 12000f `92d2e185…`, s8 `92d2e185…`, f0
`3390d763…`, f1 `1cf92679…` — all match the slice-19/20/21
reference hashes); slice-7 suite ALL IDENTICAL (retry 15000f
`0d835d95…`, mid5000 `2ab1bb5d…`, play-right `b3cb6c8b…`, death
3000f `632b2eaf…` — all match).

§7 **Verified vs inferred.** VERIFIED: bank 4 is tile data (survey
numbers above + the two VRAM-copy readers + zero code entries);
the `$356f` 768-byte / `$2d2d` 128-byte copy facts (ROM bytes +
carved callers); `[$c10a]` reaches 10 live (3 hits, writer pinned
to bank-0 `$2a39` by cycle-step refine); genuine `$db15` byte1s
max `$b0` in sampled flows; byte-match + both regression suites on
the final build. INFERRED (not verified): the entry-10 dispatch
jump itself was not directly observed (live value + unbounded
index + routine starts is the evidence); which bank's `$5f30` the
`$1832`-stored pointers address when dereferenced; the `$ff` fill
at frame 16000's writer (transient, state 18 timer 29 — not
traced); bank 4's internal tile-set boundaries (no clean split
found in the zero%/distinct profile; emitted as one run split
only at the two proven copy sources).

§8 **What the next slice should do.** Bank 4 filled this slice, so
the next bank is slice 23's job — **bank 15 first.** Justification
(surveyed this slice): bank 15 has the clearest entry of the
13/14/15 set — bank-0 `$1d82` `TransferTable0F` (slice 2) selects
bank `$0f` and reads its `$4000` table, a known reader with known
table semantics — and the highest code-like opcode density of the
three (whole-bank ret 22 / call 18 / `jp (hl)` 19 / `rst $08` 23,
vs 13: 3/5/6/25 and 14: 2/5/5/19), so it may hold code as well as
tables. Banks 13/14 are level-data streams (bank 13 selected at
bank-0 `$24a2`, then bytes read via HL into the `$257f`
decompressor; bank 14 at `$2477`, a byte read as a bank number then
bank-12 `$4a3e`) with no table structure — mostly `db` when their
turn comes. Bank 6 stays after them (run-1 stage data, slice 4's
decision: stays INCBIN as data).

## Slice 23 — DONE, byte-matching (2026-11-24)

§1 **Banks 15, 13, and 14 CLOSED — all transfer/stream data, no
code.** `src/` now 75,209 lines (was 72,096 after slice 22).
New files `src/bank15.asm` (1,256 lines, 12,229 bytes),
`src/bank13.asm` (567 lines, 8,975 bytes), `src/bank14.asm`
(1,287 lines, 16,292 bytes); `tools/gen_slice23.py`,
`tools/survey23_bank15.py`, `tools/survey23_banks1314.py`.
Curated: 194,287 / 524,288 bytes (37.1%, was 29.9%).

**Bank 15 — the `$4000` table, carved first.** `tools/
survey23_bank15.py` reproduces the numbers. The bank has
exactly ONE entry point in the whole ROM: bank-0 `$1d82`
`TransferTable0F` (slice 2) is the only `ld a,$0f; rst $10`
site anywhere. It maps bank `$0f`, reads the `$4000` table
at A*2, follows the block pointer, and for each of the
block's count sub-pointers calls `$16c2` `FrameCopy16c2`
(bank 0, already carved). No `call`/`jp`/`jr`/table target
into bank 15 exists anywhere else, so no bank-15 byte can
ever execute. The table is **74 entries** (dw, `$4000`–
`$4093`): entry 74 would read `$4094`, which is block
8/15/31's start (count byte `$01`, then `dw $4097`) — the
partition test, same pattern as slice 21's bank-9 `$418b`
boundary. 58 distinct blocks (`[count][count x dw
sub-pointer]`), 105 distinct sub-specs: 6-byte `$16c2`
headers `[dst lo, dst hi, B=rows, C=cols, src lo, src hi]`
— B rows × C bytes copied from src, dst advancing `$20`
per row (VRAM tilemap stride). Zero fill specs (D==0 never
occurs). Two specs copy FROM VRAM instead of ROM: `$48c4`
(dst `$9b80`, src `$9a20`, 1×32) and `$56bb` (dst `$9a40`,
src `$98a0`, 7×32) — tilemap-to-tilemap copies, no ROM data
span. The union of table + blocks + headers + src data
spans covers `$4000`–`$6fc4` with **zero gaps** (12,229
bytes); shared blocks (e.g. `$40c8` for entries 1–7 and 9)
and shared data spans are the same bytes, never
conflicting owners. Last non-`$ff` byte at `$6fc4`;
`$6fc5`–`$7fff` all `$ff` padding (stays INCBIN). The
opcode-density counts that made bank 15 look code-like
(whole-bank ret 22 / call 18 / `jp (hl)` 19) are data
bytes: the `$4000`–`$5fff` windows hold all of them,
`$6000`–`$6fff` holds none, and a `gb_rd` walk from the
sub-targets "succeeds" (11,993 instrs) only by decoding
tilemap data as instructions. Known literal
`TransferTable0F` indices (`ld a,imm` before `call $1d82`):
`$09`/`$0a`/`$0b`/`$0c`/`$0d`/`$0e`/`$1d`/`$1e`/`$20`/`$21`/
`$23`/`$3f` (bank 0/1/12); other callers pass A from a
register. All < 74, inside the table. The carve emits the
table as `dw` lines (symbolic, one label per distinct
block), each block as a count byte + `dw` lines (one label
per distinct spec), each spec header as a 6-byte `db` line
with dst/rows/cols/src decoded in a comment, and the src
data as plain `db` lines. No code is claimed anywhere in
the bank.

**Banks 13/14 — the fill (bank 15 closed on the first
build).** `tools/survey23_banks1314.py` reproduces the
numbers. Each has exactly ONE `ld a,$xx; rst $10` site in
the whole ROM, both inside bank-0 `$2470` (the stream
routine): bank 13 at `$24a2` (B in `[$80,$af)`,
decompressor input via `$257f`), bank 14 at `$2477`
(H >= `$7e`, the `$7e00` record table). Opcode counts at
noise level; `gb_rd` walks from `$4000` derail in 11
(bank 13) / 7 (bank 14) instructions. Bank 13:
`$4000`–`$630e` stream data as plain `db`, `$630f`–`$7fff`
`$ff` padding (stays INCBIN). Bank 14: `$4000`–`$7dff`
stream data as plain `db`, then `$7e00`–`$7fa3` a
**140-entry table of 3-byte records `[bank][ptr lo][ptr
hi]`**, all 140 plausible at alignment `$7e00` and zero at
`$7e01`/`$7e02` — the table `$2470` reads (record banks
{`$13`,`$14`,`$15`,`$16`,`$18`}, ptrs `$4000`–`$7c7c`),
emitted as structured `db bank` / `dw ptr` lines;
`$7fa4`–`$7fff` `$ff` padding (stays INCBIN). Bank 14's
low region shares bank 13's 16-byte opening (`81 81 42 42
24 24 18 18…`) but is otherwise different bytes (only
6,592/15,872 identical). **Honest gap:** no reader was
found for bank 14's `$4000`–`$7dff` region — the only
bank-14 mapping is the transient `$2470` one, gated on
H >= `$7e`, and the record banks never include `$0e` —
so it is carved as plain `db` with the reader unknown,
not papered over with a claimed consumer.

§2 **Byte-match proof.** Clean `make` (`rm build/game.gb`
first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs
vs `roms/Donkey_Kong_World_Rev1_SGB.gb` — **first try, no
build failures, for the bank-15-only build and again for
the final three-bank build.** `tools/gen_banks.py` CARVED
diff checked BEFORE each build (3 tuples added total,
insertion only, 0 dropped). `src/banks.asm` regenerated
(68 INCBIN lines left — each closed bank keeps only its
`$ff` tail as INCBIN). `git status` clean of build
artifacts / `.gb` / `.sav` / binaries / `__pycache__`
(only `.py`/`.asm` sources changed/added). One generator
bug caught by its own run before any build: `emit_db_bank`
referenced `rom` without taking it as a parameter
(`NameError`); fixed by passing it in.

§3 **Door / clear-chain entry: still NOT found (NO-GO, no new
door lead).** Banks 13/14/15 contain no code, so they write
no hStateTimer (`$ff90`) and no `[$c105]`; nothing in this
slice touches the clear chain. No completion attempt was
run (same NO-GO as slices 15–22).

§4 **Nacre results.** `tools/run_slice5_regression.sh` and
`tools/run_slice7_cases.sh` on the final build, original vs
rebuilt identical in every case (framebuffer hash + state
trace + save): slice-5 suite ALL IDENTICAL (600f
`1cf92679…`, 900f `39ffd5ee…`, 3600f `88515f4e…`, 12000f
`92d2e185…`, s8 `92d2e185…`, f0 `3390d763…`, f1 `1cf92679…`
— all match the slice-19/20/21/22 reference hashes);
slice-7 suite ALL IDENTICAL (retry 15000f `0d835d95…`,
mid5000 `2ab1bb5d…`, play-right `b3cb6c8b…`, death 3000f
`632b2eaf…` — all match).

§5 **Verified vs inferred.** VERIFIED: bank 15's 74-entry
table extent (partition test at `$4094`); the 58-block /
105-spec structure (every pointer in-bank, every count
1–9, zero-gap union coverage `$4000`–`$6fc4`); the two
VRAM-src specs (`$48c4`/`$56bb`); the single-entry-point
facts for all three banks (whole-ROM `ld a,$xx; rst $10`
surveys: one site each); bank 14's 140-record table
(140/140 plausible at one alignment, 0/140 at the other
two); byte-match + both regression suites on the final
build. INFERRED (not verified): bank 13/14's `$4000`+
regions are decompressor/stream data (reader + content
shape, no per-stream boundaries established — emitted as
plain `db`, no stream starts claimed); bank 14's
`$4000`–`$7dff` reader is unknown (no reader found, stated
as a gap, not a claim); the `$16c2` "rows × cols" reading
of B/C (from the carved bank-0 routine, not from a live
transfer watch).

§6 **What the next slice should do.** Banks 13/14/15 are
closed, so the next bank is slice 24's job — **bank 6
first** (run-1 stage data, 35 stage pointers from the
bank-5 table, `$4000`–`$71a1`, last non-`$ff` at `$7364`;
slice 4's decision stands: mostly `db`, compressed level
data with the 5-byte header + RLE + LZ + patch-list shape
— carve it as structured `db` if the header/record
boundaries can be pinned, plain `db` if not). Then banks
17, 19–22, 25–28, 30, by whatever the `$2b48` handler /
stage-table dependencies point at. The door hunt's open
item is unchanged: the clear chain's ENTRY (timer 33/42)
and the parasol collection (hand-written schedule).

## Slice 24 — DONE, byte-matching (2026-11-24)

§1 **Eleven banks CLOSED — all data, no code.** `src/` now 86,569
lines (was 75,209 after slice 23). Curated: 344,932 / 524,288
bytes (65.8%, was 37.1%) — this slice alone adds 150,645 bytes.
New files `src/bank6.asm` (947 lines, 13,157 bytes),
`src/bank17.asm` (751 lines, 10,736 bytes), `src/bank19.asm`
(960 lines, 15,232 bytes), `src/bank20.asm` (964 lines, 15,290
bytes), `src/bank21.asm` (930 lines, 14,737 bytes),
`src/bank22.asm` (1,017 lines, 16,140 bytes), `src/bank25.asm`
(647 lines, 10,210 bytes), `src/bank26.asm` (782 lines, 12,381
bytes), `src/bank27.asm` (1,280 lines, 16,041 bytes),
`src/bank28.asm` (876 lines, 11,335 bytes), `src/bank30.asm`
(2,195 lines, 15,386 bytes); `tools/gen_slice24.py`,
`tools/survey24_bank6.py`, `tools/survey24_bank17.py`,
`tools/survey24_banks1922.py`, `tools/survey24_banks2530.py`,
`tools/survey24_bank27.py`, `tools/survey24_bank28.py`.
Banks closed so far (18): 4, 6, 9, 10, 13, 14, 15, 17, 19, 20,
21, 22, 25, 26, 27, 28, 30, 31. Each closed bank keeps only its
`$ff` tail as INCBIN (68 INCBIN lines left in `src/banks.asm`).

**Bank 6 — run-1 stage data, $4000-$7364.** `tools/
survey24_bank6.py` reproduces the numbers. Stages 45–79 from
the bank-5 pointer table (slice 4); the 35 starts tile the bank
contiguously (sizes 213–555 bytes), stage 79 ($71a1) running 451
bytes to the last non-`$ff` byte at $7364 ($00); $7365–$7fff
all `$ff` padding (stays INCBIN). The ONLY `ld a,$06; rst $10`
site in the whole ROM is bank-0 $2615, inside SwitchBankByE
($2611: E < $2d → ret, else bank 6; E >= $50 → bank $12) — bank
6 is reached only via LoadStage ($24e7) → SwitchBankByE, as
decompressor input; no bank-6 byte can ever execute. `gb_rd`
walk from $4000 derails in 101 instructions; dw values pointing
in-bank are 1,304/16,383 (~8%, below the ~25% random rate), so
no embedded pointer table. The 5-byte stage header is VERIFIED
from LoadStage itself: after mapping the stage bank it reads 5
bytes from the stage start into [$c705], [$da45], [$da4b],
[$c711], [$c712] in order ($2516–$2527), and only then is the
rest decompressed. Header value sets across the 35 stages:
byte0 {0,1,2,3}, byte1 {7..35}, byte2
{1,2,4,6,7,9,11,17,18,22,26,31}, byte3
{0x96,0xc8,0xfa,0x2c,0x64}, byte4 mostly $00 (a few $01). The
carve emits one label per stage (Bank6_Stage45..79), the 5 header
bytes as one `db` line with the WRAM destinations in a comment,
then the body as plain `db`.

**Bank 17 — tile data, $4000-$69ef.** `tools/
survey24_bank17.py` reproduces the numbers. Three `ld a,$11;
rst $10` sites, all in bank-0 $3202–$32fc (state-16 tile-load
routines). $4000: 8-entry dw table, read by $3202 ($4000+B*2,
B = queue B from QueueFetchBC $0dda, gated on C==3); entries
$4070,$4070,$4530,$4870,$4d30,$4070,$4070,$4070; the $3202 copy
is $04c0 bytes to VRAM $8040 (MemcpyBC $1065). Entry 8 would
read $4010 = $0001, an invalid pointer — the partition test.
C==3 queue B values are {0,1,2,4} (enumerated from the bank-12
queue table $4f97, 331 pairs), all inside the 8-entry table.
$4010–$406f: 24 4-byte records [flag][00][dw block ptr] in 3
groups of 8 ($4010 by $323d, $4030 by $3291 which sets
[$c809]=$4030, $4050 by $32fc — `ld de,$4050; jr $3294`, the
only such site in the ROM). Each reader does base+B*4, tests
the flag byte (0 = skip via $1778), and copies 16 bytes
(MemcpyC $106e) from ptr+counter*8 ($323d, slots at $8040) or
ptr+counter*16 ($3291/$32fc, slots at $8500) to $c809 — the
pointer arithmetic was re-checked by hand after a first
misread (the popped HL is counter*8/16 WITHOUT the $8040/
$8500 base, which is added only for the saved [$da71] pointer;
the record dw IS the bank-17 pointer). All 24 records are
plausible (flag in {0,1}, b1 $00, dw in
{$5110,$55d0,$5970,$5e30,$6530}); flags repeat per group as
[1,1,1,1,1,1,0,0]; groups 1 and 2 have identical dw sequences.
Record 24 ($4070) breaks the pattern (dw $0000) — the
partition test. $4070–$69ef: data blocks as plain `db` with
labels at the 9 starts the tables reference ($4070/$4530/
$4870/$4d30 from the $4000 table; $5110/$55d0/$5970/$5e30/
$6530 from the records). `gb_rd` from $4000 derails in 42
instructions.

**Banks 19–22 — stream data.** `tools/
survey24_banks1922.py` reproduces the numbers. No `ld a,$xx;
rst $10` site for any of them anywhere in the ROM; the only
mapping is bank-0 $2470's H >= $7e branch, which reads a
bank-14 record [bank][ptr], maps the record bank, and follows
ptr+DE as a Decompress $257f / MemcpyC $106e source (bank-12
$4a3e beforehand only reads a $4eeb table byte into E, never
jumps into the record bank). Record counts / ptr ranges: bank
19: 25 records $4000–$7ade; bank 20: 36 records $4000–$79a8;
bank 21: 28 records $4000–$77c6; bank 22: 28 records
$4000–$7c7c. `gb_rd` walks from $4000 derail in 75 / 24 / 43 /
192 instructions; the code-like opcode counts (bank 19 $5000:
ret 21 / rst $08 87; bank 22 $6000: jp 45) are data bytes, as
in slice 23's bank 15 — no call/jp/jr/table target into any of
these banks exists. Carved as plain `db` $4000 to the last
non-`$ff` byte (19: $7b7f; 20: $7bb9; 21: $7990; 22: $7f0b);
`$ff` tails stay INCBIN. No per-stream boundaries claimed.

**Banks 25/26 — transfer data.** `tools/
survey24_banks2530.py` reproduces the numbers. No `ld a,$xx;
rst $10` site for either bank anywhere; the only mapping is
bank-0 $1da7 TransferTable1E, whose 7-byte items name the
source bank (bank-30 $74e5 table: 3 items from bank $19, src
$6103/$642c/$65cc, all decompress, len $0000; 14 items from
bank $1a, src $4000–$698a). `gb_rd` walks derail in 27 / 32
instructions. Carved as plain `db` $4000 to the last non-`$ff`
byte (25: $67e1; 26: $705c); `$ff` tails stay INCBIN.

**Bank 30 — SGB packets + tables, $40e0-$7cf9.** `tools/
survey24_banks2530.py` reproduces the numbers. $40e0–$470f:
SGB packets — the slice-3 $4000 table has 112 entries / 98
distinct ptrs; each packet is 16*n bytes (n = first byte & 7;
97 x n=1, 1 x n=2 at $4590, spanning 32 bytes to $45b0);
spans tile $40e0–$4710 with zero gaps; emitted as `db` with a
label per distinct packet start. $4710–$64e4 and $6de5–$74e4:
plain `db`, no reader pinned (honest gap, cf. slice 23's
bank-14 low region). $64e5–$6de4: 10 pages x 256 bytes, read by
LoadStagePtr ($1c91/$1cd9: HL=$64e5+DE, DE=(D<<8)|E, D in 0..9
from the $1c9c/$1cca branch logic, E a byte from the caller's
table; 16 bytes copied to $da61). $74e5–$7546: 49-entry dw
table (TransferTable1E index; (0x7547-0x74e5)/2 = 49 exactly).
$7547–$7cf9: 39 distinct lists [count][count x 7-byte items:
bank, src dw, dst dw, len lo, len hi+flags] (bit 7 of the last
byte selects Decompress $257f, len $0000 means
DecompressPrefixed); 276 items total; lists tile $7547–$7cfa
with zero gaps; source banks
{$04,$0d,$0e,$11,$13,$14,$16,$18,$19,$1a,$1b,$1c}. Counts run
1..17 (the $7987 list has 17 — a first probe's <=16 cap was
wrong; all 17 items parse cleanly: bank bytes <= $1f, src
in-bank, dst in VRAM $8c00–$94e0 increasing). This table is
also what pins banks 25/26's readers (above) and 91 of bank
27's items (below). $7cfa–$7fff `$ff` padding stays INCBIN.

**Bank 27 — sprite data + table, $4000-$7ea8.** `tools/
survey24_bank27.py` reproduces the numbers. $4000–$7917:
plain `db` (tile/sprite data; 91 TransferTable1E items from
bank $1b, 43 distinct srcs $4000–$732b). $7918–$7971: 45-entry
dw table read by BuildSpriteEntries ($1dfd: $7918 + A*2 →
list ptr); entry 45 would read $7972 = $0009 (the first list's
count byte) — the partition test. $7972–$7ea8: 45 lists
[count][count x 6-byte items] — [index][b0][b1][b2][b3][b4];
the index byte selects the $c200 + index*32 slot, the other 5
bytes fill the 12-byte record (bytes 0–3, byte 7); 215 items
total; lists tile $7972–$7ea9 with zero gaps. (A first probe
used 5-byte items and showed phantom gaps; the reader consumes
1 index + 5 data bytes = 6 per item — the loop at $1e10 reads
the index byte from the list, then 5 bytes from [DE].) Index
byte values are 0–14 (15 distinct). `gb_rd` from $4000 derails
in 1 instruction. $7ea9–$7fff `$ff` padding stays INCBIN.

**Bank 28 — stream-record table + pool, $4000-$6c46.**
`tools/survey24_bank28.py` reproduces the numbers.
$4000–$409b: 78-entry dw table, read by bank-0 $143e
StreamDispatchRecordD ($4000 + C*2 → stream base, C = record
byte0 & $7f; +B, B = record byte1*2), reached via
StreamIterateDual $13e7 (which maps bank $1c). Entry 78
(@$409c) would read $f100 — implausible — so the table is 78
entries; min plausible target is $409e; entries 0–77 give 56
distinct targets, all in [$409e, $43b2]. The pool head
$409c–$409d is `00 f1`, a marker pair, confirming those bytes
are pool, not table. $409c–$6c46: stream pool as plain `db`,
labelled at the 56 distinct table targets. The $143e loop walks
2-byte values with $f0/$f1 high-byte markers ($f0 x71, $f1 x85
in the pool) and never jumps/calls into the pool. Second
mapping: bank-0 $2470 B >= $af branch (Decompress $257f input).
`gb_rd` from $4000 derails in 11 instructions. $6c47–$7fff
`$ff` padding stays INCBIN.

§2 **Byte-match proof.** Clean `make` (`rm build/game.gb`
first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs
vs `roms/Donkey_Kong_World_Rev1_SGB.gb` — **first try, no
build failures, for the bank-6-only build, the bank-6+17 build,
the +19–22 build, the +25/26/30 build, and the final 11-bank
build.** `tools/gen_banks.py` CARVED diff checked BEFORE each
build (insertion-only each time, 0 dropped). `git status`
clean of build artifacts / `.gb` / `.sav` / binaries /
`__pycache__` (only `.py`/`.asm` sources changed/added). Two
generator bugs caught by their own runs before any build: (a)
a duplicate `30:` key in CARVED (the slice-3 entry at the
bottom of the dict) silently overrode the new slice-24 entry,
so `src/banks.asm` did not move for bank 30 — fixed by
editing the original line instead, and a duplicate-key check
is now part of the pre-build verification; (b) `tools/
gen_slice24.py` grew by appending, which nested the emitter
calls (main → emit_bank17 → emit_stream_banks → …) and left
the `if __name__` guard ahead of the emit_bank27/28
definitions (`NameError` on the first bank-27/28 run) — fixed
by flattening main()'s call chain and moving the guard to the
end of the file. Neither bug reached a build.

§3 **Door / clear-chain entry: still NOT found (NO-GO, no new
door lead).** None of the 11 banks contains code, so none
writes hStateTimer (`$ff90`) or `[$c105]`; nothing in this
slice touches the clear chain. No completion attempt was run
(same NO-GO as slices 15–23).

§4 **Nacre results.** `tools/run_slice5_regression.sh` and
`tools/run_slice7_cases.sh` on the final build, original vs
rebuilt identical in every case (framebuffer hash + state
trace + save): slice-5 suite ALL IDENTICAL (600f
`1cf92679…`, 900f `39ffd5ee…`, 3600f `88515f4e…`, 12000f
`92d2e185…`, s8 `92d2e185…`, f0 `3390d763…`, f1 `1cf92679…`
— all match the slice-19/20/21/22/23 reference hashes);
slice-7 suite ALL IDENTICAL (retry 15000f `0d835d95…`,
mid5000 `2ab1bb5d…`, play-right `b3cb6c8b…`, death 3000f
`632b2eaf…` — all match).

§5 **Verified vs inferred.** VERIFIED: bank 6's 35-stage tiling
(zero gaps, $4000–$7364) and its single entry point (the $2615
SwitchBankByE site); the 5-byte stage header's WRAM
destinations (read straight from LoadStage $2516–$2527);
bank 17's 8-entry table extent (entry 8 = $0001 partition) and
C==3 B values {0,1,2,4} from the queue enumeration; bank 17's
24-record extent (record 24 dw $0000 partition) and the three
reader bases ($4010/$4030/$4050, the last via the only `ld
de,$4050` site in the ROM, bank 0 $32fc); banks 19–22/25/26's
readers ($2470 record banks; TransferTable1E item banks) and
their zero literal bank-select sites; bank 30's packet tiling
(zero gaps, $40e0–$4710), its 49-entry table extent
(arithmetic: (0x7547-0x74e5)/2), and its 39-list zero-gap
tiling ($7547–$7cfa, 276 items, all items validated); bank 27's
45-entry table extent (entry 45 = $0009 partition) and its
45-list zero-gap tiling with 6-byte items (215 items); bank
28's 78-entry table extent (entry 78 = $f100 partition, pool
head `00 f1`); byte-match + both regression suites on the
final build. INFERRED (not verified): bank 6 header byte
roles (destinations known, meanings not traced); bank 17
record-phase B bound (8 per group rests on the three reader
bases + the $4070 pattern break; the queue as a whole has B
up to 203, and no live record-phase B was traced); bank 17
block sizes (only the $04c0 copy length and the 16-byte record
copies are verified); bank 30 $64e5 D ∈ 0..9 (from the
$1c9c/$1cca branch logic, not verified live); bank 28 pool
boundaries beyond the 56 table targets (targets overlap into
a shared pool; +B offsets reach further in); bank 19–22/25/26
per-stream boundaries (plain `db`, none claimed); bank 30
$4710–$64e4 / $6de5–$74e4 contents (no reader pinned, stated
as a gap, not a claim).

§6 **What the next slice should do.** The task list's banks
are done (6, 17, 19–22, 25–28, 30 all closed this slice), so
the next slice works the remaining INCBIN: easiest first is
**bank 5 stage data $40d4–$7fff** (runs 0 and 2 of the stage
table, same shape as bank 6 — 45 stages in bank 5, 26 in bank
18; bank 18's run-2 data is $4000–$61b2 plus its tail, and
bank 24 mirrors bank 18's $4934 table region with its own
$4000–$4933 stream region — the $2470 record table also points
23 records at bank 24, ptrs $4000–$4832). Then bank 23
$4000–$731e (the attract-demo code region is $731f+; the low
region's reader is the same $2470/record family — check first),
bank 12 $5dbc–$7fff (credits + tail), bank 1 $5a00–$7fff,
bank 2/3 gaps ($43b0–$45a8, $48ea–$6211, $6492+), bank 7/8/16
gaps, and the bank-0 raw regions. The door hunt's open item is
unchanged: the clear chain's ENTRY (timer 33/42) and the
parasol collection (hand-written schedule).

## Slice 25 — DONE, byte-matching (2026-11-24)

§1 **Five banks CLOSED + bank-1 code extended.** `src/` now
90,425 lines (was 86,569 after slice 24). Curated: 397,206 /
524,288 bytes (75.8%, was 344,932 / 65.8% — INCBIN lengths
summed directly from src/banks.asm + src/main.asm at both
heads; the 52,274-byte delta matches the carved bytes
exactly. Coordinator correction 2026-11-25: the worker's
345,541 / 397,815 figures counted banks.asm only and missed
main.asm's 609 INCBIN bytes.) This slice alone adds 52,274 bytes. New files
`src/bank5slice25.asm` (1,110 lines, 15,235 bytes),
`src/bank18slice25.asm` (585 lines, 7,863 bytes),
`src/bank24slice25.asm` (722 lines, 11,250 bytes),
`src/bank23slice25.asm` (1,039 lines, 13,119 bytes),
`src/bank12slice25.asm` (304 lines, 4,678 bytes),
`src/bank1slice25.asm` (93 lines, 129 bytes);
`tools/gen_slice25.py`, `tools/survey25_bank5.py`,
`tools/survey25_bank14records.py`, `tools/survey25_bank23.py`,
`tools/survey25_bank1.py`. Banks closed so far (23): 4, 5, 6,
9, 10, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
27, 28, 30, 31. Each closed bank keeps only its `$ff` tail as
INCBIN.

**Bank 5 — run-0 stage data, $40d4–$7c56.**
`tools/survey25_bank5.py` reproduces the numbers. $40d4–$41ff
is 300 bytes of repeating `b2 61` (150 pairs) between the stage
table ($4000–$40d3, slice 4) and stage 0 ($4200). Stages 0–44
from the bank-5 pointer table tile contiguously $4200–$7c56
(sizes 127–640 bytes); stage 44 ($7b64) runs 243 bytes to the
last non-`$ff` byte at $7c56 ($00); $7c57–$7fff is all `$ff`
padding (stays INCBIN). The ONLY `ld a,$05; rst $10` site in
the whole ROM is bank-0 $24e7 (LoadStage) — bank 5 is reached
only via LoadStage → SwitchBankByE ($2611), as decompressor
input; no bank-5 byte can ever execute. `gb_rd` from $4000
derails in 119 instructions; dw values pointing in-bank are
1,797/16,383 (~11%, below the ~25% random rate), so no embedded
pointer table. Header value sets across the 45 stages: byte0
{0,1,2,3,4}, byte1 {5..27}, byte2
{0,3,5,10,12,13,14,16,19,21,22,28,30,32}, byte3
{100,150,200,250} ($64,$96,$c8,$fa), byte4 all $00. The carve
emits one label per stage (Bank5_Stage0..44), the 5 header bytes
as one `db` line with the WRAM destinations in a comment, then
the body as plain `db`.

**Bank 18 — run-2 stage data, $4000–$6206.**
Stages 80–105 from the bank-5 table tile $4000–$6206 (sizes
85–622 bytes); stage 105 ($61b2) runs 85 bytes to the last
non-`$ff` byte at $6206 ($00); $6207–$7fff is all `$ff`
(stays INCBIN). The $4934–$4c84 span is ALREADY carved as 106
8-byte records in `src/bank18.asm` (slice 7's decimal/hex slip
— those bytes are stage 87's body + stage 88's header byte 0,
not a stage table): stages 86 ($49b7–$4b17) and 87
($4b18–$4c82) lie entirely inside that span, so the stage carve
skips $4934–$4c84 (section 1 covers $4000–$4933, section 2
covers $4c84–$6206 with stage 88 continued from its 2nd byte).
The ONLY `ld a,$12; rst $10` site is bank-0 $261c (inside
SwitchBankByE, E >= $50 → bank $12) — bank 18 is decompressor
input only, no bank-18 byte can execute. `gb_rd` from $4000
derails in 17 instructions. Header value sets: byte0 {0..4},
byte1 {5..28}, byte2 {3,4,6,8,9,15,20,24,26,33}, byte3
{100,150,200,250}, byte4 all $00.

**Bank 24 — stream data, $4000–$4933 + $4c84–$6f41.**
`tools/survey25_bank14records.py` reproduces the record counts.
$4000–$4933: 23 bank-14 $7e00 records (indices 117–139) point
here, ptrs $4000–$4832 in 96-byte steps (last $4832, 14 short of
the stride); read by bank-0 $2470 (H >= $7e branch) as
Decompress $257f / MemcpyC $106e input. The bank is mapped only
by bank-0 $26f6/$2773/$289e, all followed by ROM0 calls or data
reads — no call/jp into bank 24 exists. `gb_rd` from $4000
walks 1,684 instructions through data bytes (spurious; opcode
density in $4000–$4fff is ret 0 / call 0). $4c84–$6f41: plain
`db`, NO reader pinned (honest gap — the $2470 records stop at
$4832; what reads $4c84–$6f41 is unknown); `gb_rd` walks from
$4c84/$5000/$6000/$6f00 derail in 10–16 instructions.
$6f42–$7fff is all `$ff` (stays INCBIN). No per-stream
boundaries are claimed for either span.

**Bank 23 — attract-demo data, $4000–$731e + $7e12–$7e31.**
`tools/survey25_bank23.py` reproduces the numbers.
$4000–$4035: 27-entry dw table read by bank-23 $7387 ($4000 +
[$ca66]*2; [$ca66] is the queue B byte, written by C-dispatch
entry 20 $0d6f). Entries 0–26 strictly increasing
($4036–$41d6); entry 27 would read $0004 (the first block's
bytes $04 $00) — the partition break. C==20 queue B values
(enumerated from the bank-12 queue table $4f97, 331 pairs) are
{0..24, 26} (max 26), so every queue index lands inside the
27-entry table; B=25 has no queue entry. $4036–$41e5: 27 blocks
[count][count × 3-byte items: slot, b0, b1], 135 items total;
every block's slot bytes run 0..count-1 sequentially; blocks
tile with zero gaps (each block is 1+3*count bytes, ending
exactly at the next target). The reader ($7395–$73ae) stores
each item's 2 data bytes to $c20c + slot*32. $41e6–$731e: plain
`db`, no reader pinned (honest gap); `gb_rd` walks from
$4000/$5000/$6000/$7000 derail in 7–193 instructions; no carved
bank-23 code targets this span (own-file control-flow check:
NONE). $7e12–$7e31: $7e12/$7e18 are 6-byte blocks copied by
MemcpyC $106e to $d76d/$d77d ($7586/$7591); $7e1e/$7e28 are
10-byte tables (even/odd counting sequences $30..$42 /
$31..$43) indexed by a byte ($75f1 / $749e, A = [$c80b]).
$7e32–$7fff is all `$ff` (stays INCBIN). Bank 23 is mapped by
state 30 ($290a, dispatches into the carved $731f+ code), by
$293a (map-then-return, called from bank-23 $7325), and by
LoadStagePtrWrapper $1c8a (called from bank-23 $76dc) — none of
those paths jumps into $4000–$731e. (Slice 24 §6's guess that
the low region's reader is "the same $2470/record family" was
wrong: NO bank-14 record points at bank 23 — the 140 records
target only banks 19, 20, 21, 22, and 24.)

**Bank 12 — data, $5dbc–$7001 (4,678 bytes).** Plain `db`.
Opens with credits-pattern text (spaces + "defgh" / "jklmnof"
at $5dbc, continuing the $5917–$5dbb credits carve), then binary
data to the last non-`$ff` byte at $7001 ($04); $7002–$7fff is
all `$ff` (stays INCBIN). No reader pinned (honest gap); no
carved bank-12 code targets this span (own-file check: NONE);
`gb_rd` walks from $5dbc/$6000/$6c00 derail in 4–254
instructions.

**Bank 1 — code, $5a00–$5a80 (129 bytes, 78 instructions).**
`tools/survey25_bank1.py` reproduces the numbers. The carved
bank-1 code ends at $59ff; its last routine ($59c4 loop) falls
through at $59fd into $5a00, and calls $5a45/$5a76 from
$59d6/$59dd — the only two control-flow targets into
$5a00–$79ff anywhere in `src/bank1.asm`. `gb_rd` walk from
$5a00/$5a45/$5a76 covers $5a00–$5a80 with zero gaps (116
instructions, no `rst $08`): $5a00–$5a20 loop body (`jr $59c4`
back into the carved routine), $5a3b helper (called 3× from
$5a32/$5a35/$5a38), $5a45 (called from $59d6), $5a76 (called
from $59dd/$5a11) + $5a7c (called from $5a0e/$5a76/$5a79).
The $5a07/$5a26/$5a70 `call $201d` sites are bank-0 routines.
$5a81+ is NOT carved here: no walk reaches it, and the only
ld-pointers past it ($5d48+ tables, $7308 count) are data reads.
Bank 1's remaining gap is now $5a81–$7fff (9,599 bytes).

§2 **Byte-match proof.** Clean `make` (`rm build/game.gb`
first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs
vs `roms/Donkey_Kong_World_Rev1_SGB.gb` — first try for the
five-bank build, and first try again after adding the bank-1
code carve. `tools/gen_banks.py` CARVED diff checked BEFORE
each build (insertion-only each time, 0 dropped; duplicate-key
check: 31 keys, NONE). `git status` clean of build artifacts /
`.gb` / `.sav` / binaries / `__pycache__` (only `.py`/`.asm`
sources changed/added). Two generator bugs caught by their own
runs before any build: (a) `emit_stages` skipped to the next
window's END instead of its START, dropping stage 88's
$4c84–$4e20 remainder (caught by the emitted-byte assertion:
7,450 != 7,863); (b) the title-block slice was off by one
(`lines[11:]` instead of `lines[10:]`), dropping stage 80's
SECTION header so its bytes attached to the bank-18 records
section and the link failed on overlap — fixed, and the
five-bank build then byte-matched first try. A first
`survey25_bank5.py` run caught a hand-typed run-2 stage list
that was wrong (the table assert failed before any carve) —
the list now comes from `src/bank5.asm`, verified against the
ROM.

§3 **Door / clear-chain entry: still NOT found (NO-GO, no new
door lead).** None of this slice's carves writes hStateTimer
(`$ff90`), `hGameState` (`$ff8e`), or `[$c105]` — verified by
grep over all six new files (zero hits). Banks 5/18/24/23/12
are data; the bank-1 $5a00–$5a80 code touches only
$[$c809]–$[$c80c] and WRAM $c81c/$c81d. No completion attempt
was run (same NO-GO as slices 15–24).

§4 **Nacre results.** `tools/run_slice5_regression.sh` and
`tools/run_slice7_cases.sh` on the final build, original vs
rebuilt identical in every case (framebuffer hash + state
trace + save): slice-5 suite ALL IDENTICAL (600f
`1cf92679…`, 900f `39ffd5ee…`, 3600f `88515f4e…`, 12000f
`92d2e185…`, s8 `92d2e185…`, f0 `3390d763…`, f1 `1cf92679…`
— all match the slice-19/20/21/22/23/24 reference hashes);
slice-7 suite ALL IDENTICAL (retry 15000f `0d835d95…`,
mid5000 `2ab1bb5d…`, play-right `b3cb6c8b…`, death 3000f
`632b2eaf…` — all match).

§5 **Verified vs inferred.** VERIFIED: bank 5's 45-stage tiling
(zero gaps, $4200–$7c56) and its single entry point (the $24e7
LoadStage site); bank 5's $40d4–$41ff repeating `b2 61`
pattern (asserted byte-by-byte in the generator); bank 18's
26-stage tiling (zero gaps modulo the already-carved
$4934–$4c84 span) and its single entry point (the $261c
SwitchBankByE site); bank 24's 23-record pinning (indices
117–139, ptrs $4000–$4832) and its three mapping sites (all
followed by ROM0 calls/data reads); bank 23's 27-entry table
extent (partition break at entry 27 + C==20 queue B max 26)
and its 27-block zero-gap tiling with sequential slots (135
items); bank 23's $7e12–$7e31 readers (MemcpyC copies and
byte-table indexes, pinned to carved code); bank 12's
$5dbc–$7001 extent (last non-`$ff` at $7001); bank 1's
$5a00–$5a80 code (zero-gap `gb_rd` walk, both call sites in
carved code, fall-through from $59fd); byte-match on the final
build. INFERRED (not verified): bank 5/18 header byte roles
(destinations known from LoadStage, meanings not traced);
bank 23 $4000-table index range beyond the queue enumeration
([$ca66] max 26 comes from the queue table, not a live trace);
bank 23 $7e1e/$7e28 index ranges (unverified); bank 24
$4c84–$6f41 contents (no reader pinned, stated as a gap);
bank 12 $5dbc–$7001 contents (no reader pinned, stated as a
gap); bank 23 $41e6–$731e contents (no reader pinned, stated
as a gap); bank 1 $5a81+ contents (tables at $5d48+ are
ld-pointer reads, the rest unanalyzed).

§6 **What the next slice should do.** Banks 5, 12, 18, 23, 24
are now CLOSED (only `$ff` tails remain as INCBIN); bank 1 is
extended to $5a80. The remaining INCBIN, by size: bank 3
$4943–$76ea (11,688 B, the big uncarved block) and bank 2
$48ea–$6211 (6,440 B) + $6492–$7fff (7,022 B) — the bank-2/3
gaps are now the largest code-or-data unknowns (survey with
`gb_rd` seeded at gap starts and check call/jp targets from
carved code before carving, as slice 25 did for bank 1);
bank 16 $5fd3–$7fff (8,237 B) + $4044–$4992 (2,383 B); bank 1
$5a81–$7fff (9,599 B, tables at $5d48+ are ld-pointer reads —
survey the $5a81–$5d47 span first, then the tables); bank 7/8
gaps (largest: bank 8 $781a–$7fff 2,022 B, bank 8 $5809–$5e36
1,582 B, bank 7 $71ba–$7509 848 B); bank 0 raw regions; and the
`$ff`-padding tails everywhere (no work — they stay INCBIN).
The door hunt's open item is unchanged: the clear chain's
ENTRY (timer 33/42) and the parasol collection (hand-written
schedule).

## Slice 26 — DONE, byte-matching (2026-11-25)

§1 **Four banks CLOSED: 3, 2, 16, 1.** `src/` now
95,458 lines (was 90,425). Curated: 439,888 /
524,288 bytes (83.9%, was 397,206 / 75.8% — INCBIN lengths
summed directly from src/banks.asm + src/main.asm via the new
`tools/count_curated.py`; the 42,682-byte delta matches the
carved bytes exactly: 12,417 + 11,254 + 10,982 + 8,029).
New files `src/bank3slice26.asm` (924 lines, 12,417 bytes),
`src/bank2slice26.asm` (1,017 lines, 11,254 bytes),
`src/bank16slice26.asm` (2,202 lines, 10,982 bytes),
`src/bank1slice26.asm` (910 lines, 8,029 bytes);
`tools/survey26_bank3.py`, `tools/survey26_bank2.py`,
`tools/survey26_bank16.py`, `tools/survey26_bank1.py`,
`tools/gen_slice26.py`, `tools/gen_slice26_bank16.py`,
`tools/gen_slice26_bank1.py`, `tools/count_curated.py`.
Banks closed so far (27): 1, 2, 3, 4, 5, 6, 9, 10, 12, 13,
14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28,
30, 31. Each closed bank keeps only its `$ff` tail as INCBIN.

**Bank 3 — song data + stream table, $43b0–$45a9 + $4943–$798f.**
`$43b0–$45a9` (505 B) is byte-identical in bank 2: an 86-entry
dw offset table `$43b0–$445a` (strictly increasing $0000–$07f1;
breaks at `$445c`), read by stream-op `$4098` (`ld hl,$43b0`),
plus `$445c–$45a8` stream-command data (4-byte-addressed
entries from the `$4102` branch, `ld hl,$445c`; dispatcher at
`$4730`). `$4943–$76ea` (11,688 B) is **song data**, plain `db`
with a label at each unique song-table entry (32 in-span
labels): the slice-12 song table at `$48f1` (41 dw entries)
points into it; the tick at `$45f2` loads DE = table[index]
(index `[$c837]`, gated < $29) and copies a 10-byte header
(2 → `$df07`/`$df08`, 8 → `$df12–$df19`); `$46e5` treats the
`$df12` words as 4 channel-stream pointers (high byte 0 =
channel off; `$ff` in the note byte = follow-pointer jump at
`$4726`). Songs share phrase data: entries unsorted, `$4941`
(×7) is the all-zero-channel "silent" song whose first 2 bytes
are the table's own last dw (`$454b`), `$49b8`/`$4ac3` are 11
bytes apart. No call/jp/jr target into the span exists in any
carved code; `gb_rd` from `$4943` derails in 10 instrs, from
`$4ac3` in 6. `$78b0–$78f` (224 B) is wave/volume-table-like
data, labels at `$78b0`/`$78d2`/`$78e8`/`$7942` (`$78d2`/
`$7942` share a 15-byte prefix); **no reader pinned** (the
wave-RAM copy at `$781e` reads via `$df05`/`$df0c` pointers,
which are only read, never written, in carved bank-3 code).
Last non-`$ff` at `$798f`; `$7990–$7fff` all `$ff` stays
INCBIN. `$400c–$4010` (4 bytes `$ff`) also stays INCBIN.

**Bank 2 — SFX data + songs 41–64, $43b0–$45a9 + $48ea–$7566.**
`$43b0–$45a9` (505 B) is byte-identical to bank 3 (0 differing
bytes); same 86-entry dw table + `$445c` stream data, read by
bank 2's own stream-op `$4098` and `$4102` branch.
`$48ea–$6211` (6,440 B) is **SFX data**, plain `db` with labels
at each unique `$47fc` entry (118 unique of 119): the slice-12
sound table (`$47fc`, 119 dw) points here — all entries in
`$4904–$6196`. The tick at `$4694` reads each entry as an
8-byte header of 4 channel pointers (stored to `$df1a`/`$df35`/
`$df50`/`$df6b` with `[$df0e]`–`[$df11]` priority checks; high
byte 0 = channel off). Verified: all 119×4 channel pointers
are `$0000` or in `$48ea–$6211`. No per-SFX extents claimed
(streams share phrase data via `$ff`-jumps, as in bank 3).
`$6492–$64c1` (48 B) is a **24-entry dw song table, songs
41–64**: the bank-2 restart at `$6257` reads it (`ld
hl,$6492`, index = `[$c837]`−41, gated `[$c837]` ≥ $29). All
24 entries point into `$64c2–$7566`; entry 24 would read
`$452c` — the first song's own header word at `$64c2`
(partition break, same pattern as slice 25's bank-23 table).
`$64c2` (7 entries) is the all-zero-channel silent song, like
bank 3's `$4941`. `$64c2–$7566` (4,261 B) is song data, songs
41–64; 10-byte headers (same format as bank 3, read at
`$6263`); verified every unique entry's 4 channel pointers
are `$0000` or in `$64c2–$7566`; 17 unique-entry labels (first
table index wins). Last non-`$ff` at `$7566`; `$7567–$7fff`
all `$ff` stays INCBIN. `$4000–$4003` and `$4009–$4010` (all
`$ff`) stay INCBIN.

**Bank 16 ($10) — dispatcher + tables + record helper,
$4000–$4030 + $4044–$4992 + $4eb2–$51c7 + $59f1–$5a10 +
$5fd3–$7e02.** `$4000`: `jp $4044`; `$4003–$4011` is the
fall-through chain `call $43d7; call $45e5; call $46a8; call
$48c4; call $4928`. **`$4031–$4043` is already carved in
`src/bank10.asm` as `Bank10_4031` (hex bank $10, slice 8) —
this carve skips it.** `$4044` reads hStateTimer (`$ff90`):
==$11 (17) → `$4003` chain; `[$c0a4]`==0 → `$4345`;
`[$dd1a]`==4 → `$4003`; else `[$c133]`/`[$c141]` checks →
`$409f` → `$40b0`, ending in `jp hl` through the dw table at
`$4ebf` (index `[$dd18]`*2). `$40bf` reads the `[$ddaa]`
record pointer (+$0b==$0a, +$10 in {3,4}), sets `[$ff91]`
bits, clears `$c205` records / `$dd72` slots, and dispatches
again through the `$4eb2` byte table + `$413e` dw table.
Tables (all `dw`, readers pinned): `$413e` 3 entries (`$4144`,
`$41db`, `$41de`; read at `$4136`, index = `$4eb2[[DE]]`*2;
`$41db`/`$41de` are mid-routine entries); `$4354` 4 entries
(`$435c`, `$4381`, `$4394`, `$43c9`; read at `$434c`, index
`[$c0a5]`*2); `$444a` 9 entries (`$4aef`, `$4460`, `$4498`,
`$44b7`, `$44cf`, `$44f3`, `$4526`, `$456a`, `$459f`; read at
`$4442`, index from a byte table at `$4edd`/`$4fdd`/`$4fe5`
chosen at `$442a`/`$442f`/`$4434`); `$46b7` 6 entries (`$4aef`,
`$4721`, `$47ce`, `$47e0`, `$482d`, `$484d`; read at `$46af`,
index `[$c21f]`*2). `$445c–$445f` (`00 00 40 00`) are 4
unaccounted bytes after the `$444a` table (plain `db`, gap).
Code spans (all `gb_rd` walks, no `rst $08`): `$4144–$4353`
(`$413e`-table routines; `$4342` is `jp $4003`; `$4345` is the
second dispatcher via `$4354`); `$435c–$4449` (`$4354`-table
routines incl. `$43d7`); `$4460–$459d` (`$444a`-table
routines); `$459e` lone `ret` (`$c9`); `$459f–$46b6` (`$444a`
entry 9 + `$45e5` + `$46a8`); `$4721–$4992` (`$46b7`-table
routines incl. `$48c4`/`$4928` chain targets and `$4889`
`call $7dbe`; ends at `$4992`, `$4993+` already carved as
`Bank16_4993`). `$46c3–$4720` (94 B) is small-value data after
the `$46b7` table; no reader pinned (gap). `$4eb2–$51c7`
(790 B) is plain `db` with labels at known bases — `$4eb2`
(13-byte table for the `$413e` dispatch, read at `$412d`),
`$4ebf` (11-entry dw table, index `[$dd18]` 0–10, matching the
`$0a` scan-gate value), `$4edd`/`$4fdd`/`$4fe5` (byte-table
bases for the `$444a` dispatch, read at `$4437`).
`$4ed5–$4edc` (8 bytes) unaccounted inside the span.
`$59f1–$5a10` (32 B) is ASCII-coincident bytes; `gb_rd` from
`$59f1` walks spuriously into carved code — data, no reader
pinned. `$5fd3–$7dbd` (7,659 B) is dense varied data (242
distinct byte values, no 16-byte structure); walks from
`$5fd3`/`$6000`/`$7000`/`$7800` are spurious data-decoding.
No reader pinned (gap). `$5fd3–$605d` is 139 zero bytes.
`$7dbe–$7e02` (69 B) is a record-write helper, called from
`$4889` (`call $7dbe`); writes `$42`/`$7b` markers, `call
$33a7`, builds a record at `$c7f7`, `call $169c`, ends `jp
$0e29` (bank-0). `$7e02` is the last non-`$ff` byte in the
bank; `$7e03–$7fff` all `$ff` stays INCBIN. Generator note:
the first run emitted `$4342–$4353` as `db` because the
seeds missed `$4342`/`$4345` — caught by the generator's own
no-`db`-in-code check, fixed by adding both seeds.

**Bank 1 — [$c809] dispatch code + tables, $5a81–$79dd.**
`$5a81–$5d47` (711 B) is code, one continuous `gb_rd` span
from seeds `[$5a81, $5b71, $5ceb, $5d21]` (417 instrs, zero
unreached, no `rst $08`). Entries, all verified: `$5a81`
(`call $5a81` at bank-0 `$0b3a`, inside State16Table[41]
`$0b28`, which maps bank 1 and calls `$5a81` when
`[$c860]`!=0 and `[$c858]`!=$ff); `$5b71` (`call $5b71` at
bank-0 `$0b3f`, the same `$0b28` else-branch); `$5ceb`
(`call $5ceb` at bank-0 `$22b3`, stream area — bank-1
mapping at that point unpinned, gap); `$5d21` (`jp $5d21`
at bank-0 `$1c7a`, BuildAttrMap tail — TransitionStep1 maps
bank 1 before calling BuildAttrMap). `$5a81`/`$5b71` are
parallel `[$c809]` dispatches ($11/$12 vs $0b/$0c
thresholds; MemcpyC sources `$5fd3` vs `$5f69`, both copied
to `$d76d`). `$5d48–$79dd` (7,318 B) is data, plain `db` with
labels at 22 ld-pointer targets read by carved bank-1 code
(`$5d48`, `$5d5e`, `$5d74`, `$5d8a`, `$5d9e`, `$5dae`,
`$5db4`, `$5e80`, `$5e92`, `$5e96`, `$5e99`, `$5ecb`,
`$5f0d`, `$5f21`, `$609d`, `$60c5`, `$60fd`, `$610d`,
`$6114`, `$7308`) plus the MemcpyC sources `$5f69`/`$5fd3`.
The `$5d48` walk (219 instrs) is spurious: the `$5d48` bytes
are digit-like table data read by `ld`, and the walk jumps
back into `$5d10` only through data-decoding. The
`$6000`/`$7000`/`$7800` walks are spurious too: no call/jp/ld
entry to `$7000`/`$7800`/`$5e54` anywhere in the ROM (byte
search), and `$7000–$704d` / `$7800–$7903` contain ZERO `ret`
(`$c9`) bytes. Last non-`$ff` at `$79dd`; `$79de–$7fff` all
`$ff` stays INCBIN. The `$5bd1` timer restore is in §3.

§3 **Door / clear-chain entry: still NOT found (NO-GO, no new
door lead) — but the `[$c70b]` timer save/restore mechanism is
now fully mapped.** Banks 2 and 3 are all data — zero
`$ff90`/`$ff8e`/`$c105` hits (grep-verified). Bank 16 has
**five hStateTimer (`$ff90`) writes, all writing `$19` (25
decimal)**: `$4126` (in the `$40bf` routine), `$437c`,
`$438f`, `$43ae`, `$43cb` (in the four `$4354`-table handlers).
Timer 25 is State16Table[25] = `$09c6` (the state-16
queue-advance area) — transition machinery, not a clear-chain
entry. **Bank 1 has one hStateTimer write, at `$5bd1`: `ld
a,[$c70b]; ldh [$ff90],a` — a RESTORE of the timer saved in
`[$c70b]`, not a literal 33/42 write.** The mechanism (all 6
writers / 4 readers now pinned): a routine saves the current
hStateTimer into `[$c70b]`, switches to a sub-sequence timer,
and a later routine restores it. Writers: `$08bd`/`$08c6`
(bank-0 `$0859`, State16Table[6] — save timer, set timer 41
`$29`, the save that launches the `$5a81` sequence),
`$6d2a`/`$405a` (bank 7: save, set `$11`), `$66b5` (bank 7:
save, set `$10`), `$55b6` (bank 31: save, set `$10`).
Readers: `$0a2c` (bank-0, the slice-13 restore), `$4e0f`
(bank 1), `$6fc4` (bank 7), `$5bd1` (bank 1, this slice).
The normal restored value is 6 (saved by `$08bd` when timer 6
launches the sequence). `$5c55`/`$5cbf` READ hGameState and
compare with `$1e` (30 = attract demo): the `$5c61`/`$5ce6`
writes are skipped during the demo. `$5ceb` writes
`[$c80d]`=$54/$01. No `[$c105]` writes in any new file.
**Live (`gb_pcwatch`, 15000f retry flow, progress-1 save):**
`$5a81@1` 0, `$5b71@1` 0, `$5bd1@1` 0, `$08bd` 0, `$0b28` 0 —
the `$5a81` sequence NEVER fires in this flow. `$0859` fires
2,262× but in STATE 18 timer 6 (the routine is shared between
states 16 and 18), and its `$08bd` save branch is never taken:
the gate (`[$ff8b]`&$0c, `[$da4b]`!=$21, `$c712`/`$c711`
check) fails throughout. So the `$5a81` sequence is gated on
a flow the retry run never takes — which flow (map entry with
input?) is an OPEN QUESTION for a later slice, and the
restored value at `$5bd1` is unresolved live (statically
normally 6). VERIFIED LIVE in the same run: `$5d21@1` 23×
and `$5ceb@1` 6×, both state 18 timer 1 — the BuildAttrMap
tail-jump and the `$22b3` stream call run on every stage
load. (Tool check: `gb_pcwatch` validated on a 600f idle run
— `$0100` 1×, `$0040` 3,792×, `$06bd` 1× at frame 234 — before
trusting the zeros; the binary is git-ignored, source
`tools/gb_pcwatch.c`.) No completion attempt was run (same
NO-GO as slices 15–25).

§4 **Nacre results.** `tools/run_slice5_regression.sh` and
`tools/run_slice7_cases.sh` on the final combined build
(banks 2+3+16+1), original vs rebuilt identical in every case
(framebuffer hash + state trace + save): slice-5 suite ALL
IDENTICAL (600f `1cf92679…`, 900f `39ffd5ee…`, 3600f
`88515f4e…`, 12000f `92d2e185…`, s8 `92d2e185…`, f0
`3390d763…`, f1 `1cf92679…` — all match the canonical
reference hashes); slice-7 suite ALL IDENTICAL (retry 15000f
`0d835d95…`, mid5000 `2ab1bb5d…`, play-right `b3cb6c8b…`,
death 3000f `632b2eaf…` — all match). The slice-5/7 runs on
the bank-3-only build (earlier in the slice) were also all
identical with the same hashes.

§5 **Verified vs inferred.** VERIFIED: bank 3's `$43b0`
86-entry table (strictly increasing, reader `$4098` pinned)
and its byte-identity with bank 2's; bank 3 song-data
identification (tick reads + channel-pointer format + no cf
targets into the span); bank 2 SFX identification (all 119×4
channel pointers verified `$0000` or in-span); bank 2 song
table 41–64 + partition break at entry 24; bank 16's
dispatcher + all four dw tables with readers pinned; bank
16's five timer-25 writes (all `$19`, grep-verified); bank 1's
`$5a81–$5d47` code (zero-gap walk, all four entries pinned to
carved callers / ROM byte search); bank 1 `$5d21`/`$5ceb`
live (23×/6×, state 18 timer 1); bank 1 `$5a81`/`$5b71`/
`$5bd1` never firing in the retry flow (`gb_pcwatch`, 0 hits);
the `[$c70b]` mechanism (6 writers / 4 readers, all pinned);
the count (42,682 delta = INCBIN reduction exactly);
byte-match on the final build. INFERRED (not verified): bank 3
`$78b0` wave/volume-table role (no reader pinned); bank 3 song
extents (streams share phrase data, no per-song extents
claimed); bank 2 song-table upper index bound (unverified);
bank 16 `$46c3–$4720`, `$4ed5–$4edc`, `$445c–$445f`,
`$59f1–$5a10`, `$5fd3–$7dbd` contents (no readers pinned);
bank 1 `$5d48–$79dd` contents beyond the 22 labelled reader
targets (no per-entry extents claimed); the `$5a81` sequence's
firing flow and the `$5bd1` restored value (statically
normally 6, unresolved live); bank-1 mapping at `$22b3` for
the `$5ceb` call (call exists, mapping unpinned).

§6 **What the next slice should do.** Banks 1, 2, 3, 16 are
now CLOSED (only `$ff` tails remain as INCBIN). The remaining
INCBIN is 84,400 bytes, of which the only non-`$ff` work is
the bank 7 gaps (3,379 B: `$6581–$664d` 205, `$67a1–$68ac`
268, `$68c4–$695a` 151, `$6ed2–$6f05` 52, `$7001–$714b` 331,
`$71ba–$7509` 848, `$7610–$77a8` 409, `$7abb–$7d5d` 675,
`$7e18–$7edc` 197, `$7f0d–$7fff` 243) and the bank 8 gaps
(6,395 B: `$5809–$5e36` 1,582, `$611f–$6273` 341,
`$6283–$63b4` 306, `$6669–$67bc` 340, `$67cc–$68b7` 236,
`$68ef–$69ae` 192, `$69be–$6a24` 103, `$6a34–$6aba` 135,
`$6aca–$6d89` 704, `$7292–$730f` 126, `$74f4–$7525` 50,
`$7588–$7601` 122, `$762a–$7684` 91, `$76b6–$76e2` 45,
`$781a–$7fff` 2,022), plus the bank-0 tail `$3947–$3fff`
(1,721 B, SGB code tail — raw region) and bank 11
`$7e3d–$7fff` (451 B). Everything else remaining is `$ff`
padding (stays INCBIN). The door hunt's open items: which flow fires the
`$5a81` sequence / what `$5bd1` restores live (a scripted
run that takes the `$0859` gate — map entry with input —
then `gb_pcwatch` on `$5bd1@1`); the clear chain's
ENTRY (timer 33/42) unchanged; the parasol collection
(hand-written schedule) unchanged. SLICE 27 UPDATE: the
clear-chain ENTRY is now FOUND statically — the `$75ea`
handlers invoke the `$7abb`-family blobs via `$6e54`,
which save the timer to `[$c70b]` and set timer 22, and
state-16 timer 22 (`$098c`) goes to state 24, the bank-1
`$4000` stage-clear dispatch (slice 27 §3). What remains
live is WHICH `$75ea` handler index (which tile) fires
one of them in real gameplay — needs a run where Mario
actually reaches the door. The `$0859` gate flow is
STILL unfound live: four `gb_pcwatch` runs (baseline,
Start@835, Start@2501, Select@835) all show gate 1
(`$0894`) at 0 — the gate never opens, and `$5bd1`'s
live restore is still unresolved (statically the
`$08bd` save, normally 6). The bank-16 pockets
(`$617c`/`$61b2`/`$6b32`/`$6b85` — slice 26's "pure
data" was wrong there) are uncarved, blocked on
`$0fd9` (slice 27 §2). The parasol collection
(hand-written schedule) unchanged.

## Slice 27 — DONE, byte-matching (2026-11-25)

§1 **Two banks CLOSED: 7, 8.** `src/` now
99,814 lines (was 95,458). Curated: 449,550 /
524,288 bytes (85.7%, was 439,888 / 83.9% — INCBIN lengths
summed directly from src/banks.asm + src/main.asm via
`tools/count_curated.py`; the 9,662-byte delta matches the
carved bytes exactly: 3,267 + 6,395). New files
`src/bank7slice27.asm` (1,585 lines, 3,267 bytes),
`src/bank8slice27.asm` (2,841 lines, 6,395 bytes);
`tools/survey27_gaps.py`, `survey27b.py`, `survey27c.py`,
`survey27d.py`, `survey27e.py`, `survey27f.py`,
`survey27g.py`, `tools/gen_slice27.py`. Banks closed so
far (29): 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15,
16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30,
31. Each closed bank keeps only its `$ff` tail as INCBIN.
Bank 0 is 85% done; its tail `$3947–$3fff` (1,721 B) is
confirmed all `$ff` (the task's "SGB code tail" premise
was wrong — it is `$ff` padding continuing from
`$392b–$3946`, which `src/sgb.asm` already notes) and
stays INCBIN. Bank 11 `$7e3d–$7fff` (451 B) is confirmed
all `$ff` and stays INCBIN.

**Bank 7 — `$6581–$664d`, `$67a1–$68ac`, `$68c4–$695a`,
`$6ed2–$6f05`, `$7001–$714b`, `$71ba–$7509`,
`$7610–$77a8`, `$7abb–$7d5d`, `$7e18–$7edc`,
`$7f0d–$7f8f`.** `$6581–$6584` is a 2-entry dw jump
table (`$6585`, `$65cd`); reader `$6572` (slice 5:
`ld a,[$dd1e]; add a; ld c,a; ld b,$00; ld hl,$6581;
add hl,bc; ld a,[hl+]; ld h,[hl]; ld l,a; jp hl`). The
2-entry reading is a judgment call: the bytes at `$6585+`
decode as a coherent routine (`ld a,[$0efa];
jp nz,$6f26; nop; add hl,hl` ×5; …) flowing into the
verified `$65a3` span, and entry 0 (`$6585`) pointing
into its own table would be self-referential under a
4-entry reading. `$6585–$664d` code (337 instrs, 0
uncovered); `$662a` REAL (9 same-bank `jp z` from carved
`$47xx–$58xx`). `$67a1–$67de` code (38 instrs, entry
`$67a1` from bank-7 `$4000` call); `$67df–$67ee` an
8-entry dw jump table (`$67ef`, `$6b09`, `$68a5`,
`$688e`, `$6b09`, `$67fd` ×3), reader `$67d6`
(`ld hl,$67df; add hl,bc; ld a,[hl+]; ld h,[hl];
ld l,a; jp hl`, index from the `$73xx` data table);
`$67ef–$68ac` code (271 instrs, 0 uncovered; `$67fa`
`jp $768a` and `$68a2` `jp $771e` real; boundary clean:
`$68ab` `inc [hl]`, `$68ac` `ret`, carved `$68ad` starts
`ld a,[$dd1b]`). `$68c4–$695a` data (table base,
`ld hl,$68c4` at `$68b7`). `$6ed2–$6f05` code (48
instrs, entry-unverified — carved `$6ed1` ends
`jp $6f2e`, no fall-through; tail jumps into carved
`$6f2e–$6f3f`). `$7001–$701a` a 13-entry dw jump table
(`$701b`, `$706c`, `$7068`, `$708f`, `$70c2`, `$70e4`,
`$70f0`, `$701b`, `$70f0`, `$70f1`, `$7107`, `$7124`,
`$7125`), reader `$6fe8` in the `$6f62` dispatch area;
`$701b–$714b` code (207 instrs, 0 uncovered).
`$71ba–$7509` data (31 ld-ptr labels; `$7394` read by
the `$7169` stage-RAM clear, 16-byte copy
`$7394→$dd59`). `$7610–$7688` data (`$3f`-fill with
sparse `$7f`/`$80–$88` markers; `$7610` a data base,
`ld bc,$7610`); `$7689` a 1-byte `ret` (entry via
`$6e54` Handler10, B=`$2e` — `$6e54` `jp hl` lands on
it and it returns to the handler's caller);
`$768a–$77a8` code (205 instrs, 0 uncovered; `$768a`
from `$67fa` jp VERIFIED; `$76c5` record-builder
family, entry UNVERIFIED; `$771e` entry UNVERIFIED —
see §6). `$7abb–$7d5d` code (481 instrs, 0 uncovered)
— the door finding, see §3. `$7e18–$7ed2` code (122
instrs, 0 uncovered); `$7ed3–$7edc` data (label
`$7ed3`, read by the `$76c5`/`$7abb`/`$7d03`
record-builders and by `bank7.asm`). `$7f0d–$7f8f`
data (dw-table-like pattern, no reader pinned);
`$7f90–$7fff` all `$ff` stays INCBIN.

**Bank 8 — `$5809–$5e36`, `$611f–$6273`,
`$6283–$63b4`, `$6669–$67bc`, `$67cc–$68b7`,
`$68ef–$69ae`, `$69be–$6a24`, `$6a34–$6aba`,
`$6aca–$6d89`, `$7292–$730f`, `$74f4–$7525`,
`$7588–$7601`, `$762a–$7684`, `$76b6–$76e2`,
`$781a–$7fff`.** `$5809–$5904` data (63 × 4-byte class
records, continuing the `$5409–$5808` table:
`$5409 + 256*4 = $5809` exactly; no reader pinned for
`$5809+`). `$5905–$5e36` code (802 instrs, 0 uncovered):
11 parallel position-math routines (`ld hl,$dd98`;
`xor a`; `ld [hl+],a` ×5; …; writes
`[$c1f3]`/`[$c1f4]`/`[$c1f5]`/`[$c1f6]`), ending
`ldh a,[$ff8d]; jp $0fe5` (bank-switch return) or
`jp $5e1b` (shared tail). 8 entries verified via the
bank-0 `$2a0a` dispatch tail (`$5a5e`/`$5ab4`/`$5905`/
`$5962`/`$59cb`/`$5a32`/`$5c51`/`$5d07`); `$5bec`/
`$5c9e`/`$5d59` entry UNVERIFIED (no `$2a`-tail/table/
cf entry) but `$5bec` ends `jp $5d59` (internal link)
and all three decode as perfect family members.
`$611f–$612c` a 7-entry dw table (`$6473`, `$612d`,
`$609d`, `$7310`, `$63b5`, `$6646`, `$63f0`), reader
`$6117`; `$612d–$6273` code (192 instrs). `$6283–$6290`
a 7-entry dw table (`$7310`, `$6291`, `$6360`, `$6386`,
`$63b5`, `$7310`, `$63f0`), reader `$627b`;
`$6291–$63b4` code (160 instrs). NOTE on both tables:
the walk's "`$6290`/`$612c`: `ld h,e`" is a MISALIGNED
decode of the `$63f0` high byte; real code starts
`$6291`/`$612d` (`call $2acd`). `$7310` is the shared
sentinel (also the `$6a34` table). `$6669–$67aa` code
(194 instrs; `$66fd` countdown helper, targeted from
`$6670`/`$6675`/`$667a`/`$67a8`; entry into `$6669`
UNVERIFIED — `$6668` is a 1-byte `ret`) + db
`$67ab–$67bc` (18 B). `$67cc–$68b7` code (224 instrs,
0 uncovered; `$67cc` a table base, `ld hl,$67cc` at
`$67c4`). `$68ef–$69ae` code (154 instrs) + db
`$68f6–$68fa` (5 B; `$6902` from same-bank `$69ac` jp,
circular). `$69be–$6a24` code (110 instrs) + db
`$6a02–$6a04` (3 B; entry UNVERIFIED — ld-ptr `$69be`
only; walk starts `jp nz,$0269`). `$6a34–$6a3b` a
4-entry dw table (`$7310`, `$6a3c`, `$6a57`, `$6aa7`),
reader `$6a2c`; `$6a57–$6a58` is `ld a,[$c0f8]` (the
walk's "`$6a59`: `ret nz`" was the misaligned low byte
`$c0`); `$6a3c–$6aba` code (196 instrs, 0 uncovered).
`$6aca–$6ad5` a 6-entry dw table (`$6ad6`, `$6b7c`,
`$6ba1`, `$6cc5`, `$6d16`, `$6d20`), reader `$6ac2`;
`$6ba1`/`$6d16` are TABLE ENTRIES (code starts there),
not data pockets — the earlier "uncovered" reading was
the walk missing the table seeds; `$6ad6–$6d89` code
(570 instrs, 0 uncovered). `$7292–$730f` code (127
instrs), `$74f4–$7525` code (33 instrs), `$7588–$7601`
code (97 instrs; `$7588` VERIFIED by bank-0 `$08d2`
call with bank 8 mapped; `$75e5` routine entry
UNVERIFIED and contains a `$75f6` self-loop trap
(`jr $75f6`) when its inner scan exhausts E without
finding a zero byte), `$762a–$7684` code (68 instrs),
`$76b6–$76e2` code (28 instrs). `$781a–$7fff` data
(2,022 B): NO verified entries — every bank-0 hit is
a phantom or an other-bank target (`$78ba`→bank 7,
`$7909`/`$790d` phantoms, `$7ae5`/`$7b6c`/`$7c57`/
`$7c88`/`$7cb0`→bank 10, `$7e35` phantom,
`$7e44`→bank 31; same-bank `$7e09`/`$7ee5` phantoms
straddling `ld hl,$c200`/`$c220`) — walks from those
seeds are spurious. Plain `db`, no labels.

§2 **CORRECTION — bank 16 `$5fd3–$7dbd` is NOT pure
data (slice 26 §1).** Bank-0 callers verified this
slice map bank 16 and call `$617c` (`$08fd`/`$0974`),
`$61b2` (`$28e5`/`$321f`), `$6b32` (`$0aaf`/`$2904`),
`$6b85` (`$0b0f`) — so slice 26's classification is
wrong at those four points (bank 16 vs bank 8 bytes
differ almost entirely there: 42/42, 116/116, 74/74,
27/28). Walks (survey27f `b16`, 216 instrs): `$617c`
clean (`call $72e4`; `ld a,[$c160]` … `jp hl`) + the
`$72e4–$733a` routine; `$61b2`/`$6b32`/`$6b85` derail
at `call $0fd9` (bank-0 raw region, uncarved — the
bytes after the call decode as garbage: `$61b5–$61c0`,
`$6b39–$6b44`, `$6b8c–$6b8f`; the `$61c1–$622a` and
`$6b45–$6b56` tails recover into clean record-write
code). NOT carved this slice (out of scope — bank 7/8
+ bank-0 tail): carving the pockets is blocked on
`$0fd9` first. Left for a later slice with `$0fd9`
as the prerequisite.

§3 **Door / clear-chain ENTRY — FOUND statically; the
`$0859` gate — NOT FOUND live.** The `$7abb–$7d5d`
carve adds FIVE `[$c70b]` writers (the `[$c70b]` list
grows 6 → 11). Each saves `hStateTimer` into `[$c70b]`
and sets timer 22 (`$16`):
`$7b6e` (in the `$7b14` routine, entered via `$6e54`
Handler02), `$7c34`, `$7c97`, `$7cfa` (in the
`$7bda–$7d02` span, entered via `$6e54` Handlers
04/08/09 at `$7bda`/`$7c3d`/`$7ca0`), `$7bd1` (in the
`$7b77` routine, entry UNVERIFIED). The entries are
via `$6e54` (bank7slice10 handlers `jp $6e54` with
HL=blob; `$6e54` ends `pop hl; jp hl`, so the blobs
EXECUTE as code — this is what resolves the old
`$7abb` data-vs-code tension: the "code-like" bytes
are `$6e54` blobs, and the `$7e43`/`$7e55`/`$7e67`/
`$7e79` blobs are likewise code, entered the same way
by Handlers 14/15/16/13). The chain from there is
fully mapped in carved code: state-16 timer 22 is
`$098c` (`ld a,$01; rst $10; ld a,$18; ldh [$ff8e],a;
xor a; ldh [$ff90],a` — `hGameState`=24, timer 0),
and state 24 is the banked entry `$4000` (bank 1,
mapped by `$098c` itself): `Bank1_State24Dispatch`
(`ldh a,[$ff90]; rst $08`, 5-entry table `$400d`,
`$406c`, `$41cf`, `$411b`, `$4142`) — the stage-clear
sequence. So the clear-chain ENTRY slice 24 was
missing is: a `$75ea` interaction handler (tile
interaction) → `$6e54` → a `$7abb`-family blob →
save timer to `[$c70b]`, set timer 22 → state 24.
The `$7e79` routine writes `[$c70c]` (not `$c70b`) —
adjacent, same family. LIVE: the five new writers
never fire in the retry flow (15000f, all 0) or the
play-right flow (5000f, all 0) — Mario never reaches
the door in either flow, so the entry is verified
statically but NOT yet observed live. The remaining
live question is which `$75ea` handler index (which
tile) fires one of them in real gameplay.
The `$0859` gate (State16Table[6], bank-0 `$0859`) is
a SEPARATE mechanism, now mapped statically in full:
it saves the timer and sets timer 41 when the player
presses Select/Start (`hJoypadNew & $0c` — low nibble
bit 2 = Select, bit 3 = Start, per `ReadJoypad`
`$1022`) on a state-16/18 timer-6 frame, with
`[$da4b]!=$21` and (`$c712!=0` or `$c711!=1`); the
bit-3 branch (`$08c4`) saves and calls `AdvanceState`,
the bit-2 branch (`$08bd`) saves and sets timer 41
(launching the `$5a81` sequence via State16Table[41]
`$0b28`). LIVE (gb_pcwatch, validated first on the
600f idle run: `$0100` 1×, `$0040` 3,792×, `$06bd` 1×
at frame 234 — identical to slice 26): the gate
NEVER opens in four runs — baseline retry 15000f
(`$0859` 2,262×, all state 18 timer 6; `$088d`
18,066×; `$0894`/`$089e`/`$089f`/`$08bd`/`$08c4`/
`$0b28` all 0), retry + Start 835:847 (2,208×; all
gate points 0), retry + Start 2501:2513 (2,262×, gate
points 0), retry + Select 835:847 (2,208×, gate
points 0). The Start/Select presses at 835–847 are
consumed by FileSelectLoop (the `$0859` count drops
2,262→2,208 and the first hits move 835→1130); the
2501 press lands on no `$0859` firing at all in the
pcwatch flow. The `$5a81` sequence never fires in any
run (`$5a81@1`/`$5b71@1`/`$5bd1@1` all 0), so what
`$5bd1` restores live is still UNRESOLVED — statically
it is the `$08bd` save, normally 6. HARNESS CAVEAT:
`gb_pcwatch` reads state mid-frame (at the PC hit)
while `gb_headless`'s trace reads it end-of-frame,
and `DispatchState` runs ~6×/frame (`$01a9` 5,673× in
900f) — so the two disagree on which state a frame is
"in" (pcwatch: state 18 timer 6 at frames 835–842;
trace: state 3 timer 1 at 839–842). The pcwatch counts
are self-consistent and match slice 26 exactly; the
trace is the end-of-frame view. Do not mix the two
when timing an input.

§4 **Byte-match proof.** Clean `make` (`rm
build/game.gb` first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp`
zero diffs vs
`roms/Donkey_Kong_World_Rev1_SGB.gb`.

§5 **Nacre results.** Slice-5 regression: 600f
`1cf92679…`, 900f `39ffd5ee…`, 3600f `88515f4e…`,
12000f `92d2e185…`, s8 `92d2e185…`, f0 `3390d763…`,
f1 `1cf92679…` — ALL REGRESSION CASES IDENTICAL.
Slice-7 cases: retry 15000f `0d835d95…`, mid5000
`2ab1bb5d…`, play-right `b3cb6c8b…`, death `632b2eaf…`
— ALL SLICE-7 CASES IDENTICAL. All canonical hashes
match.

§6 **Verified vs inferred.** VERIFIED: every
region's byte coverage (generator asserts the
uncovered set equals exactly the expected db
pockets); all table entries and readers named in §1;
the `$6e54` blob-execution mechanism (`$6e54` ends
`pop hl; jp hl`, handlers `jp $6e54` with HL=blob);
the timer-22 → state-24 → bank-1 `$4000` chain
(all carved code); the `$0859` gate's static
conditions and its never-opening in four live runs.
INFERRED / ENTRY-UNVERIFIED (code by decode +
family, entry not pinned): bank 7 `$76c5`, `$771e`,
`$7abb` head, `$7b77`, `$7d03` head, `$6ed2`,
`$7ecb`; bank 8 `$5bec`/`$5c9e`/`$5d59`, `$6669`,
`$69be`, `$75e5`, `$6b32`/`$6b85` (bank-8 bytes).
JUDGMENT CALLS: `$6581` is a 2-entry table (see §1);
`$6b77` "entry" DISPROVED (raw bytes `$6b70–$6b80`
are `sub [hl]; ld a,$19; ld [$c0f9],a; ld a,$03;
ld [$c10a],a; ret; …` — `$6b77` is the `$03` operand
byte); `$7e22`/`$7ecb`/`$7722`/`$773a`/`$773d`/`$7786`
"jp from carved" hits do NOT exist in carved bank-7
source (grep) — ROM byte-search phantoms in data
bytes; `$7e20` `ld de,$0080` spans `$7e20–$7e22`
(the `$7e22` entry was a phantom); `$7e51–$7e54`
is NOT a 4-byte orphan — the walk shows `$7e50`:
`ld a,$01`, `$7e52`: `jp $0df4` (earlier mis-index
corrected); `$6a57–$6a58` is `ld a,[$c0f8]` (the
walk's "`$6a59`: `ret nz`" was the misaligned low
byte `$c0`); `$612c`/`$6290` "`ld h,e`" are misaligned
decodes of the `$63f0` table high byte. Bank 16
pockets: NOT carved (see §2).

## Slice 28 — DONE, byte-matching (2026-11-25)

§1 **Bank 16 CLOSED for real; bank 0's main.asm INCBINs all gone.**
`src/` now 102,996 lines (was 99,814). Curated: 450,159 / 524,288
bytes (85.9%, was 449,550 / 85.7% — the 609-byte delta is exactly
the bank-0 carve; bank 16's 7,659 bytes were already counted as
curated, because slice 26 had emitted them as `db` — this slice
replaces that `db` with real code/tables/data, so bank 16's count
does not move). New files `src/bank16slice28.asm` (3,368 lines,
7,659 bytes), `src/bank0slice28.asm` (306 lines, 609 bytes);
`tools/survey28_b16.py`, `tools/survey28_bank0.py`,
`tools/gen_slice28.py`. `src/bank16slice26.asm` truncated (its
`$5fd3-$7dbd` db block, lines 1722-EOF, deleted with a pointer
comment); `src/main.asm` has ZERO INCBIN left — the only bank-0
INCBIN remaining is the `$3947-$3fff` `$ff` tail in `src/banks.asm`
(1,721 B). Remaining INCBIN overall: 74,129 B, all `$ff` padding
tails in `src/banks.asm` (per-bank: 0: 1,721; 1: 1,570; 2: 2,723;
3: 1,652; 4: 2,384; 5: 937; 6: 3,227; 7: 112; 9: 4,180; 11: 451;
12: 4,094; 13: 7,409; 14: 92; 15: 4,155; 16: 509; 17: 5,648;
18: 7,673; 19: 1,152; 20: 1,094; 21: 1,647; 22: 244; 23: 462;
24: 4,286; 25: 6,174; 26: 4,003; 27: 343; 28: 5,049; 29: 364;
30: 774). Banks closed so far (29, unchanged): 1, 2, 3, 4, 5, 6, 7,
8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
26, 27, 28, 30, 31. Bank 16 is now closed for real (slice 26's
"CLOSED" was premature — the `$5fd3-$7dbd` span was `db`, not
code). Only bank 11 remains unclosed and it is `$ff` padding only.

**CORRECTION — bank-0 `$0fd9` is NOT raw (slice-27 task premise
wrong).** `$0fd9` (DispatchViaRST8) has been carved in `src/main.asm`
since slice 1. What slice 27 actually found is the `call $0fd9`
INLINE-TABLE idiom: `$0fd9` pops the return address (= the address
just after the call), adds A*2, and jumps to the dw stored there —
so the bytes after `call $0fd9` are a dw jump table, not code (same
family as `rst $08` tables, entered via call). The table-entry
routines `ret` to whatever the caller pushed (or to the call's
return address when nothing was pushed). `gb_rd` does not know this
— it falls through the call into the table bytes and decodes garbage
— so the generator walks ONLY from table-entry targets, emits each
inline table as `dw`, and linear-decodes dispatch heads stopping at
the `call $0fd9`. The six `call $0fd9` sites in bank 16
`$5fd3-$7dbd` are `$61b2`, `$649e`, `$6b36`, `$6b89`, `$6bcc`,
`$6d64` (whole-ROM byte search; no `rst $08` in the span).

**Bank 16 — `$5fd3-$7dbd` (7,659 B).** `$5fd3-$617b` data (no
reader pinned; `$5fd3-$605d` zeros; the `$6118` words look like
`$61xx` pointers but their targets decode as data noise —
`ld [$0808],sp` ×4 — so the span is data). `$617c-$619b` code
(83 instrs; bank-0 `$09cc` call, bank 16 mapped) + `$619c` dw
table, 2 entries (`$61a0`, `$61a6`; reader `$6194`, index
`[$c213]`*2) + `$61a0-$61b1` code (26 instrs; `$61ac` by
fall-through from `$61a6`). `$61b2` head (`call $0fd9`; bank-0
`$28e5`/`$321f` call, A=B) + `$61b5` dw table, 6 entries
(`$61c1`, `$622b`, `$633c`, `$63d7`, `$63d8`, `$649d`) +
`$61c1-$6484` code (424 instrs; db `$6335-$633b`, 7 B) +
`$6485-$649c` data (24 B, record-looking, no reader pinned) +
`$649d` 1-byte `ret` (entry 5, a no-op entry). `$649e` head
(`call $0fd9`; bank-0 `$0af7` call, A=B) + `$64a1` dw table, 8
entries (`$64b1`, `$661a`, `$67bc`, `$692a`, `$69ba`, `$6a3c`,
`$6b30`, `$6b31`; entries 6/7 are 1-byte rets) + `$64b1-$6b31`
code (1,029 instrs, one continuous span, 0 uncovered).
`$6b32` head (`ld hl,$72e4; push hl; call $0fd9`; bank-0
`$0aaf`/`$2904` call, A=B; the pushed `$72e4` is the
continuation the table routines `ret` to via `$6d52`/`$6db7`)
+ `$6b39` dw table, 6 entries (`$6b45`, `$6b57`, `$6b69`,
`$6b6f`, `$6b70`, `$6b84`; entry 5 is a 1-byte `ret`) +
`$6b45-$6b84` code (48 instrs). `$6b85` head (same shape;
bank-0 `$0b0f` call, A=B) + `$6b8c` dw table, 8 entries
(`$6b9c`, `$6bae`, `$6cfc`, `$6d14`, `$6d2c`, `$6d3e`, `$6d50`,
`$6d51`; entries 6/7 are 1-byte rets) + `$6b9c-$6bce` code (18
instrs, incl. the `$6bc9` nested head `ld a,[$c213];
call $0fd9`) + `$6bcf` dw table, 4 entries (`$6bd7`, `$6bfe`,
`$6c2a`, `$6ce5`) + `$6bd7-$6d51` code (234 instrs).
`$6d52` head (`ld de,$c161; ld a,[de]; res 0,a; ld [de],a;
push hl; ld e,[hl]; inc hl; ld d,[hl]; ld c,l; ld b,h;
ld a,[de]; ld hl,$6db7; push hl; call $0fd9`) + `$6d67` dw
table, **40 entries — ONE table, not two**: entries 0–20
(`$6dbf-$6fe9`) and 21–39 (`$6ff5-$72c5`) are contiguous
(`$6d67+2k`, k=0..39); the "$6d91 table" is entries 21–39 of
the same table. Index A = `[$c161]` & ~1, so A ranges 0..78.
No separate reader exists (no `ld hl,$6d91` anywhere in the
ROM — whole-ROM byte search, zero hits; no `ld h,$6d` /
`ld l,$91` in bank 16 either); the reader is `$6d52` itself.
`$6db7-$6dbe` continuation (`pop hl; ld a,[$c161]; rra;
jr nc,$6d59` — loops back into `$6d52` while bit 0 clear —
`ret`). `$6dbf-$7280` code (867 instrs, entries 0–36) +
`$7281-$7290` data (16 B; `$7281` is a data base,
`ld hl,$7281` at `$7274`) + `$7291-$72e3` code (61 instrs,
entries 37–39, incl. the `$72dd` shared tail: `add a,l;
ld l,a; inc de; ld [hl],e; inc hl; ld [hl],d; ret`) +
`$72e4-$733a` code (64 instrs; the record-scan routine, reads
the `$7b86` pointer table; called from `$617c` and pushed as
the `$6b32`/`$6b85` continuation). `$733b-$7dbd` data (labels
`$7343` = signed-offset table read at `$6ee3`, `$735d` read at
`$718b`, `$7b86` = pointer table read at `$72f8`; the post-ret
walk over this span decodes as data noise — `ld a,e;
ret z` ×10, `ld bc,$0b02`, `jp nz,$0380` — and the `$7b86`
entries point at data records, not code, so the whole span is
data). `$7dbe-$7e02` was already carved (slice 26).

**Bank 0 — `$0674-$067f`, `$0df4-$0f08`, `$0f74-$0f94`,
`$0fa1-$0fc0`, `$1075-$10aa`, `$1e6b-$1e85`, `$3689-$3736`
(609 B).** `$0674-$067f` code (14 instrs; `$0674-$067a` is the
tail of STAT_0673: `ldh [$ff45],a; ld a,$35; jp $03e9`;
`$067b` called from `$04fc`: `ld hl,$ce1d; jr $0683`).
`$0df4-$0f08` code (entries `$0df4`, `$0e29`, `$0e64`, `$0ea9`,
`$0ecd`; `$0df4` jp'd from bank-7 `$7e52`/`$7e64`/`$7e76` and
called from bank-1 `$50ef` / bank-12 `$564e`; `$0e29` jp'd
from `$0bcd`/`$0bdb` + bank-16 `$7e00`, called from bank-16
`$481a`; `$0e64` called from bank-1 `$4e0c` / `$074a`; `$0ea9`
called from bank-1 `$4142`; `$0ecd` called from `$3548`).
`$0f74-$0f94` code (18 instrs; 3× memcpy via `$106e`, ends
`jp $106e`). `$0fa1-$0fc0` data (labels `$0fa1` — `ld de,$0fa1`
at `$0c9c`, source for a `$169c` transfer — and `$0fae` —
`ld hl,$0fae` at `$07f1`; the "code" decode is noise: `daa;
sbc h; ld bc,$a707…`). `$1075-$10aa` code (39 instrs;
`$1075` = 16-bit division helper, `$1092` = 5-byte add-HL-A
helper, `$1097` = `$c220` record scan). `$1e6b-$1e85` code (15
instrs; called from bank-1 `$411e`/`$5148`). `$3689-$3736`
data (labels `$370f` — read at `$338f`/`$33a7`/`$33c3` — and
`$3723` = PutNumberTiles digit table; ASCII digit / tile
data, `"//////02468:<>@B13579;=?AC"` at `$3723`).

§2 **Generator lesson — post-ret seeds need TRUE ret opcodes.**
Earlier survey scripts' `RET_OPS` also listed `0xE0`/`0xE8`/
`0xF0`/`0xF8`, which are LDH / ADD-SP / LDH / LD-HL-SP, NOT
rets — that seeds garbage decodes overlapping real
instructions (the spurious `"$0e6c: adc a"` over `$0e6b`'s
`ldh [$ff8f],a`). `tools/gen_slice28.py` uses only
`{C9,C0,C8,D0,D8}` and additionally filters post-ret seeds
that land inside an expected-`db` gap (a ret-terminated code
span followed by data would otherwise seed a garbage decode
that "covers" the gap — e.g. `$6335`, where `xor b` /
`ld hl,sp+$a8` chains through the 7 gap bytes to `$633c`).
Same lesson applies to any future `post_ret` use: check the
set before trusting it.

§3 **Door — static mapping narrowed; still NO live firing.**
The timer-22 `$75ea` handlers are entries **02, 04, 08, 09**
(`$6c7a`, `$6c8f`, `$6ca4`, `$6cb9` → the `$7b14`/`$7bda`/
`$7c3d`/`$7ca0` routines with the `$7b6e`/`$7c34`/`$7c97`/
`$7cfa` timer-22 writers). Handlers 13/14/15/16 are NOT
timer-22 (their blobs set sound IDs and `jp $0df4`; `$7e79`
writes `[$c70c]`, not `$c70b`). The `$750a` byte map gives the
record byte-1 values that select them: index 2 ← byte-1
16–19, index 4 ← 24–27, index 8 ← 38–41, index 9 ← 42–45.
So the live question is now precise: which interaction makes
the `$c117` record's byte 1 land in {16–19, 24–27, 38–41,
42–45}. LIVE (`gb_pcwatch`, bank-qualified, validated first
on the 600f idle run: `$0100` 1×, `$06bd` 1× at frame 234 —
identical to slices 26/27): in the play-right 5000f flow the
ONLY `$75ea` handler that fires is entry 0, the key pickup
(`$6b55`, 1× at frame 860, state 18 timer 8 — before any
player input, i.e. the attract demo's Mario, not the
player's); entries 01/02/04/06/07/08/09 are all 0. In the
idle 30000f attract run the demo picks up the key 12× (one
per attract cycle: frames 1196, 3748, 6298, 8859, 11420,
13971, 16523, 19075, 21638, 24201, …) and STILL never fires
a timer-22 handler or a door writer (`$6c7a`/`$6c8f`/`$6ca4`/
`$6cb9`/`$7c34`/`$7b6e`/`$7bd1` all 0). The attract demo
reaches the key every cycle but never the door — it dies or
loops first, or the demo's key pickup does not lead to the
door at all. The `$0859` gate was not re-run this slice
(slice 27's four runs stand: never opens). NO live door
firing in any run; the chain stays statically complete and
live-unobserved. The `$7b77`/`$7bd1` writer's entry is still
unverified (no handler pinned to `$7b77`).

§4 **Live validation of the carve.** Retry flow 15000f
(`gb_pcwatch`, bank-qualified): `$61b2@16` 17× (state 18
timer 1, frames 1188/1579/3486/3876/4359/6037/6427/6910/8590/
8982…), `$6b32@16` 5,036×, `$6d52@16` 15,426×, `$72e4@16`
5,033× — the pockets are live code, not dead bytes. `$617c`,
`$6b85`, `$649e` are 0× in this flow: real routines with
verified bank-0 callers (`$09cc`, `$0b0f`, `$0af7`) whose
paths do not run in the retry flow; live-or-dead unknown.
`$7c34@7` (door writer) 0×, as in slice 27.

§5 **Byte-match proof.** Clean `make` (`rm build/game.gb`
first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs
vs `roms/Donkey_Kong_World_Rev1_SGB.gb`. First-try match.

§6 **Nacre results.** Slice-5 regression: 600f `1cf92679…`,
900f `39ffd5ee…`, 3600f `88515f4e…`, 12000f `92d2e185…`, s8
`92d2e185…`, f0 `3390d763…`, f1 `1cf92679…` — ALL REGRESSION
CASES IDENTICAL. Slice-7 cases: retry 15000f `0d835d95…`,
mid5000 `2ab1bb5d…`, play-right `b3cb6c8b…`, death `632b2eaf…`
— ALL SLICE-7 CASES IDENTICAL. All canonical hashes match.

§7 **Verified vs inferred.** VERIFIED: every region's byte
coverage (generator asserts the uncovered set equals exactly
the expected db pockets); all six `call $0fd9` inline tables
and their entries; the `$6d67` table is ONE 40-entry table
(contiguity + no separate `$6d91` reader anywhere in the
ROM); the `$733b-$7dbd` data verdict (post-ret walks decode
as noise; `$7b86` entries point at data); the bank-0 carves
(all entries pinned by carved callers except as noted);
`$61b2`/`$6b32`/`$6d52`/`$72e4` firing live in the retry flow.
INFERRED / ENTRY-UNVERIFIED (code by decode + family, entry
not pinned): bank 16 `$61ac` (fall-through only), `$63d7`
(1-byte entry — `ret` — inside the `$61c1` span), `$6b6f`/
`$6b70` (1-byte-apart entries in the `$6b45` span), `$6b84`
(1-byte `ret` entry), `$1092` (5-byte helper, post-ret seed
only), `$7b77`/`$7bd1` (door writer, no handler pinned);
`$6485-$649c` / `$6335-$633b` / `$5fd3-$617b` internal
structure (plain `db`, no reader pinned). JUDGMENT CALLS:
`$61b5`/`$64a1`/`$6b39`/`$6b8c` table extents rest on the
entry-count reading (6/8/6/8 — the trailing entries are
1-byte `ret`s, which is what makes the extent checkable);
`$6d50`/`$6d51`/`$6b30`/`$6b31` as no-op `ret` entries rather
than data; `$0674-$067a` as the tail of STAT_0673 (STAT_0673
itself is 1 byte, `xor a`, at `$0673`).

## Slice 29 — DONE, byte-matching (2026-11-25) — THE FINISH: ZERO INCBIN

**`src/` has ZERO INCBIN.** `tools/count_curated.py` reports
524,288 / 524,288 (100.0%), remaining 0. Every byte of the
512 KiB ROM is now hand-labelled RGBDS source (code, data,
tables, or labelled `$ff` padding) — the loop's definition of
done. `src/` is 103,031 lines.

§1 **INCBIN conversion (32 ranges, 74,129 bytes).**
`tools/gen_slice29.py` reads every INCBIN line in
`src/banks.asm`, verifies FIRST from the ROM bytes that the
range is all `$ff` (refuses — exit 1, file untouched — any
range that is not), then rewrites each as a labelled
`ds $len, $ff` with a comment naming the bank and range
(e.g. `; Bank 4 $76b0-$7fff $ff padding`). Verified
32/32 ranges, 74,129 bytes, all `$ff` — independently
re-verified here, not taken on the coordinator's word.
`grep INCBIN src/*.asm` now matches only comments (stale
prose in older slice files + the conversion note in
`banks.asm` itself); zero INCBIN directives remain.
`tools/gen_banks.py` was patched the same day so a future
regen emits `ds` lines instead of INCBIN (verified:
`python3 tools/gen_banks.py` output is byte-identical to
the new `src/banks.asm`). No carved code or data was
touched; the conversion is purely the padding tails
(bank 0 `$3947-$3fff` + one tail per bank in 1, 2, 3, 4,
5, 6, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
22, 23, 24, 25, 26, 27, 28, 29, 30 — 32 ranges; banks 8,
10, 31 have no tail because they were already 100%
carved). Bank 11 is closed by this conversion (its only
remainder was the `$7e3d-$7fff` `$ff` tail) — all 32 banks
are now closed.

§2 **Byte-match proof.** Clean `make` (`rm build/game.gb`
first) rebuilds SHA-1
`397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, `cmp` zero diffs
vs `roms/Donkey_Kong_World_Rev1_SGB.gb`. First-try match.

§3 **Nacre results.** Slice-5 regression: 600f `1cf92679…`,
900f `39ffd5ee…`, 3600f `88515f4e…`, 12000f `92d2e185…`, s8
`92d2e185…`, f0 `3390d763…`, f1 `1cf92679…` — ALL REGRESSION
CASES IDENTICAL. Slice-7 cases: retry 15000f `0d835d95…`,
mid5000 `2ab1bb5d…`, play-right `b3cb6c8b…`, death `632b2eaf…`
— ALL SLICE-7 CASES IDENTICAL. All canonical hashes match.
Both suites were re-run on the final build after the
harness rebuild (§6) — same hashes.

§4 **Door — live attempt, NO-GO (honest, with new evidence).**
No live door firing in any run; the chain stays statically
complete and live-unobserved. What this slice adds is a
precise static verdict on WHY the timer-22 handlers never
fire in 1-1, plus the harness work that unblocks future
replays (§6).

(a) **The static verdict: no timer-22 `$0b` cell exists in
1-1.** `$6b0a` (bank 7) dispatches into `$75ea` ONLY when a
`$c117`-family record's byte 0 (type) is `$0b`; byte 1
(subtype) then indexes `$750a`. Live WRAM-map surveys
(`tools/survey29_map.py`, `tools/survey29b_map.py`) of the
1-1 map (`$c86d-$d86d`) at frame 2500 (idle), frame 3100
(play-right), and every 25 chunks of two `gb_play` runs
plus key collection: the ONLY type-`$0b` cells in 1-1 are
the parasol (subtypes 34–37 → handler 7), the top-right
pickup (32–33 → handler 6), the key (74–77 → handler 17),
and the `$5b` trigger (91 → handler 0) — 12 cells, none in
the timer-22 subtype ranges {16–19, 24–27, 38–41, 42–45}.
Timer-22-range subtypes DO exist in the map (24 cells,
subtypes 39/40, the two ladder columns at OAM x=32 and
x=96) but their type is `$00`, which `$6b0a` never
dispatches on. Zero `($82,$37)` cells at every observed
time, so the `$6331` post-key scan stays inert in 1-1.
The door trigger cell is therefore NOT in the 1-1 map as
loaded or as observed through key collection: either it is
written later (after all three pickups — the parasol was
never collected), or the timer-22 entry is not a map cell
at all in 1-1.

(b) **The map changes during play — the `$41` block.**
Diffing the map between frame 2500 and key collection
(`tools/survey29c_diff.py`) shows the key cells cleared
to `0001` (handler 17), one `$5b` cell consumed (`$c560`
1→0, `$c858` 3→2), and a NEW 7-cell block of type-`$0b`
subtype 65 (`$41`) at rows 5–7, cols 6–8 (OAM 48–64,
48–64 — the ladder top by the key niche). Subtype 65 →
`$750a[65]` = handler 14 (`$6d9f`), whose target `$7e43`
plays sound `$37`, builds a record via `$7e18`, and
`jp $0df4` (a score routine, +1) — NOT a door, and NOT
timer-22. Its writer is unidentified (not handler 0's
`$6b55` chain, not handler 17's `$7dbe` — neither writes
`$41` cells; it appears between `gb_play` chunks 50–75
in one run and not at all in the slice-29 run, so it is
not a pure function of the `$5b` trigger). The block is
never consumed in any dump, and handler 14 (`$6d9f`) is 0
in both slice-29 pcwatch replays — consistent with it never
firing, though no pcwatch run has yet watched it along an
autopilot run that actually reaches the block. The `$41`
block is a side mystery, not a door lead.

(c) **Fresh `gb_play` run (new post-key route).**
`gb_play orig save-prog1.sav 400 "" "56,136;56,56;88,60"
"56,56;40,56;32,56;32,32;16,32;8,32"` — post-key route
revised off the rendered map (`tools/survey29d_render.py`):
back along the key girder, UP the left ladder (x=32) to
the parasol, instead of the slice-11/12 pit route via
(24,72). Log: `build/nacre-test/slice29/play29.log`.
Key collected chunk 103 at (73,63). Post-key waypoints
0–2 (56,56 → 40,56 → 32,56) reached repeatedly, but
waypoint 3 (32,32) NEVER reached: Mario keeps falling
from the girder to (24–32, 88) and backtracking (14
backtracks, chunks 135–356). Final: 356 chunks, done=0.
No STAGE CLEAR. Same failure mode as slices 11/12 — the
climb from (32,56) up the col-4 ladder to (32,32) is what
the greedy cannot do; it falls instead. The parasol (and
whatever follows `$c858`→0) is still uncollected live.

(d) **pcwatch replays of the autopilot schedule.**
`gb_pcwatch` (validated first on 600f idle: `$0100` 1×,
`$06bd` 1× at frame 234, identical to slices 26–28),
8500f, play29 schedule, watching `$6c7a`/`$6c8f`/`$6ca4`/
`$6cb9` (timer-22 entries, bank 7), `$6d9f` (handler 14),
`$6b55` (handler 0), `$6dcf` (handler 17, key), `$7c34`
(door writer): ALL ZERO except `$6b55` 1× at frame 860
(the attract demo's `$5b` trigger, as in slice 28). The
key handler is 0 because the replay diverges before the
key (see §6) — the replay's Mario never reaches it, so
these zeroes are replay-divergence zeroes, NOT evidence
about the autopilot's own run. Do not cite them as "the
autopilot route fires no timer-22 handler" — the
autopilot's own firings were not instrumented (pcwatch
cannot watch a gb_play run in-process).

(e) **`$0859` gate (secondary target).** pcwatch on the
play29 schedule's exact-replay prefix (3400f, chunks
0–57), watching `$0859`@0, `$5a81`/`$5b71`/`$5bd1`@1,
`$08bd`/`$0b28`@0: ALL ZERO. The `$0859`/[$c809]-
dispatch sequence does not run at all on the player
route in 1-1; slice 26's finding stands (it runs only
in the state-18 attract flow, where its save branch is
never taken).

§5 **Verified vs inferred.** VERIFIED: the 32-range
all-`$ff` check (this script, from ROM bytes); zero
INCBIN directives; 100.0% curated; byte-match + both
Nacre suites on the final build; the 12-cell `$0b`
inventory of 1-1 at frames 2500/3100 and across two
`gb_play` runs (no timer-22 subtype among them);
subtypes 39/40 exist only in type-`$00` ladder cells;
zero `($82,$37)` cells at all observed times; handler
14/15/16 are score pickups (`$0df4` is a score routine —
read the code, not just the sound ID); the `$41` block
exists (7 cells, rows 5–7 cols 6–8) in one run's dumps
and never fires; the play29 autopilot outcome (key
chunk 103, done=0, waypoint 3 never reached). INFERRED:
that the `$41` block's writer is `$627b`/`$6331`-family
(no writer pinned — the `$6b55`/`$7dbe` exclusions are
verified, the positive attribution is not); that the
door cell appears only after all three pickups (no run
has collected the parasol, so this is a guess, not a
finding); the exact mechanism of the §6 sub-pixel
nondeterminism (1px split observed twice, cause not
pinned). CORRECTED this slice: slice 11 §5's "the
slice-11 run's key pickup fired with the `$5b` trigger
never having fired" does not match the on-disk dump —
the surviving `key_wram.bin` (overwritten by the
slice-12 run; the slice-11 dump is gone) shows `$c560`
1→0 and one `$5b` cell consumed by key collection, i.e.
the trigger HAD fired in that run. The prose was read
off play12's dump; the disk now holds the later run's.

§6 **Harness — two real fixes, one open problem.**
(1) **Window caps raised.** `tools/gb_headless.c`
(16 → 512 windows, spec buffer 512 → 8192) and
`tools/gb_pcwatch.c` (32 → 512, buffer 1024 → 8192).
A `gb_play` schedule runs to ~250 merged windows; the
old caps SILENTLY dropped the rest, so every schedule
replay before this slice was replaying a truncated
schedule. This is a likely contributor to the slice-8
replay divergence. Short specs are unaffected (windows
still OR per frame); both Nacre suites re-run clean on
the rebuilt `gb_headless` (§3). (2) **The +1 frame
shift.** Replaying play29's printed schedule unshifted
diverges at chunk 1 (auto (37,136) vs replay (38,136));
shifting every schedule window +1 frame (intro windows
unchanged) reproduces the autopilot EXACTLY through
chunk 57 — verified position-by-position at every chunk
boundary to frame 3369. So `gb_play`'s printed `f0` is
one frame ahead of the replay tools' frame counting; a
future replay must shift +1. (3) **Open: residual
sub-pixel nondeterminism.** Even with +1, the replay
diverges at chunk 58: auto (87,88) vs replay (96,88).
Worse, `gb_play`'s OWN backtrack replay disagrees with
its first pass — `left` from (96,88) gives (87,88) the
first time and (88,88) after the backtrack, same integer
position, same action. So the state that matters (Mario's
sub-pixel position, or an RNG/enemy phase) differs
between passes that look identical at integer precision.
Cause NOT pinned (candidates: sub-pixel phase from the
±1 frame alignment, an RNG state that is not reset by
`gb_create`, or an enemy/record phase). Consequence: no
fixed open-loop schedule can be replayed exactly past
~chunk 57, and a winning door schedule cannot be verified
by replay until this is found. The fix belongs in the
harness (dump full Mario-record bytes at chunk ends, or
find the nondeterministic state), not in more waypoints.
`tools/gb_pcwatch` binary was deleted after use (not
git-ignored), as in slices 26–28. New tools this slice:
`tools/gen_slice29.py`, `tools/survey29_map.py`,
`tools/survey29b_map.py`, `tools/survey29c_diff.py`,
`tools/survey29d_render.py`. The play29 schedule is saved
at `build/nacre-test/slice29/play29.spec` (+1 variant
`play29.spec+1`); the slice-12 `play/` dumps it overwrote
were backed up first to `build/nacre-test/slice29/
play12-backup/`.

## Next slices (priority order)

1. **Gameplay: complete stage 1-1 live (key -> door).**
   Slice 12 CLOSED two of slice 11's three door leads by
   killing them as door mechanisms, and the third is now
   the only live one. (a) The `$6331` scan is carved
   (bank 7 `$627b-$63c3` + `$63f4-$643e` + `$664e`/`$714c`,
   `$4827` table): it is real, gated on `[$dd18]==$0a`
   + `[$c21c]` + `[$ff94]` bit 5 + `[$c20d]==0`, and its
   hit writes `[$c830]`/`[$c835]=$5f` — which slice 12
   proved is a SOUND ID (see below), not a door signal.
   Slice 13 surveyed ALL 101 loadable stages: `($82,$37)`
   cells exist in 6 stages (44, 45, 49, 50, 80, 82) and
   the `$5b` trigger in 5 (4, 6, 15, 26, 41), and NO
   stage has both — so the scan is inert in every stage,
   not just 1-1. The `$4827` table's other entries are
   now carved (slice 13 §1); the only `$0a` setter is
   the `$6bf2` tail. (b) Collecting
   all three `$0b` pickups is DEAD as a door lead:
   `$7e07`'s `$44` is a sound ID (bank-2 `$47fc` entry
   67 → `$5480`), consumed by the bank-2 timer tick.
   The parasol is still uncollected live (two slice-12
   `gb_play` runs both died in the pit below it; it
   needs a precision jump into OAM x 8–23, y 32–47 —
   a hand-written schedule or jump-aware search, not
   another waypoint tweak), but collecting it would only
   play the jingle. (c) RESOLVED (slice 12 §3): the
   readers of `[$c82f]`/`[$c835]` are the bank-2 tick
   (`$45a9`/`$4677`, `$47fc` sound table) and the bank-3
   tick (`$45a9`, `$48f1` song table); `$c82d-$c835`
   is a sound-request queue, `$c836-$c838` the music
   request. Slice 13 resolved the timer-22/23 mechanism
   (slice 13 §3) and the C==4 entry condition (slice 13
   §4): timer 22 comes only from the `$75ea` handler
   tails (tiles `$a5`/`$a6`/`$a7`/`$eb`/`$ec`); timer 23
   has no literal setter and its only path is the
   `$0a2c` `[$c70b]` restore; every C==4 queue entry is
   preceded by a (1,B) load, and 1-1's clear chain runs
   23→24→42→43→44→45→0 without timer 33. Slice 14 CLOSED
   the two remaining candidates: state-20 timer 23 is
   VERIFIED unreachable in both states (the `$0a2c`
   restore can yield only {3–10, 18, 19}; the 19–26 chain
   needs `[$c70f]` bit 0, which the attract demo's own
   soft reset wipes before any state-20 visit — both
   writes pinned live by `gb_watch`), and `$5083` is
   VERIFIED orphaned dead code with no entry, not a
   mechanism. The new lead (slice 14 §5): the per-frame
   `$2a0a` dispatch into bank 8 `$7526` / bank 10 `$7730`
   (runs every frame in 1-1, fed by the `$c200` record
   handler 17 creates on key pickup), and the clear
   chain's ENTRY itself — timer 33 is set only in the
   timer-23/26 bodies, timer 42 only in timer-24/26/40,
   so what starts 33→40→42→43→44→45→0 is now the open
   question. The `$0f15` SRAM stage-record writer (called
   from timer 23/26) is carved and is what the game does
   WHEN a stage clears — but its callers are unreachable
   via known paths. Slice 15 carved the `$2a0a` dispatch
   whole (bank 0 `$2b48` table, decimal bank 10 `$7730`
   + tables + spawn, bank 8 `$5e37`/`$7311`/`$7526` and
   the `$2b48`-entry handlers) and CLOSED timer 13 as a
   1-1 clear-chain entry: its only `$2b48` setters are
   entry 34 (bank 8 `$6d8a`→`$6ecd`) and entry 53 (bank
   `$0a` `$5cd8`→`$5c4f`/`$5c97`), both gated on
   `[$c109]` bit 3, and no 1-1 record has `[$c105]`=34
   or 53 (live values {0,1,2,3,6,7,32,45,72}); and its
   body `$0968` runs bank-16 `$5a11`, which sets only
   timers 1/12 — so timer 13 resolves to resume or
   death, never to 23/26/33/42 (slice 15 §3). The new
   lead (slice 15 §8): the bank-`$1f` `$2b48` handlers
   actually firing every frame in 1-1 (entries 7/32/45/
   72: `$40e1`/`$48e3`/`$49b0`/`$58e2`) plus bank-8
   `$5f5c` (entry 1), then the decimal-bank-`$0a`
   handler set (`$4000-$7072`, incl. the `[$c109]`-bit-3
   setters `$4add`/`$4d58` and what arms a record, and
   which stages spawn 34/53 records).
   Slice 16 carved all of that (bank `$1f` entries 7/32/
   45/72 + 73 — `$58e2` is entry 73, not 72, see slice 16
   §2 — bank-8 entry 1's table + routines, the full
   bank-`$0a` handler set, bank-16 `$5a11`/`$4e89`) and
   CLOSED it as a door lead: none of the carved handlers
   writes a clear-chain timer (bank-16 `$5a11` sets only
   timers 1/12, verified from the carved code), the
   sound writes are sound IDs (`$64`/`$42`/`$12`), and
   the `[$c109]`-bit-3 setters `$4add`/`$4d58` have no
   direct caller anywhere in the ROM. Slice 17 finished
   the table — 94/94 carved — and CLOSED it as a door
   lead too: no handler in bank 9 or bank `$1f` writes
   timer 23/26/33/42 (the only two `ldh [$ff90],a`
   sites in the whole bank-31 carve are `$4b70`/
   `$7847`, both literal 13; bank 9 has none), timer 13
   still resolves only to timer 1 or 12, and entries
   66/67 are a real path (bank-0 trampolines → bank 12),
   not a quirk. What slice 17 DID pin: timer 13 has
   FOUR `$2b48` setters, not two (slice 15's "exactly
   two" was wrong — entry 46 `$4aee` disarms bit 3 and
   sets timer 13, entry 92 `$780b` sets timer 13 on a
   position gate near the key niche), and the arming
   half is entry 91 `$6c60` (bit 2 set + bit 3 clear →
   fall through to `$6ca9`, `set 3,[$c109]` — inline,
   not a subroutine). The open link: whether a 91-armed
   record ever becomes a 46 record (no `[$c105]`
   rewrite to 46 exists; 1-1 never shows 46/91 live).
   Slice 18 CLOSED the 91→46 link as DEAD (proven: no
   `[$c105]` rewrite to 46 exists anywhere in the ROM;
   the `$7730` table writes only `$3f`/`$36`; type-46
   lives only in B1 and type-91 nowhere in the 101
   surveyed stages; `$7378`'s variable path is a no-op
   for 46 and its routine is orphaned) and carved the
   bank-9/bank-31 gaps (bank 9 `$684f-$6907`, bank 31
   `$4499-$4566`, `$506c-$5200`, `$6244-$64ed`,
   `$6fde-$704f`, `$708f-$70de`, `$7a12-$7bf5`).
   Slice 19 CLOSED the three remaining leads from slice 18:
   bank 29's sprite table + blocks are carved (121 blocks)
   and its selector is PINNED (state-16 steps call `$10d5`
   → bank 29; everything else calls `$10dd` → bank 11;
   live probe 1770 vs 21756 executions in a 6000f run);
   the `$7378` routine's entry is RESOLVED ([$c10a]=4 of
   the `$7073` table, read by the `$2b48`-entry-63 handler
   `$705f`; live in stage B55: `$705f` 66×, `$7369` 8×,
   `$7378` 2× with bank=10) and the `$70df-$723d` remainder
   is carved (entries 14–18 of the `$6a98` table, which is
   19 entries, not 9 as slice 17 had it). None of the
   slice-19 carves writes a clear-chain timer, so the
   door/clear-chain entry is still NOT found and no
   completion attempt was run (NO-GO, no new door lead).
   Slice 20 CLOSED both of those leads as carves — bank 31's
   26 gaps (978 bytes) and bank 10's `$480a-$705e` region
   (10,344 bytes) are now carved, both banks 100% — and
   neither writes a clear-chain timer, so the door /
   clear-chain entry is still NOT found (slice 20 §4).
   Remaining door leads: a fresh look at what actually
   sets `[$c105]`=63 records in play (only B55 is known
   to carry one), and the `$7e3c` table's unidentified
   reader in bank 10 (slice 20 §4). Slice 21 adds: no
   handler in bank 9 writes a clear-chain timer; the
   `$68d7`/`$6d6d` entry question and the A 197–207 table
   hole are the new open notes (slice 21 §3/§5). Slice 22
   SETTLES both: the `$664a`/`$6d33` tables are 11 entries, not 10
   — `[$c10a]` reaches 10 live (3 hits in a 30000f idle run, writer
   pinned to the bank-0 `$2a39` `$c200`-record copy loop), so
   `$68d7`/`$6d6d` are entry 10; and genuine `$db15` byte1s max at
   `$b0` in sampled flows (the only ≥`$f5` values are a transient
   `$ff` fill in state 18 that `$0bff` never sees, since its only
   caller chain runs in state 16) — the A 197–207 hole is not
   reachable via live records in those flows. Bank 4 itself writes
   no clear-chain timer (it has no code), so the door/clear-chain
   entry is still NOT found and no completion attempt was run (NO-GO,
   no new door lead). Slice 26 maps the `[$c70b]` timer
   save/restore mechanism whole (6 writers / 4 readers) and finds
   its newest reader at bank-1 `$5bd1`, in the `$5a81`/`$5b71`
   [$c809]-dispatch sequence entered from State16Table[41]: the
   `$0859` routine (State16Table[6], shared with state 18) saves
   the current timer and sets timer 41, the sequence steps
   `[$c809]` through its phases, and `$5bd1` restores the saved
   timer (statically normally 6). It is NOT a timer-33/42 lead:
   live `gb_pcwatch` (15000f retry flow) shows the sequence
   never fires there (`$5a81`/`$5b71`/`$5bd1`/`$08bd`/`$0b28`
   all 0 hits; `$0859` fires 2,262× in state 18 timer 6 but its
   save branch is never taken), while `$5d21` (23×) and `$5ceb`
   (6×) run on every stage load in state 18 timer 1. Open: which
   flow takes the `$0859` gate, and what `$5bd1` restores live.
   Slice 28 narrows the door statically and tests it live: the
   timer-22 `$75ea` handlers are entries 02/04/08/09, selected
   by `$c117` record byte-1 values {16–19, 24–27, 38–41, 42–45}
   via the `$750a` map (handlers 13/14/15/16 are NOT timer-22 —
   sound IDs + `jp $0df4`). Live, the ONLY `$75ea` handler that
   ever fires is entry 0, the key pickup (`$6b55`): 1× in
   play-right 5000f (frame 860, before player input — the
   attract demo), 12× in idle 30000f (once per attract cycle);
   entries 02/04/08/09 and the door writers `$7c34`/`$7b6e`/
   `$7bd1` are 0 in retry 15000f, play-right 5000f, and idle
   30000f. The attract demo reaches the key every cycle but
   never the door. The remaining static link is what makes the
   `$c117` record's byte 1 land in the timer-22 ranges — i.e.
   which tile interaction that is — and the live link is any
   run (player or demo) that gets Mario from the key to the
   door.
   Slice 29 CLOSES the static link in the negative and leaves
   the live link open: a live-map survey of 1-1 (frames 2500/
   3100, two full `gb_play` runs, key collection) proves NO
   type-`$0b` cell in 1-1 carries a timer-22 subtype — the
   only `$0b` cells are the parasol (34–37), top-right
   (32–33), key (74–77), and `$5b` trigger (91); the
   timer-22 subtypes 39/40 exist only in type-`$00` ladder
   cells `$6b0a` never dispatches on; `($82,$37)` cells are
   0 everywhere. A fresh `gb_play` run with a revised
   post-key route (up the left ladder to the parasol, not
   the pit route) collected the key at chunk 103 but never
   reached the (32,32) ladder waypoint — same failure mode
   as slices 11/12, done=0. The door trigger cell is not in
   the 1-1 map as observed: it is written later (after all
   three pickups — parasol still uncollected, guess not
   finding) or it is not a map cell in 1-1 at all. The
   `$0859` gate is 0 on the player route too (slice 29 §4).
   The map DOES change during play (a 7-cell `$0b`/`$41`
   block appears at the ladder top in one run — handler-14
   score cells, writer unidentified, never fired). Harness
   state after slice 29: press-window caps raised 16/32 →
   512 (old caps silently truncated every schedule replay
   before this slice); a +1 frame shift aligns a replay
   exactly through chunk 57; a residual sub-pixel
   nondeterminism (gb_play's own backtrack replay gives
   (87,88) vs (88,88) for the same action from the same
   integer position) blocks exact open-loop replay past
   ~chunk 57 — that, not waypoints, is now the blocker for
   verifying any winning door schedule by replay.
   Once a run completes, verify the winning schedule by
   replaying it with `gb_headless` on both the original
   and rebuilt ROMs (framebuffer hash + state trace +
   save identical) — but note the slice-8 schedule-replay
   divergence (the SCHEDULE drifts slowly through
   gb_headless, so verify inside gb_play itself or find
   the divergence source first). `gb_play`'s dump dir is
   now `build/nacre-test/slice12/play/` (slice 12 fixed
   the hardcoded slice-9 path) and its waypoint radius
   is 6px (slice 12: slower pre-key route, key at chunk
   88 not 31 — the radius is not the fix; the greedy
   needs ladder/ledge awareness).
2. **Bank-29 sprite blocks — DONE (slice 19).** Table + 121
   blocks carved (`src/bank29.asm`, `src/bank29slice19.asm`);
   selector PINNED (state-16 steps → bank 29 via `$10d5`,
   everything else → bank 11 via `$10dd`; live probe counts
   1770 vs 21756). (The stage-table layout is
   RESOLVED — slice 8 §1 — and the death->timer-12
   instruction is PINNED — slice 8 §2. The `$56c3` entry
   mechanism is RESOLVED — slice 10 §1 — and the key pickup
   is PROVEN — slice 10 §3.)
3. **Roles for the carved code.** Bank 7 `$6f62` and bank 23
   `$7722` are pinned (slice 7 §2); bank 10 `$51c8`/`$5349`
   are pinned (slice 8 §2); bank 7 `$6b55` (key pickup) and the
   `$75ea` handler families are pinned (slice 10 §4). Still open:
   bank 7 `$4794`, `$77a9`/`$78ba` roles from slice 4; the
   `$3414` dispatcher and the `$b4ca-$b927` SRAM writer are resolved
   (slice 6 §2, §4).
4. **Further carves.** Whole banks 6, 17,
   19–22, 25–28, 30 are now CLOSED (slice 24 — 11 banks in one
   slice, all data, no code; curated 65.8%). **Banks 5, 12, 18,
   23, and 24 are now CLOSED (slice 25 — stage / stream /
   attract / credits data; curated 75.9%).** Banks closed so
   far (27): 1, 2, 3, 4, 5, 6, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
   22, 23, 24, 25, 26, 27, 28, 30, 31 (slice 26 adds 1, 2, 3, 16).
   Bank 7 is now
   extensively carved — slices 4/5/10/11; bank 8 is now
   substantially carved — slices 11/12/15; **bank 9 is now CLOSED
   except the `$ff` padding tail — slice 21**; **decimal bank 10 and
   bank 31 are now CLOSED, 100% carved — slice 20**; **bank 4 is now
   CLOSED as tile data except the `$ff` padding tail — slice 22**;
   **banks 13, 14, and 15 are now CLOSED as transfer/stream data
   except their `$ff` padding tails — slice 23**;
   **banks 6, 17, 19–22, 25–28, and 30 are now CLOSED as stage /
   tile / stream / transfer / sprite / packet data except their
   `$ff` padding tails — slice 24**;
   **banks 5, 12, 18, 23, and 24 are now CLOSED as stage /
   stream / attract / credits data except their `$ff` padding
   tails — slice 25**; **bank 1 code now reaches $5a80 — slice 25**;
   **banks 1, 2, 3, and 16 are now CLOSED — slice 26 (song/SFX
   data, the bank-16 dispatcher, and the bank-1 [$c809] dispatch
   code; curated 83.9%)**. Banks closed so far (27): 1, 2, 3, 4,
   5, 6, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
   24, 25, 26, 27, 28, 30, 31. Next candidate by dependency
   (slice 26 §6): the bank 7 gaps (3,379 B) and bank 8 gaps
   (6,395 B) — the only non-`$ff` work left — then the bank-0
   tail `$3947–$3fff` and bank 11 `$7e3d–$7fff`. The `$2b48` table is DONE (94/94, slice 17) — it is no
   longer a lead. The 91→46 link is DEAD (slice 18 §1).
   The bank-11 sprite blocks are DONE (slice 18 §2). The
   bank-9/bank-31 gaps are DONE (slice 18 §3). Bank 29's
   sprite table + blocks are DONE (slice 19 §2). The
   `$7378` routine's entry is RESOLVED (slice 19 §3) and
   the `$70df-$723d` remainder is carved (slice 19 §4).
   Bank 31's 26 gaps and bank 10's `$480a-$705e` region
   are DONE (slice 20 §1–§2). Bank 11 `$4000`, bank 18 `$4934`, bank 24
   `$4934`, bank 10 `$51c8-$59f1`, bank 12 `$5917-$5dbc`, bank 9
   `$4000-$4020`/`$418b-$4690`/`$63f3-$6401`/`$6480-$6484`,
   bank 0 `$17eb-$1d06`, bank 7
   `$63c4`/`$6b55-$6e8b`/`$750a-$75ea`, bank 8
   `$4000-$4aec`/`$4aed-$4b62`/`$5409-$5808`, bank 7
   `$41dd-$4793`/`$7d96-$7e06`, and bank 16 `$4af0-$4e88` are
   done (slices 7–11). Slice 12 adds: bank 2 `$47fc-$48e9`
   (sound table), bank 3 `$48f1-$4942` (song table), bank 7
   `$4827-$4840`/`$627b-$63c3`/`$63f4-$643e`/`$643f-$6452`/
   `$664e-$66c9`/`$714c-$7167`, bank 8 `$4b63-$5408` (class
   byte tables). Slice 15 adds: bank 8
   `$5e37-$5efd`/`$5efe-$5f5b`/`$5f5c-$5f6a`/`$609d-$60e8`/
   `$6110-$611e`/`$6274-$6282`/`$63b5-$63ef`/`$6443-$6466`/
   `$6467-$646c`/`$6473-$6667`/`$6668`/`$67bd-$67cb`/
   `$68b8-$68ee`/`$69af-$69bd`/`$6a25-$6a33`/`$6abb-$6ac9`/
   `$6d8a-$6da9`/`$6daa-$6db5`/`$6db6-$6f64`/`$6f65-$6f7a`/
   `$6f7b-$7291`/`$7310-$74f3`/`$7526-$7587`/`$7602-$7629`/
   `$7685-$76b5`/`$76e3-$7740`/`$7741-$7746`/`$7747-$77d9`/
   `$77da-$7819`, decimal bank 10 `$4ff2-$4ffe`/
   `$5021-$5084`/`$5c4f-$5cf7`/`$5cf8-$5d07`/`$759a-$75af`/
   `$7730-$7814`/`$7815`/`$7816-$787c`/`$787d-$789e`/
   `$7c57-$7caf`/`$7e50-$7ead`/`$7eae-$7f43`, bank 0
   `$2b48-$2c61` (the `$2a0a` dispatch table). Slice 16
   adds: bank 31 (`$1f`) `$40e1-$40ef`/`$40f0-$40f5`/
   `$40f6-$414d`/`$48e3-$4931`/`$49b0-$49be`/`$49bf-$49c2`/
   `$49c3-$4a94`/`$589c-$58aa`/`$58ab-$58ae`/`$58af-$58e1`/
   `$58e2-$58fd`/`$58fe-$590d`/`$590e-$5a3b`/`$7ca1-$7ce1`/
   `$7d83-$7db8`/`$7e07-$7e43`/`$7e7e-$7ea5`/`$7f01-$7f5e`,
   bank 8 `$5f6b-$5f7a`/`$5f7b-$609c`/`$60e9-$610f`/
   `$63f0-$6442`, decimal bank 10 `$4000-$46e2`/
   `$46e3-$47a2`/`$47a3-$4809`/`$4add-$4ae2`/`$4d58-$4d5d`/
   `$4dbe-$4e55`/`$5192-$51a0`/`$51e0-$5211`/`$522b-$524a`/
   `$532b-$534a`/`$5412-$5420`/`$568c-$56b0`/`$56db-$56fa`/
   `$57bb-$5893`/`$5909-$5917`/`$5d08-$5d5d`/`$5d86-$5e09`/
   `$5e88-$5ec9`/`$60f3-$612d`/`$63a3-$6413`/`$6582-$65a1`/
   `$678c-$67ab`/`$69be-$69dd`/`$6af9-$6b07`/`$6d77-$6d99`/
   `$6e42-$6e61`/`$6f3d-$6f65`/`$705f-$7072`/`$7951-$79e9`/
   `$7ab8-$7b11`/`$7b3f-$7b6b`/`$7c24-$7c56`, bank 16
   `$4993-$49c3`/`$49c4-$49c7`/`$49c8-$4a17`/`$4a18-$4aee`/
   `$4aef`/`$4e89-$4eb1`/`$5a11-$5a17`/`$5a18-$5a25`/
   `$5a26-$5a4e`/`$5a4f-$5a58`/`$5a59-$5b3f`/`$5b40-$5b45`/
   `$5b46-$5c05`/`$5c06-$5c15`/`$5c16-$5d51`/`$5d52-$5d57`/
   `$5d58-$5e03`/`$5e04-$5e0d`/`$5e0e-$5f16`/`$5f17-$5f1e`/
   `$5f1f-$5fd2`. Slice 17 adds: bank 9 `$6490-$64ca`/
   `$6574-$6649`/`$664a-$6659`/`$6660-$6695`/`$6696-$66b6`/
   `$66b7-$684e`/`$6908-$6961`/`$696b-$6999`/`$69ac-$6a07`/
   `$6a11-$6a3f`/`$6a53-$6a7c`/`$6a9c-$6ac7`/`$6ae7-$6b42`/
   `$6b4c-$6b7a`/`$6b8d-$6be8`/`$6bf2-$6c20`/`$6c34-$6c5e`/
   `$6c7e-$6ca9`/`$6cb7-$6d32`/`$6d33-$6d42`/`$6d49-$6d58`/
   `$6d5b-$6d6a`/`$6d8b-$6d99`/`$6d9a-$6d9d`/`$6d9e-$6dd3`/
   `$6dd4-$6ddf`/`$6de0-$6e62`/`$6e6a-$6e93`/`$6eb1-$6ed8`/
   `$6f34-$6f64`/`$6f9b`/`$6f9c-$6fab`, bank 31 (`$1f`)
   `$4000-$4052`/`$4053-$4058`/`$4059-$40e0`/`$414e-$4161`/
   `$4162-$416b`/`$416c-$41fa`/`$41fb-$4204`/`$4205-$4498`/
   `$4567-$4575`/`$4576-$457b`/`$457c-$467e`/`$4689-$46bf`/
   `$46c0-$46c7`/`$46c8-$48c6`/`$4932-$4940`/`$4941-$4944`/
   `$4945-$49af`/`$4a95-$4aa3`/`$4aa4-$4aa9`/`$4aaa-$4c9b`/
   `$4cd4-$4ce3`/`$4ce4-$4ce9`/`$4cea-$4d89`/`$4da6-$4db4`/
   `$4db5-$4dba`/`$4dbb-$4e3f`/`$4e40-$4e47`/`$4e48-$4f9a`/
   `$4fb9-$4fd2`/`$503c-$506b`/`$5201-$520f`/`$5210-$5217`/
   `$5218-$53d9`/`$53da-$53df`/`$53e0-$5406`/`$540e-$5444`/
   `$544b-$5463`/`$5464-$5467`/`$5468-$55d7`/`$55d8-$55dd`/
   `$55de-$56c4`/`$56c5-$56ce`/`$56cf-$57a0`/`$57c1-$589b`/
   `$5a3c-$5a8a`/`$5a8b-$5a90`/`$5a91-$5b5a`/`$5b5b-$5b6c`/
   `$5b6d-$5e81`/`$5e82-$5e87`/`$5e88-$5f37`/`$5f38-$5f49`/
   `$5f4a-$6151`/`$616e-$6187`/`$61a5-$6243`/`$64ee-$64fd`/
   `$64fe-$650b`/`$650c-$66b1`/`$66b2-$66bb`/`$66bc-$67f7`/
   `$68dc-$68f9`/`$68fa-$68ff`/`$6900-$6a97`/`$6a98-$6aa9`/
   `$6abe-$6b52`/`$6b6f-$6cc1`/`$6cc2-$6cc6`/`$6cc7-$6d8d`/
   `$6d8e-$6da1`/`$6daa-$6df5`/`$6e0a-$6e83`/`$6e95-$6eb9`/
   `$6f89-$6fdd`/`$7050-$708e`/`$723e-$7305`/`$7316-$7324`/
   `$7325-$7350`/`$7351-$7370`/`$7374-$73d0`/`$73d4-$7433`/
   `$7437-$74d4`/`$74d8-$775e`/`$7775-$792d`/`$7934-$7a11`/
   `$7bf6-$7ca0`/`$7ce2-$7d82`/`$7de4-$7e06`/`$7ea6-$7f00`,
   bank 0 `$0f95-$0fa0`. Slice 28 adds: bank 16
   `$5fd3-$7dbd` is now carved for real (code + six
   `call $0fd9` inline tables + data — slice 26's "pure
   data" verdict was wrong at `$617c`/`$61b2`/`$6b32`/`$6b85`,
   and the `$6d67` table is ONE 40-entry table, not two),
   and bank 0's last `main.asm` INCBINs are gone (`$0674`,
   `$0df4`, `$0f74`, `$0fa1`, `$1075`, `$1e6b`, `$3689` —
   609 B). What remains is the door (§1) and the `$0859`
   gate, plus the replay-nondeterminism blocker (§1, slice 29
   §6) — there is NO non-`$ff` carve left anywhere and NO
   INCBIN left anywhere. Slice 29 closed the last of it:
   all 74,129 B of `$ff` padding tails are now labelled
   `ds $len, $ff`, `src/` is 524,288/524,288 (100%), and all
   32 banks are closed (bank 11's only remainder was its
   `$ff` tail). The disassembly as a byte-coverage project
   is DONE; what is left is the scientific item (the door,
   live) and the harness item (exact replay).
   The `$2b48` table is DONE (94/94, slice 17) — it is no

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
- Open (slice 12, not blocks): the door position/trigger is
  not positively identified — the `$c0-$c3` block is
  ELIMINATED as the tile-path door (slice 9 §5), the `$75ea`
  interaction system is mapped and carved (slice 10 §4), and
  slice 11 proved all its `$0b` handlers (6/7/17/0) are score
  pickups or a record deactivation, so the door is not a
  `$0b` handler. Slice 14 adds: timer 23 VERIFIED
  unreachable in both states (slice 14 §3 — the `$0a2c`
  restore can yield only {3–10, 18, 19}; the 19–26 chain
  needs `[$c70f]` bit 0, wiped by the attract demo's own
  soft reset before any state-20 visit); `$5083` VERIFIED
  orphaned dead code, not a mechanism (slice 14 §4); the
  `$0f15` SRAM stage-record writer is carved (called from
  timer 23/26 — what the game does WHEN a stage clears,
  but its callers are unreachable via known paths); the
  clear chain's ENTRY (timer 33/42) is now the open
  question; the next lead is the per-frame `$2a0a` dispatch
  into bank 8 `$7526` / bank 10 `$7730` (slice 14 §5). Slice
  15 adds: timer 13 VERIFIED unreachable in 1-1 as a
  clear-chain entry (slice 15 §3 — its only `$2b48`
  setters, entry 34 → bank 8 `$6d8a`→`$6ecd` and entry 53
  → bank `$0a` `$5cd8`→`$5c4f`/`$5c97`, both gated on
  `[$c109]` bit 3, need a `[$c105]`=34/53 record no 1-1
  record carries; and its body `$0968` runs bank-16
  `$5a11`, which sets only timers 1/12); the `[$c109]`
  bit-3 setters (`$4add`/`$4d58` bank `$0a`, `$6ca9` bank
  31) sit in the uncarved bank-`$0a` handler set / bank 31;
  the `$5cf8`-table routines `$5d08`/`$5d48`/`$5d86`/`$5d9f`/
  `$5e88`/`$5e97` are uncarved; bank `$1f` (entries
  7/32/45/72, the per-frame behavior actually firing in
  1-1) is almost entirely uncarved; the 2990-frame `$0a`
  re-set of `[$dd18]` in the slice-15 replay is
  unexplained (open loose end, not the door). The
  `$29c0`/`$29ee` queue scans are orphaned (no caller). No
  run has completed 1-1 yet (key collected,
  play12/13/14 all end at the block, done=0; the slice-11
  parasol route died at (26,88); the slice-12 parasol
  routes both died in the pit below the parasol, key at
  chunk 88). Bank-1 `$56c3`'s entry mechanism is RESOLVED
  (slice 10 §1: PostStart table entry 33 — NOT a door
  trigger); timer 23 has no literal setter (see slice 10
  §2). The `[$c70f]` bit-0 setter is RESOLVED (slice 9 §3:
  bank 23 `$7337`). The bank-11 table's extent (128 entries)
  is inferred, not verified against live record[0] values.
  Stage-table records B=97..105 do not fit the
  (world,stage) pattern — role unresolved. The bank-10
  `$4031` routine's entry mechanism is unverified.
  Slice 12 NOT pushed (coordinator handles pushes).
- Slice 16 adds: the bank-`$0a` handler set is DONE
  (2,304 instrs; `$2b48` entries 66/67 excepted — ROM0
  targets `$33e3`/`$33ef`); the `$5cf8`-table routines
  `$5d08`/`$5d48`/`$5d86`/`$5d9f`/`$5e88`/`$5e97` are
  carved; bank `$1f` entries 7/32/45/72 (+73 — `$58e2`
  is entry 73, not 72, correcting slice 15 §8) are
  carved; bank-16 `$5a11`/`$4e89` is carved and slice
  15's "sets only timers 1/12" is VERIFIED from the
  carved code (all 13 literal writes are `$01`/`$0c`).
  The `[$c109]`-bit-3 setters `$4add`/`$4d58` have NO
  direct caller anywhere in the ROM (whole-ROM byte
  search, zero hits) — what arms a record is still
  open. The `$2b48` table is 54/94 carved; the remaining
  40 (bank 9's 3, bank `$0a` 66/67, bank `$1f`'s 35) are
  the next door lead. `$5d48`'s `$33` to `[$c836]`
  (music-request field) exceeds the 41-song table —
  role unverified.
- Slice 17 adds: the `$2b48` table is DONE (94/94) —
  bank 9's three entries, bank `$0a` 66/67 RESOLVED as
  a real path (bank-0 trampolines → bank 12, not a
  table quirk), and bank `$1f`'s remaining 35 are
  carved; bank 0 `$0f95-$0fa0` is carved. Timer 13 has
  FOUR `$2b48` setters, not two (slice 15's "exactly
  two" was wrong): entry 46 `$4aee` (disarms bit 3,
  sets timer 13) and entry 92 `$780b` (position gate
  near the key niche, sets timer 13) join entries 34
  and 53. The arming half is entry 91 `$6c60` — bit 2
  set + bit 3 clear falls through to `$6ca9`
  (`set 3,[$c109]`, INLINE, not a subroutine —
  slice 15's "third setter" framing was wrong) — and
  entry 91's return `$5b55` clears bit 3. Whether a
  91-armed record ever becomes a 46 record is OPEN (no
  `[$c105]` rewrite to 46 exists; 1-1 never shows 46/91
  live). `$4add`/`$4d58` STILL have no direct caller
  (re-verified: `$4add` zero hits anywhere, `$4d58` one
  hit inside bank-29 data). No handler in this slice
  writes timer 23/26/33/42 — the door/clear-chain entry
  is still NOT found, and no completion attempt was run
  (NO-GO, no new door lead). The `$6dd4` 12-byte blob's
  meaning and the `$80`/`$33` to `[$c836]` (both out of
  the 41-song range) are unverified.
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
