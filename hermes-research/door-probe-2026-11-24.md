# Rivet: first door interaction probe

Source: Rivet commit `68290f35967d2323b976f03229fda43ee1c2acc4` (local checkout at time of investigation). Rebuilt ROM SHA-1 was previously verified as `397ad2ff25627b83e02c71b54c72bb4deb39e0c0`; the fixture used here is the locally rebuilt ROM, not an independently obtained original.

## Setup and controls

Nacre core from `/srv/agents/workspace/bunsen/experiments/graphify-nacre/paired-test/plain/workspace/repo` (an unversioned experimental snapshot, not established as current Nacre). Compiled existing Rivet harnesses with locally extracted Debian TCC; no system installation. Generated f1 save using the slice-5 f1 input and 7000 frames; framebuffer SHA-256 was `1cf926799cff7d9119d27ca6fde515c0da226eccb342eb0a823e8bbb79733c03`, matching the progress log's f1 prefix. Patched it with `tools/make_progress_save.py` to progress 1. At 5000 frames with the slice-7 mid5000 inputs the framebuffer SHA-256 was `2ab1bb5dfac756816557ed1f86dbd875623b4ae71cbdfa5417e187b96006b237`, matching the progress log's mid5000 prefix. This checks reproducibility of these two states, not general emulator accuracy.

## Correction and successful key replay

The initial pcwatch results below are INVALID as gameplay-frame evidence. Nacre `gb_run_cycles(gb, 1)` executes at least one complete instruction, not exactly one cycle. The old pcwatch executes it `GB_CYCLES_PER_FRAME` times per nominal frame, over-advancing the emulator. An amended scratch probe loops until the emulator's actual cycle counter reaches a per-frame target, matching `gb_headless`/`gb_play` stepping semantics.

Using the documented play29 waypoint settings, the autopilot reached the key at chunk 103, position (73,63). It produced a 142-chunk schedule. Replaying that schedule with gameplay input windows shifted +1 frame, the corrected probe observed bank 7 key handler `$6dcf` at frame 4057, and the key tiles were absent at frame 4059 (chunk boundary 104), Mario (74,65). Positions are not perfectly identical to the original autopilot, so this is a repeatable key-collection outcome, not an exact state-for-state replay. Two separate harnesses using the same input agreed on all 138 position samples with corresponding headless trace entries, supporting the fixed probe's frame alignment; 9 samples lacked headless trace rows and were not compared.

At `$6b48`, the corrected probe saw lookup index `$74` at frame 2920 and `$4c` at frame 4057; the latter reached key handler `$6dcf`. No watched timer-22 candidate handlers `$6c7a`, `$6c8f`, `$6ca4`, `$6cb9`, or writer `$7b6e` fired through frame 4700. This is specific to this path and does not prove anything about a door encounter. Saved `probe_fixed.c`, `key-route-press-spec.txt`, `play-fast.log`, and `replay-fixed.log` alongside this report; these do not include ROMs or save files.

## Initial live experiment (invalid timing; superseded)

Ran `gb_play` with 45 search iterations, progress-1 save, and default waypoint strategy. Result was `done=0`, 37 chunks after backtracking; no key collection or clear was reported. Its termination detection is based on historical hypotheses (including an explicitly refuted timer-26 door hypothesis), so cannot establish a clear without independent checks.

Instrumented a scratch copy of `gb_pcwatch.c`: at bank 7 PC `$6b48` tally register C as the dispatcher lookup index, plus original bank-filtered PC watches. Replayed the printed schedule with intro inputs `start:620:632,a:1000:1012,a:2000:2012`, through frame 3100. Observed one dispatcher hit and a hit at key handler `$6b55`, both at frame 860, state 18 timer 8, record value `$74`; no hits for handlers `$6c7a`, `$6c8f`, `$6ca4`, `$6cb9`, writer `$7b6e`, or bank-zero `$098c`. A 3100-frame intro-only control produced precisely the same hits and record value. Thus this hit does not demonstrate key collection in the player-controlled run, and none of the tested clear-candidate handlers fired. These negative results apply only to these exact schedules and frames.

