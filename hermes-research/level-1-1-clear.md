# Rivet: key pickup and stage 1-1 door, 2026-11-24

## Scope and reproducibility

Rivet commit `68290f35967d2323b976f03229fda43ee1c2acc4`. Experimental, unversioned Nacre core at `/srv/agents/workspace/bunsen/experiments/graphify-nacre/paired-test/plain/workspace/repo`. The test ROM was the locally rebuilt image matching the expected SHA-1 `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`, not an independently obtained original. Progress-1 battery save was recreated using the project fixture generator, and prior f1/mid5000 frame hashes matched the log (see `door-probe-2026-11-24.md`). ROM and save are not included here.

Input schedule `carry-route.spec` was extracted from a real `play_carry.c` run, and independently replayed through both frame-stepped `gb_headless` and a corrected instruction-observing probe (`probe_transitions.c`). The former produced the `door-result.trace` and latter `clear-transitions.log`. PC watch uses actual `gb->cycles` per-frame targets; the original pcwatch oversteps.

## Observations

- Frame 2949: while Mario stands on the large key-shaped item, B press causes bank 7 `$4b47` to write `$dd18` 00→03. Corrected probe observes bank 7 PCs `$4a51`, `$4a75`, `$4a8b`, `$4b47` in the same frame. Screenshots show Mario subsequently holding the key overhead (`pickup-b.png`). Bank-7 source `$4a51` tests low five bits of a nearby collision record against 7; `$4a75` onward updates the map. The frame-0 map has key-area cells of type `$47` (low five bits 7), a supported static/live association. A control with the identical input schedule except omitted B never hits `$4a51`, `$4a75`, or `$4b47` in the observed window.
- Frame 3345: after carrying the key to the door, state-16 timer 10→25; instruction at bank 16 `$4126` is the observed writer. Source immediately before `$4126` loads A=$19; this is a different path from the previously proposed timer-22 handler route. The four watched timer-22 handlers `$6c7a/$6c8f/$6ca4/$6cb9` and writer `$7b6e` did not execute in this replay, but this is only a bounded result for this one route.
- Door animation evidence: `clear-montage.png` shows before, during and after entering/opening the doorway (frame snapshots at 3345, 3460 and 3626). Following the carry and door contact, recorded game timer progression was 25→26→42→43→44→45, then state 20. This summarizes end-of-frame observations: the instruction-level probe additionally sees brief timer 42→41→43 in frame 3627.
- Frame 3625: bank 16 `$6fd4` increments timer 25→26. Frame 3626: bank-zero `$09d7` writes 26→42. Frame 3695: bank-zero `$0bf9` resets timer to 0; frame 3696 bank-zero `$0d25` changes game state 16→20. Frame-stepped trace shows queue `$c85c` 16→17 at frame 3626 and lives `$da43` remain 04. The screenshot and progression together support that this run cleared stage 1-1 and advanced to the next game state; independently identifying every state-20 screen is outside this probe.
- A no-B control using the same subsequent button windows did not run the pickup branch, did not show the 10→25 transition, and did not reach the watched 16→20 transition through frame 3800. The control's later positions can differ because it does not carry the key, so this is a behavioral control, not an isolated proof of every intermediate cause.

## Corrections and limits

The project and previous report mislabeled the upper hat-shaped bonus as the key: collecting that item fired handler 17 and left the actual key-shaped object visible. The actual key pickup here used bank-7 `$4a51`→`$4b47`, not handler 17. The stage-clear initiation in this gameplay path is timer 25 via bank 16 `$4126`, not the earlier hypothesized bank-7 timer-22 route. The latter may be meaningful elsewhere; this run does not determine its purpose.

The exploration runner's final `done=0` is not a failure verdict: its old terminal check was disabled and its experimental replacement only watched state 24, while the real transition went to state 20. The stage-clear claim is based on the independent replay, frame progression, and images, not that runner's success flag.

No Rivet code, emulator source, GitHub files or other agents were modified. No ROM, save, or emulator binary is in these artifacts.
