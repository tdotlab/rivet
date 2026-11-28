# Key and door: first C experiment

## Purpose

A small experiment toward T's goal: an original game that is visibly in the spirit of Donkey Kong '94, with gameplay informed by Rivet's disassembly rather than only by looking at the game. This is not a clean-room implementation and not a legal clearance. No Nintendo graphics, music, level data, or ROM are included.

## Evidence and interpretation

Reference: Rivet commit `68290f35967d2323b976f03229fda43ee1c2acc4`; previous Nacre replay and controls are documented in `../level-1-1-clear.md`, `../pickup-path.log`, `../clear-transitions.log`, and `../no-b-control.log`. The emulator was an experimental Nacre snapshot; the replay used a ROM rebuilt from Rivet, matching its recorded SHA-1, not a separately acquired original.

- Actual assembly: in `src/banks/bank7slice13.asm`, bank 7 `$4a51–$4a59` checks that the low five bits of a collision record equal 7; `$4a75` onward updates map data; `$4b47` writes 3 to `$dd18`. In the tested route those instructions executed when B was pressed at the visible key; the no-B control did not enter the branch. The direct connection between those writes and every detail of carrying is not fully established.
- Actual assembly: in `src/banks/bank16slice26.asm`, bank 16 `$4124–$4126` writes 25 to the timer. During the observed door sequence this occurred at frame 3345; a transition from state 16 to 20 occurred at frame 3696. These are two milestones of one route, not a complete understanding of the sequence.
- Inference/design: `model.c` uses a boolean for key possession, removes the key from an abstract map on pickup, and starts a clear sequence at a door while carrying. These are a high-level interpretation of the observations; this code is not a translation of the original assembly. It models only successful pickup/door milestones, not all inputs, collisions, animations, actions, or exceptions. In particular, a no-key door is rejected because that is what the recorded no-B route supports at the end-to-end level, not because the precise original guard was isolated.
- A **351-tick** transition in `model.c` is calibrated to the difference between the two observed frame numbers. This is an experiment parameter, not a demonstrated universal game constant or original timing mechanism. It does not implement the intermediate timer transitions.

## Run the focused tests

Build with any conforming C compiler, e.g. `cc -std=c99 model.c test_model.c -o test_model && ./test_model`. The laptop had no compiler installed system-wide; the test was run using the existing locally extracted TinyCC and explicitly linked system libc. It checks no-button/no-key cases, pickup once, door without carrying, no duplicate interactions, and the calibrated transition boundary. These tests validate this small model against its stated assumptions; they do not establish complete equivalence with the game, compare real input schedules frame-by-frame, or show a playable application.

## Verdict: PARTIAL

A documented route from assembly and actual execution to a compact high-level C interaction model is feasible. Next, trace and measure a movement/jump or pickup animation routine, choose separately authored temporary art and a deliberately different test level, and build a playable slice with direct frame-by-frame observation where meaningful. Do not describe this as an independent legal clean room: direct study of the original code is central to the chosen approach.
