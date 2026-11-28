# Hermes's Rivet research handoff

Research and experiments from November 24–25, 2026, preserved for Mike and T. This is separate from Rivet's disassembly; it has not been integrated into the game or its build. The reference was Rivet commit `68290f35967d2323b976f03229fda43ee1c2acc4` and an experimental, unversioned Nacre snapshot.

## Start here

- `level-1-1-clear.md` — actual key pickup, carry, door transition and a no-pickup control. This supersedes the early identification of a hat-shaped bonus as the key.
- `door-probe-2026-11-24.md` — research history and corrected instrumentation. Read its later corrections: it preserves outdated conclusions as history. The final successful route is in the clear report above.
- `carry-route.spec`, `probe_transitions.c`, `door-result.trace`, `clear-transitions.log`, `no-b-control.log` — replay schedule, probe and recorded observations. These are research artifacts, not a turnkey portable test suite.
- `playable-spike/` — small, separate C room with original four-shade placeholder art, browser preview, Windows frontend and tests. Read its README for the original experiments and fidelity limits. Binaries are deliberately omitted; build them locally. The Windows version was cross-compiled but not run on Windows.
- `interaction-spike/` — earlier simplified key-and-door model, not a translation of the original game.

## What the experiments show—and do not show

The reports describe a successful replay on a locally rebuilt ROM, including a no-B control. They do not establish general emulator accuracy or identify every game state. The original instruction watch over-stepped frames; the corrected probe uses the emulator's actual cycle counter. Related earlier instruction-level observations need individual revalidation. The prototype's jump follows one measured example; collision and other mechanics are approximations. The tests described are historical; they were not rerun when this handoff was assembled.

No ROM, save, executable, shared library, archive, or original-game screenshot is included in this handoff. Reports and logs preserve historical machine-specific paths, unavailable dependencies and references to screenshots or binaries that were not copied; they are evidence of the original setup, not paths guaranteed to work. The `playable-spike/monochrome-room.png` image is the newly drawn prototype, not the original game. The unversioned Nacre snapshot and generated fixture from the original session are not included, so complete reproduction requires reconstructing the environment.

Original conversation: Hermes session `20261124_222201_c1f2a3d4`. No changes to Rivet source or emulator code were made as part of the original experiments.
