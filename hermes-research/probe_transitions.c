/* gb_pcwatch: live probe for the DK94 decomp (slice 19).
 * Cycle-steps a run and logs every execution of up to 8 given PCs
 * (ROM-window addresses), with frame/state/timer at each hit, plus
 * totals. Frame-stepping cannot see transient code (e.g. a $2b48
 * handler that runs inside one frame's dispatch loop), so this steps
 * one cycle at a time and watches gb->pc.
 * Usage: gb_pcwatch <rom.gb> <frames> <press_spec> <save_in|-> <pc,...>
 *   press_spec: same "btn:start:end,..." windows as gb_headless ("-" = none).
 *   save_in: path to a .sav to preload, or "-" for fresh SRAM.
 *   pc list: hex addresses, optionally with @bank (e.g. 7378@10 counts
 *   PC $7378 only while bank 10 is mapped -- PC alone is ambiguous
 *   across banks).
 * Build (from the decomp project root):
 *   cc -I ~/workspace/nacre/repo/include -I ~/workspace/nacre/repo/src/gb -O2 \
 *      -o tools/harnesses/gb_pcwatch tools/harnesses/gb_pcwatch.c \
 *      ~/workspace/nacre/repo/src/gb/gb.c ~/workspace/nacre/repo/src/gb/gb_cpu.c \
 *      ~/workspace/nacre/repo/src/gb/gb_ppu.c ~/workspace/nacre/repo/src/gb/gb_cart.c \
 *      ~/workspace/nacre/repo/src/gb/gb_apu.c
 * Slice 29: press windows raised 32 -> 512 and the spec buffer
 * 1024 -> 8192 bytes, so a full gb_play schedule (~250 merged
 * windows) replays whole instead of silently truncating at 32 --
 * the likely source of the slice-8 schedule-replay divergence.
 */
#include "gb.h"
#include "gb_internal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { GbButton btn; int start, end; } Press;
static Press presses[512]; static int npress = 0;

int main(int argc, char **argv) {
    if (argc < 6) {
        fprintf(stderr, "usage: %s <rom.gb> <frames> <press_spec> <save|-> <pc,...>\n", argv[0]);
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
    if (strcmp(argv[4], "-")) {
        FILE *sf = fopen(argv[4], "rb");
        if (!sf) { perror("open save"); return 1; }
        uint8_t *sav = malloc(8192);
        size_t n = fread(sav, 1, 8192, sf); fclose(sf);
        if (n != 8192) { fprintf(stderr, "short save\n"); return 1; }
        gb_save_load(gb, sav, 8192);
        free(sav);
    }
    int frames = atoi(argv[2]);
    char buf[8192];
    snprintf(buf, sizeof buf, "%s", argv[3]);
    if (strcmp(argv[3], "-"))
        for (char *tok = strtok(buf, ","); tok && npress < 512; tok = strtok(NULL, ",")) {
            char name[16]; int s, e;
            if (sscanf(tok, "%15[^:]:%d:%d", name, &s, &e) != 3) continue;
            static const char *names[GB_BUTTON_COUNT] = {
                "right", "left", "up", "down", "a", "b", "select", "start" };
            for (int b = 0; b < GB_BUTTON_COUNT; b++)
                if (!strcmp(name, names[b])) { presses[npress].btn = (GbButton)b; presses[npress].start = s; presses[npress].end = e; npress++; }
        }
    int pcs[8]; int banks[8]; long totals[8] = {0}; int npcs = 0;
    snprintf(buf, sizeof buf, "%s", argv[5]);
    for (char *tok = strtok(buf, ","); tok && npcs < 8; tok = strtok(NULL, ",")) {
        char *at = strchr(tok, '@');
        banks[npcs] = at ? (int)strtol(at + 1, NULL, 10) : -1;
        if (at) *at = 0;
        pcs[npcs++] = (int)strtol(tok, NULL, 16);
    }
    unsigned long values[256] = {0};
    int prev_pc = -1;
    for (int frame = 0; frame < frames; frame++) {
        if (frame >= 2499 && (frame - 2499) % 15 == 0) printf("CHUNK %d frame=%d x=%u y=%u key=%d\n", (frame - 2499)/15, frame, gb->wram[0x207], gb->wram[0x203], gb->vram[0x1800 + 5*32+9] == 0x3b && gb->vram[0x1800+5*32+10] == 0x3c);
        for (int b = 0; b < GB_BUTTON_COUNT; b++) gb_set_button(gb, (GbButton)b, 0);
        for (int p = 0; p < npress; p++)
            if (frame >= presses[p].start && frame < presses[p].end)
                gb_set_button(gb, presses[p].btn, 1);
        uint64_t target = gb->cycles + GB_CYCLES_PER_FRAME;
        while (gb->cycles < target) {
            int pc = gb->pc;
            if (pc != prev_pc) {
                if (pc == 0x6b48 && gb->hram[0x0c] == 7) values[gb->c]++;
                for (int i = 0; i < npcs; i++)
                    if (pc == pcs[i] && (banks[i] < 0 || gb->hram[0x0c] == banks[i])) {
                        if (totals[i] < 10)
                            printf("PC $%04x frame %d state=%d timer=%d bank=%d\n",
                                   pc, frame, gb->hram[0x0e], gb->hram[0x10], gb->hram[0x0c]);
                        totals[i]++;
                    }
            }
            prev_pc = pc;
            uint8_t oldtimer = gb->hram[0x10], oldstate = gb->hram[0x0e]; uint8_t before = gb->wram[0x1d18]; uint16_t oldpc=gb->pc; int oldbank=gb->hram[0x0c];
            if (!gb_run_cycles(gb, 1, err, sizeof err)) {
                fprintf(stderr, "cpu lockup at frame %d cycle %d: %s\n", frame, 0, err);
                return 1;
            }
            if (frame >= 3300 && frame <= 3720 && (oldtimer!=gb->hram[0x10] || oldstate!=gb->hram[0x0e])) printf("STATEWRITE frame=%d pc=%04x bank=%d state=%u->%u timer=%u->%u\n", frame,oldpc,oldbank,oldstate,gb->hram[0x0e],oldtimer,gb->hram[0x10]);
            if (gb->wram[0x1d18] != before) printf("DD18 frame=%d pc=%04x bank=%d %02x->%02x\n",frame,oldpc,oldbank,before,gb->wram[0x1d18]);
        }
    }
    for (int i = 0; i < 256; i++) if (values[i]) printf("RECORD %02x: %lu\n", i, values[i]);
    for (int i = 0; i < npcs; i++)
        printf("TOTAL PC $%04x: %ld\n", pcs[i], totals[i]);
    return 0;
}
