/* gb_probe17: one-shot probe for the state-17 timer-29 oddity (slice 3).
 * Runs the slice-2 Start+A input (start:620:632,a:1000:1012) on a ROM and
 * watches for hGameState==17 with hStateTimer==29. On first sight it dumps
 * WRAM $cc00-$ce00 (so the bytes at the rst-$08 target $cdc8 are visible)
 * and then cycle-steps, logging PC/state/timer/bank on every change for
 * ~200k cycles, so the path out of the $cdc8 jump is visible.
 * Usage: gb_probe17 <rom.gb>
 * Build (from the decomp project root):
 *   cc -I ~/workspace/nacre/repo/include -I ~/workspace/nacre/repo/src/gb -O2 \
 *      -o tools/harnesses/gb_probe17 tools/harnesses/gb_probe17.c \
 *      ~/workspace/nacre/repo/src/gb/gb.c ~/workspace/nacre/repo/src/gb/gb_cpu.c \
 *      ~/workspace/nacre/repo/src/gb/gb_ppu.c ~/workspace/nacre/repo/src/gb/gb_cart.c \
 *      ~/workspace/nacre/repo/src/gb/gb_apu.c
 */
#include "gb.h"
#include "gb_internal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s <rom.gb>\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open rom"); return 1; }
    fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *rom = malloc(len);
    if (fread(rom, 1, len, f) != (size_t)len) { fprintf(stderr, "short read\n"); return 1; }
    fclose(f);
    Gb *gb = gb_create();
    char err[256] = {0};
    if (!gb_load_rom(gb, rom, (size_t)len, err, sizeof err)) {
        fprintf(stderr, "gb_load_rom failed: %s\n", err); return 1;
    }
    int hit = 0;
    for (int frame = 0; frame < 6000 && !hit; frame++) {
        /* Press spec that reproduces the slice-2 observation: NO press at
         * 620 (game idles into attract demo, state 30), Start at 2500-2511
         * during the attract, which cuts it short; the second title cycle
         * then goes 16 -> 20 -> 18 -> 17 (timer 29) -> 18. (Note: the
         * harness's multi-window spec for one button clobbers earlier
         * windows with later ones, so this run's effective input was
         * Start only at 2500-2511 -- see PROGRESS.md.) */
        gb_set_button(gb, GB_BUTTON_START, frame >= 2500 && frame < 2512);
        gb_set_button(gb, GB_BUTTON_A, 0);
        if (!gb_run_cycles(gb, GB_CYCLES_PER_FRAME, err, sizeof err)) {
            fprintf(stderr, "cpu lockup at frame %d: %s\n", frame, err); return 1;
        }
        int state = gb->hram[0x0e], timer = gb->hram[0x10];
        { static int ps=-1, pt=-1; if (state!=ps||timer!=pt) { printf("frame %d state=%d timer=%d\n", frame, state, timer); ps=state; pt=timer; } }
        if (state == 17 && timer == 29) {
            hit = 1;
            printf("HIT frame %d pc=%04x state=%d timer=%d bank=%d\n",
                   frame, gb->pc, state, timer, gb->hram[0x0c]);
            printf("WRAM $cc00-$ce00:\n");
            for (int base = 0xcc00; base < 0xce00; base += 16) {
                printf("%04x:", base);
                for (int i = 0; i < 16; i++) printf(" %02x", gb->wram[base - 0xc000 + i]);
                printf("\n");
            }
            /* Cycle-step, logging state/timer/bank changes and the first
             * 120 distinct PCs (the path out of the $cdc8 jump). */
            int ps = -1, pstate = -1, ptimer = -1, pbank = -1, pc_lines = 0;
            for (int c = 0; c < 200000; c++) {
                if (!gb_run_cycles(gb, 1, err, sizeof err)) {
                    printf("lockup at cycle %d: %s\n", c, err); break;
                }
                int s = gb->hram[0x0e], t = gb->hram[0x10], b = gb->hram[0x0c];
                if (s != pstate || t != ptimer || b != pbank) {
                    printf("cyc %6d pc=%04x state=%d timer=%d bank=%d\n",
                           c, gb->pc, s, t, b);
                    pstate = s; ptimer = t; pbank = b;
                } else if (gb->pc >= 0xc000 && gb->pc < 0xe000 && gb->pc != ps && pc_lines < 80) {
                    /* True WRAM execution (excludes HRAM DMA at $ff80+):
                     * the $cdc8 NOP slide and where it lands. */
                    printf("cyc %6d WRAM pc=%04x (state %d timer %d bank %d)\n",
                           c, gb->pc, s, t, b);
                    pc_lines++;
                } else if ((gb->pc == 0x34df || gb->pc == 0x0fd9 || gb->pc == 0xcdc8 ||
                            gb->pc == 0x1d22) && gb->pc != ps && pc_lines < 80) {
                    /* FileSelect entry, RST8 dispatch, $cdc8 target, AdvanceState. */
                    printf("cyc %6d MARK pc=%04x (state %d timer %d bank %d)\n",
                           c, gb->pc, s, t, b);
                    pc_lines++;
                }
                ps = gb->pc;
                if (s == 18 && t == 1) { printf("reached state 18 timer 1 at cycle %d\n", c); break; }
            }
        }
    }
    if (!hit) printf("no state-17 timer-29 seen in 3600 frames\n");
    gb_destroy(gb);
    free(rom);
    return 0;
}
