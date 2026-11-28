# Key & Door — movement experiment

A small, unfinished room to explore the feel of a Donkey Kong '94-inspired game. This is a research prototype, not a finished game or a clean-room implementation. The explorer, key, door and room are newly drawn pixel art for this experiment, in four grayscale shades on a 160×144 canvas. No Nintendo ROM, art, level data, music, or sound is included. Original artwork alone does not guarantee legal clearance.

## Windows

Double-click `KeyDoor.exe` on 64-bit Windows. Arrow keys move, Z or Space jumps, X picks up the key, R resets, and Escape exits. Jump onto the low platform, collect the key and bring it to the door. The executable was cross-compiled successfully but has NOT been run on Windows or Wine, so the Windows frontend is unverified. The program is unsigned and may trigger Windows security warnings.

## What was actually tested

The C gameplay core compiled and passed a scripted full room traversal on Linux, including a platform jump, pickup, walk off the platform and delivery. The shared C renderer passed tests for its four-shade palette and changed pickup/victory frames. A separate browser preview called the same game and rendering code via a local server: keyboard events completed the room and the screen displayed `Key delivered!`. The actual browser canvas was checked and contained exactly grayscale values 24, 104, 188 and 252. This exercises the C model, renderer and browser frontend, not the Windows frontend. No person has judged the feel by hand.

## How Rivet informed this

At Rivet commit `68290f35967d2323b976f03229fda43ee1c2acc4`, a Nacre replay of the rebuilt, SHA-matching ROM (not an independently acquired original) began a stationary A-button jump at frame 2500. Observed Y went from 136 to 120, with the first changed frame 2501, remained at the top around frames 2513–2521, and returned to 136 by frame 2538. An idle control stayed at 136. A right-only run moved X from 17 at frame 2500 to 44 at frame 2539. Logs `movement-jump.trace`, `movement-idle.trace` and `movement-run.trace` contain frame-by-frame positions. Emulator source was an experimental, unversioned Nacre snapshot; tests don't establish general emulator accuracy.

An instruction-level probe (`position_probe.c`, output `position-writes.log`) observed changes of the Y byte `$c203` at bank-zero `$1142`. In `src/banks/bank0slice6.asm` this instruction is in `StreamDispatchRecord` and follows an add-with-carry sequence on the record. The routine appears to update a multi-byte position from other record fields, but this alone does not identify the jump-initiation or gravity routine. Earlier key investigation identified bank-7 `$4a51` through `$4b47` during the pickup and bank-16 `$4126` at the door; details are in `../level-1-1-clear.md`.

The room's jump arc uses the measured positions as an explicit sampled curve with simplified landing; horizontal movement is approximately 0.7 pixels per tick from the single observed run. The platform, collision, falling, key pickup range and door are our prototype's choices, not proven matches to the original. No proof exists that the same jump arc applies to every game state or input, and current tests do not compare the playable room's movement frame by frame against the original. Both frontends target roughly 60 updates per second, but their real timing can vary under load. No claim of precise game parity is made.

## Source and reproducibility

`game.c` / `game.h`: C gameplay core. `render.c` / `render.h`: shared software renderer. `windows.c`: Win32/GDI frontend. `test_game.c`, `test_render.c`: core and rendering tests. `preview.py`, `preview.html`, `game.so`: local Linux browser preview (Python standard library + C shared library; `python3 preview.py`, then visit `http://127.0.0.1:8767`). Server has no authentication and binds only to localhost. One shared game state, for local testing only. The Linux shared library was built in a Debian container; rebuild on other platforms. `position_probe.c` is a Nacre research harness requiring the experimental Nacre core and an appropriate locally supplied ROM/save; none is bundled.

The Windows build used MinGW-w64 GCC in a temporary Debian container, `x86_64-w64-mingw32-gcc -std=c99 -O2 -Wall -Wextra -Werror -mwindows game.c render.c windows.c -lgdi32 -o KeyDoor.exe`.
