/* gb_bank29: live probe for the slice-19 bank-29 selector (tools/harnesses/gb_bank29.c).
 * Cycle-steps a run and logs every execution of the two sprite-table
 * bank selectors: PC $10da (rst $10 after `ld a,$1d`, the $10d5 entry)
 * and PC $10e2 (rst $10 after `ld a,$0b`, the $10dd entry), with A,
 * frame, state, timer, and the calling instruction (previous PC).
 * Frame-stepping cannot see these: the bank is restored (pop af;
 * rst $10) before the frame ends, so the switch is transient within
 * the frame. Usage: gb_bank29 <rom.gb> <frames> <press_spec>
 *   press_spec: same "btn:start:end,..." windows as gb_headless.
 * Build (from the decomp project root):
 *   cc -I ~/workspace/nacre/repo/include -I ~/workspace/nacre/repo/src/gb -O2 \
 *      -o tools/harnesses/gb_bank29 tools/harnesses/gb_bank29.c \
 *      ~/workspace/nacre/repo/src/gb/gb.c ~/workspace/nacre/repo/src/gb/gb_cpu.c \
 *      ~/workspace/nacre/repo/src/gb/gb_ppu.c ~/workspace/nacre/repo/src/gb/gb_cart.c \
 *      ~/workspace/nacre/repo/src/gb/gb_apu.c
 */
#include "gb.h"
#include "gb_internal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { GbButton btn; int start, end; } Press;
static Press presses[32]; static int npress = 0;

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s <rom.gb> <frames> <press_spec>\n", argv[0]);
        return 2;
    }
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
    int frames = atoi(argv[2]);
    char buf[1024];
    snprintf(buf, sizeof buf, "%s", argv[3]);
    for (char *tok = strtok(buf, ","); tok && npress < 32; tok = strtok(NULL, ",")) {
        char name[16]; int s, e;
        if (sscanf(tok, "%15[^:]:%d:%d", name, &s, &e) != 3) continue;
        static const char *names[GB_BUTTON_COUNT] = {
            "right", "left", "up", "down", "a", "b", "select", "start" };
        for (int b = 0; b < GB_BUTTON_COUNT; b++)
            if (!strcmp(name, names[b])) { presses[npress].btn = (GbButton)b; presses[npress].start = s; presses[npress].end = e; npress++; }
    }
    long n29 = 0, n11 = 0, n29entry = 0;
    int prev_pc = -1;
    for (int frame = 0; frame < frames; frame++) {
        for (int b = 0; b < GB_BUTTON_COUNT; b++) gb_set_button(gb, (GbButton)b, 0);
        for (int p = 0; p < npress; p++)
            if (frame >= presses[p].start && frame < presses[p].end)
                gb_set_button(gb, presses[p].btn, 1);
        for (int c = 0; c < GB_CYCLES_PER_FRAME; c++) {
            int pc = gb->pc;
            if (pc == 0x10da && prev_pc != 0x10da) {
                if (n29 < 10)
                    printf("BANK29 frame %d state=%d timer=%d A=$%02x caller_pc=$%04x\n",
                           frame, gb->hram[0x0e], gb->hram[0x10], gb->a, prev_pc);
                n29++;
            }
            if (pc == 0x10e2 && prev_pc != 0x10e2) {
                if (n11 < 10)
                    printf("BANK11 frame %d state=%d timer=%d A=$%02x caller_pc=$%04x\n",
                           frame, gb->hram[0x0e], gb->hram[0x10], gb->a, prev_pc);
                n11++;
            }
            if (pc == 0x10d5 && prev_pc != 0x10d5) n29entry++;
            prev_pc = pc;
            if (!gb_run_cycles(gb, 1, err, sizeof err)) {
                fprintf(stderr, "cpu lockup at frame %d cycle %d: %s\n", frame, c, err);
                return 1;
            }
        }
    }
    printf("TOTAL rst-$10-after-$1d ($10da): %ld  rst-$10-after-$0b ($10e2): %ld  $10d5 entries: %ld\n",
           n29, n11, n29entry);
    return 0;
}