The dispatch map in `src/banks/bank7slice10.asm` maps lookup indices `$10–$13` to handler 02, `$18–$1b` to 04, `$26–$29` to 08, `$2a–$2d` to 09. Static routines store the previous timer at `$c70b` and set timer `$16` (decimal 22); slice 27 documents the later transition. These indices are candidates, not established door tiles or proven causes of stage completion.

## Major visual correction: the supposed key is likely a bonus item

The prior sections use the original harness's word `key` for the tiles at screen (72–87,40–55). A direct framebuffer comparison contradicts that identification: the sprite removed at this location resembles a hat, while a visibly key-shaped object around screen (112–128,70–89) and a locked-door-shaped object around (112–128,119–136) remain on screen. The key-shaped and door-shaped crops were byte-identical between the frame 2499 baseline and frame 4059 after the recorded pickup, while 65 pixels changed at the supposed-key location. `before-after-collectible.png` contains both screenshots (before left, after right). This strongly suggests handler 17 picked up the hat/bonus, not the actual key; the precise object identities and how to take the key still need live verification. The harness and several earlier notes misname that pickup. Therefore the preceding 'key replay' establishes reproducible collection of the upper-center item, NOT actual key possession. It also does not demonstrate proximity to a door.

At the replay's frame 4057 the frame-stepped trace independently shows `$c858` 03→02 and `$da41` 06→08 while `$dd18` remains 00. This supports a scored collectible/counter event; it does not establish possession of the key-shaped object. The map cells covering the key-shaped image (rows 10–11, columns 15–16, mapping as documented in `survey29_map.py`) contain `47 00`, `47 01`, `47 02`, `47 03` in the first pair in both the chunk-0 and pickup WRAM dumps. That spatial association is a lead, not proof of an interaction path.

The same over-stepping loop is present in `gb_bank29.c`, and in the second, instruction-refinement pass of `gb_watch.c`. The latter's first, frame-stepped pass is different and is not invalidated by that issue. Past conclusions relying on affected instruction-level timestamps or extended watched windows need individual revalidation; this does not invalidate byte-matching builds or all gameplay observations.

## Next experiment

### Direct approach to the key-shaped object

Made a scratch-only copy of `gb_play`, changed the waypoint logic to target the visually identified key area immediately rather than first pursuing the upper collectible, and disabled the outdated stage-clear heuristic. With post-objective waypoints (112,136), (128,96), a 300-iteration search ended `done=0` at 252 chunks and repeatedly backtracked. It got Mario to roughly OAM (139,88), near the right side of the key-shaped object, but did not establish a pickup or win.

Replayed the first 18 choices with the +1 input alignment, reaching OAM (152,88). From there, four manually tried continuations (left, left+B, left+down, left+A) did not produce an observed key pickup; left and left+B stopped at approximately OAM (140,88). A frame-2829 screenshot (`at-key.png`) shows Mario immediately to the right of the key-shaped graphic, with a vertical block wall between them. Thus simple proximity and B from the outside is insufficient on the tested timings; a route around/over the barrier is a concrete next hypothesis. The screenshot does not itself prove the graphic's mechanics or that the button was correctly timed for pickup.

A second 200-iteration search tried approaching over the wall via waypoints (112,136) → (152,88) → (136,48) → (120,48) → (120,96). It repeatedly reached the upper waypoints (within the harness's 12-pixel radius), but never reached the final waypoint; the search ended after 180 retained chunks and repeated backtracking. The termination heuristic was disabled, so `done=0` is not a stage-completion test. Its complete log is `play-over-wall.log`.

Saved the target search source/log, initial input spec, one button-variant log and screenshot here; no original or rebuilt ROM or game save is included. Core used remains the experimental unversioned Nacre snapshot. Future work should trace type `$47` object handling and compare state before/after actual contact, rather than infer a door trigger from bonus-item collection. Avoid using the outdated gb_play terminal detector as proof of completion.

No Rivet source was modified, no code was pushed, and no original ROM is included in this report.
