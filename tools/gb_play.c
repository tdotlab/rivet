/* gb_play: greedy beam-less autopilot for the DK94 decomp (slice 8).
 * Goal: complete stage 1-1 live (key -> door) and record the input
 * schedule that does it, so the run is reproducible from frame 0.
 *
 * Method: run the standard progress-1 intro (start/a/a) to the first
 * playable frame (state 16, timer 3). Then, in CHUNK-frame steps, fork
 * one child per action; each child applies its action, then reports
 * Mario's position ($c200 record 0: x=byte 7, y=byte 3), whether the
 * key tiles are still in the tilemap ($9800 row 5 cols 9-10 == $3b/$3c),
 * whether a death (timer 12) or stage-clear (timer >= 23) was seen.
 * The parent picks the best-scoring child, applies that action to its
 * own emulator (deterministic: same result as the child), and repeats.
 * Score is distance to the current waypoint (pre-key) or post-key
 * waypoint, then distance to a door prior (top-right) plus an upward
 * bias, minus a visit penalty (quantized Mario cells revisited) so it
 * does not oscillate. Waypoints steer Mario up the ladders: plain
 * distance-to-key leads him right along the ground into a local
 * optimum (he never climbs, because walking right always scores
 * better than climbing at each step); plain distance-to-door stalls
 * the same way after the key, because the route backtracks down to
 * the ground first.
 * If the score stalls for STALL_MAX chunks, or every action dies, the
 * parent backtracks: it replays from frame 0 (fresh emulator, same
 * save, recorded schedule) to the last decision point with an untried
 * action and resumes there. The winning schedule is printed as a
 * gb_headless press spec so the run can be replayed exactly.
 *
 * Usage: gb_play <rom.gb> <save_in.sav> <max_chunks> [seed_actions] [waypoints] [postwp]
 *   seed_actions: optional comma list of action indices to force for
 *   the first N chunks (e.g. "1,1,1,3,3" = right,right,right,up,up).
 *   waypoints: optional "x,y;x,y;..." pre-key route (last is the key).
 *   postwp: optional "x,y;x,y;..." post-key route (door last resort).
 * Key OAM target: key tiles at screen (80,44) -> OAM (88,60).
 * Door prior: OAM (127,95) -- center of the $c0-$c3 2x2 block at
 * tilemap rows 9-10, cols 14-15 (screen x=112-127, y=72-87). Slice 8's
 * play11 only reached (116,98), 4px short of overlap, with the old
 * (112,96) prior at the block's left edge; the top-right candidates
 * (152,40) and (152,20) were tested by jumping/falling through and by
 * standing (play6/9/10) with no trigger, and the top girder does not
 * support Mario at x=153. Terminal is any stage-clear entry timer
 * (13/23/26/42/33+, slice 9): the door sets timer 26 (bank-1 $56c3)
 * and the clear chain runs 33->40->42->43->44->45->0.
 * Build (from the decomp project root):
 *   cc -I ~/workspace/nacre/repo/include -I ~/workspace/nacre/repo/src/gb -O2 \
 *      -o tools/gb_play tools/gb_play.c \
 *      ~/workspace/nacre/repo/src/gb/gb.c ~/workspace/nacre/repo/src/gb/gb_cpu.c \
 *      ~/workspace/nacre/repo/src/gb/gb_ppu.c ~/workspace/nacre/repo/src/gb/gb_cart.c \
 *      ~/workspace/nacre/repo/src/gb/gb_apu.c
 */
#include "gb.h"
#include "gb_internal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <math.h>
#include <sys/wait.h>

#define CHUNK 15
#define STALL_MAX 10
#define MAX_CHUNKS 600
#define NACTIONS 10

/* intro press windows (progress-1 flow, slice 6/7) */
typedef struct { GbButton btn; int start, end; } Press;
static Press intro[] = {
    { GB_BUTTON_START, 620, 632 },
    { GB_BUTTON_A, 1000, 1012 },
    { GB_BUTTON_A, 2000, 2012 },
};
#define NINTRO (sizeof(intro)/sizeof(intro[0]))

/* actions: bitmask over buttons, applied for a whole chunk */
static const char *aname[NACTIONS] = {
    "wait", "right", "left", "up", "down",
    "right+A", "left+A", "A", "B", "right+B"
};
/* button bit order: right,left,up,down,a,b,select,start */
static const int abits[NACTIONS] = {
    0,
    1 << GB_BUTTON_RIGHT,
    1 << GB_BUTTON_LEFT,
    1 << GB_BUTTON_UP,
    1 << GB_BUTTON_DOWN,
    (1 << GB_BUTTON_RIGHT) | (1 << GB_BUTTON_A),
    (1 << GB_BUTTON_LEFT) | (1 << GB_BUTTON_A),
    1 << GB_BUTTON_A,
    1 << GB_BUTTON_B,
    (1 << GB_BUTTON_RIGHT) | (1 << GB_BUTTON_B),
};

static const char *rom_path, *save_path;
static int max_chunks;

/* dump WRAM+HRAM+VRAM at a notable moment (key collect, terminal) so
 * the $c200/$db15 records and tilemap can be diffed afterwards.
 * Durable path under the repo (slice 9): /tmp was wiped mid-session
 * and took the key dump with it once already. */
static void dump_state(Gb *gb, const char *tag) {
    char dir[256];
    snprintf(dir, sizeof dir, "build/nacre-test/slice12/play");
    char cmd[300];
    snprintf(cmd, sizeof cmd, "mkdir -p %s", dir);
    (void)system(cmd);
    char path[300];
    snprintf(path, sizeof path, "%s/%s_wram.bin", dir, tag);
    FILE *f = fopen(path, "wb"); if (f) { fwrite(gb->wram, 1, 8192, f); fclose(f); }
    snprintf(path, sizeof path, "%s/%s_hram.bin", dir, tag);
    f = fopen(path, "wb"); if (f) { fwrite(gb->hram, 1, 128, f); fclose(f); }
    snprintf(path, sizeof path, "%s/%s_vram.bin", dir, tag);
    f = fopen(path, "wb"); if (f) { fwrite(gb->vram, 1, 8192, f); fclose(f); }
    printf("  dumped %s/* to %s\\n", tag, dir);
    fflush(stdout);
}

/* Mario pos from $c200 record 0; key present from VRAM tilemap. */
static void read_state(Gb *gb, int *mx, int *my, int *key, int *lives) {
    *mx = gb->wram[0x207];   /* $c207 record 0 byte 7 = X */
    *my = gb->wram[0x203];   /* $c203 record 0 byte 3 = Y */
    /* key tiles $3b/$3c at tilemap $9800 row 5 cols 9-10 (vram +$1800) */
    *key = (gb->vram[0x1800 + 5 * 32 + 9] == 0x3b &&
            gb->vram[0x1800 + 5 * 32 + 10] == 0x3c);
    *lives = gb->wram[0xda43 - 0xc000];
}

static void set_buttons(Gb *gb, int bits) {
    for (int b = 0; b < GB_BUTTON_COUNT; b++)
        gb_set_button(gb, (GbButton)b, (bits >> b) & 1);
}

/* run `frames` frames with constant button bits; report death/clear seen */
static void run_chunk(Gb *gb, int bits, int frames, int *dead, int *term) {
    char err[256] = {0};
    *dead = 0; *term = 0;
    for (int i = 0; i < frames; i++) {
        set_buttons(gb, bits);
        if (!gb_run_cycles(gb, GB_CYCLES_PER_FRAME, err, sizeof err)) {
            fprintf(stderr, "cpu lockup: %s\n", err);
            *dead = 1; return;
        }
        int state = gb->hram[0x0e], timer = gb->hram[0x10];
        if (state == 16 && timer == 12) *dead = 1;
        /* Stage-clear entry timers (slice 9): the door sets timer 26
         * (bank-1 $56c3, the only writer of $1a to $ff90) or timer 23
         * (no direct writer; reached only via IncStateTimer); the
         * clear chain is timers 33->40->42->43->44->45. Timer 13 is
         * set by bank-10 $5405 handlers 2/4/12 ($555d/$564f/$59ad) --
         * those tiles ($5c/$64/$68/$be) are absent from stage 1-1, so
         * timer 13 firing here would itself be news. Report the exact
         * timer value so a hit can be judged, not just "term". */
        if (state == 16 && (timer == 13 || timer == 23 || timer == 26 ||
                            timer == 42 || timer >= 33)) *term = timer;
    }
}

static Gb *load_fresh(void) {
    FILE *f = fopen(rom_path, "rb");
    if (!f) { perror("open rom"); exit(1); }
    fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *rom = malloc(len);
    if (fread(rom, 1, len, f) != (size_t)len) { fprintf(stderr, "short read\n"); exit(1); }
    fclose(f);
    Gb *gb = gb_create();
    char err[256] = {0};
    if (!gb_load_rom(gb, rom, (size_t)len, err, sizeof err)) {
        fprintf(stderr, "gb_load_rom failed: %s\n", err); exit(1);
    }
    free(rom);
    FILE *sf = fopen(save_path, "rb");
    if (sf) {
        fseek(sf, 0, SEEK_END); long slen = ftell(sf); fseek(sf, 0, SEEK_SET);
        uint8_t *sdata = malloc(slen);
        if (fread(sdata, 1, slen, sf) == (size_t)slen) gb_save_load(gb, sdata, (size_t)slen);
        free(sdata); fclose(sf);
    }
    return gb;
}

/* run the intro; returns the first playable frame (state 16 timer 3). */
static int run_intro(Gb *gb) {
    char err[256] = {0};
    for (int i = 0; ; i++) {
        for (int b = 0; b < GB_BUTTON_COUNT; b++) gb_set_button(gb, (GbButton)b, 0);
        for (size_t p = 0; p < NINTRO; p++)
            if (i >= intro[p].start && i < intro[p].end)
                gb_set_button(gb, intro[p].btn, 1);
        if (!gb_run_cycles(gb, GB_CYCLES_PER_FRAME, err, sizeof err)) {
            fprintf(stderr, "cpu lockup at frame %d: %s\n", i, err); exit(1);
        }
        int state = gb->hram[0x0e], timer = gb->hram[0x10];
        /* The first timer 3 after a (3,1) dispatch is the level-load
         * chain (3->28->29->30->31->32->3); Mario's record is parked
         * off-screen (x=$f0) until the load finishes. Wait for the
         * timer 3 where Mario is actually on screen. */
        int mx = gb->wram[0x207], my = gb->wram[0x203];
        if (state == 16 && timer == 3 && mx < 200 && my < 200) return i + 1;
        if (i > 6000) { fprintf(stderr, "intro never reached playable\n"); exit(1); }
    }
}

typedef struct {
    int action, mx, my, key, dead, term, lives;
} Report;

static double dist(int x1, int y1, int x2, int y2) {
    double dx = x1 - x2, dy = y1 - y2;
    return sqrt(dx * dx + dy * dy);
}

/* Waypoints for the pre-key phase: the route goes UP the ladders, and
 * plain distance-to-key leads Mario right along the ground into a
 * local optimum (he never climbs, because at every step walking right
 * scores better than climbing). Waypoints are (x,y) in OAM coords
 * ($c200 record 0), reached within 12px; the last one is the key
 * itself, reached only when the key is collected (key==0). */
static int waypoints[16][2];
static int nwaypoints = 0;
static int cur_wp = 0;

/* Post-key waypoints: after the key, Mario must backtrack (down to
 * the ground, across to the right) before he can climb to the door,
 * so plain distance-to-door stalls the same way distance-to-key did.
 * Same format as waypoints; reached within 12px; when exhausted the
 * score falls back to the door prior (152,40) + upward bias. */
static int postwp[16][2];
static int npostwp = 0;
static int cur_postwp = 0;

/* Advance the current waypoint when Mario gets within 12px of it.
 * The last waypoint is the key itself: it only advances when the
 * key is actually collected (key==0), so Mario keeps being pulled
 * to the exact key position until he touches it. */
/* Advance the current waypoint when Mario gets within 6px of it.
 * (Slice 12: was 12px -- at 12px Mario at (48,136) "reached"
 * (56,136) while still on the ground, the target switched to
 * (56,56), and the greedy climbed diagonally up-left to (32,59)
 * where all actions die. 6px keeps him on the waypoint until he
 * is actually there.) */
static void maybe_advance_wp(int mx, int my, int key) {
    while (cur_wp < nwaypoints && key &&
           dist(mx, my, waypoints[cur_wp][0], waypoints[cur_wp][1]) < 6.0) {
        printf("  waypoint %d (%d,%d) reached\n", cur_wp,
               waypoints[cur_wp][0], waypoints[cur_wp][1]);
        cur_wp++;
    }
    while (cur_postwp < npostwp && !key &&
           dist(mx, my, postwp[cur_postwp][0], postwp[cur_postwp][1]) < 6.0) {
        printf("  post-key waypoint %d (%d,%d) reached\n", cur_postwp,
               postwp[cur_postwp][0], postwp[cur_postwp][1]);
        cur_postwp++;
    }
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s <rom.gb> <save_in.sav> <max_chunks> [seed_actions] [waypoints x,y;x,y;...]\n", argv[0]);
        return 2;
    }
    rom_path = argv[1]; save_path = argv[2];
    max_chunks = atoi(argv[3]);
    if (max_chunks > MAX_CHUNKS) max_chunks = MAX_CHUNKS;
    int seed[64], nseed = 0;
    if (argc >= 5 && argv[4][0]) {
        char buf[256];
        snprintf(buf, sizeof buf, "%s", argv[4]);
        for (char *tok = strtok(buf, ","); tok && nseed < 64; tok = strtok(NULL, ","))
            seed[nseed++] = atoi(tok);
    }
    if (argc >= 6 && argv[5][0]) {
        char buf[256];
        snprintf(buf, sizeof buf, "%s", argv[5]);
        for (char *tok = strtok(buf, ";"); tok && nwaypoints < 16; tok = strtok(NULL, ";")) {
            int x, y;
            if (sscanf(tok, "%d,%d", &x, &y) == 2) {
                waypoints[nwaypoints][0] = x; waypoints[nwaypoints][1] = y; nwaypoints++;
            }
        }
        printf("waypoints:");
        for (int i = 0; i < nwaypoints; i++) printf(" (%d,%d)", waypoints[i][0], waypoints[i][1]);
        printf("\n");
    }
    if (argc >= 7 && argv[6][0]) {
        char buf[256];
        snprintf(buf, sizeof buf, "%s", argv[6]);
        for (char *tok = strtok(buf, ";"); tok && npostwp < 16; tok = strtok(NULL, ";")) {
            int x, y;
            if (sscanf(tok, "%d,%d", &x, &y) == 2) {
                postwp[npostwp][0] = x; postwp[npostwp][1] = y; npostwp++;
            }
        }
        printf("post-key waypoints:");
        for (int i = 0; i < npostwp; i++) printf(" (%d,%d)", postwp[i][0], postwp[i][1]);
        printf("\n");
    }

    /* schedule: one action per chunk, plus the intro end frame. */
    int *sched = calloc(MAX_CHUNKS, sizeof(int));
    int *tried = calloc(MAX_CHUNKS * NACTIONS, sizeof(int)); /* tried[chunk*NACTIONS+a] */
    int nchunks = 0;          /* chunks currently in the schedule */
    int f0 = -1;              /* first playable frame */
    Gb *gb = load_fresh();
    f0 = run_intro(gb);
    printf("playable at frame %d\n", f0);
    fflush(stdout);

    /* visit counts, quantized Mario cells (8px), for the anti-stall penalty */
    int visits[32 * 32];
    memset(visits, 0, sizeof visits);
    double best_score = -1e18;
    int stall = 0, done = 0;

    for (int step = 0; step < max_chunks && !done; ) {
        int mx0, my0, key0, lives0;
        read_state(gb, &mx0, &my0, &key0, &lives0);
        int cur_score_int = 0;
        (void)cur_score_int;
        /* choose the next action: seed first, else fork-evaluate all */
        int chosen = -1;
        if (nchunks < nseed) {
            chosen = seed[nchunks];
            printf("chunk %d: seed %s\n", nchunks, aname[chosen]);
            fflush(stdout);
        } else {
            /* fork one child per untried action */
            int pipes[NACTIONS][2];
            pid_t pids[NACTIONS];
            int nchild = 0;
            for (int a = 0; a < NACTIONS; a++) {
                if (tried[nchunks * NACTIONS + a]) continue;
                if (pipe(pipes[a]) != 0) { perror("pipe"); return 1; }
                fflush(stdout);
                pid_t pid = fork();
                if (pid == 0) {
                    /* child: apply action, report */
                    close(pipes[a][0]);
                    int dead, term;
                    run_chunk(gb, abits[a], CHUNK, &dead, &term);
                    Report r;
                    r.action = a;
                    read_state(gb, &r.mx, &r.my, &r.key, &r.lives);
                    r.dead = dead || (r.lives < lives0);
                    r.term = term;
                    if (write(pipes[a][1], &r, sizeof r) != sizeof r) _exit(3);
                    close(pipes[a][1]);
                    _exit(0);
                }
                close(pipes[a][1]);
                pids[a] = pid;
                nchild++;
            }
            /* collect */
            double best = -1e18;
            Report bestr; memset(&bestr, 0, sizeof bestr);
            int any_alive = 0;
            for (int a = 0; a < NACTIONS; a++) {
                if (tried[nchunks * NACTIONS + a]) continue;
                Report r;
                ssize_t got = read(pipes[a][0], &r, sizeof r);
                close(pipes[a][0]);
                int status; waitpid(pids[a], &status, 0);
                if (got != sizeof r) { printf("chunk %d: child %s failed\n", nchunks, aname[a]); continue; }
                double s;
                if (r.term) s = 1e6;
                else if (r.dead) s = -1e6;
                else if (r.key) {
                    /* pre-key: target the current waypoint (last one is
                     * the key itself) */
                    int tx = 88, ty = 60;
                    if (cur_wp < nwaypoints) { tx = waypoints[cur_wp][0]; ty = waypoints[cur_wp][1]; }
                    s = -10.0 * dist(r.mx, r.my, tx, ty);
                }
                else if (cur_postwp < npostwp) {
                    /* post-key: target the current post-key waypoint */
                    s = 10000.0 - 10.0 * dist(r.mx, r.my, postwp[cur_postwp][0], postwp[cur_postwp][1])
                        + 2.0 * (136 - r.my);
                }
                else s = 10000.0 - 10.0 * dist(r.mx, r.my, 127, 95) + 2.0 * (136 - r.my);
                /* visit penalty (parent-side, from the child's end cell) */
                int cx = r.mx / 8, cy = r.my / 8;
                if (cx >= 0 && cx < 32 && cy >= 0 && cy < 32)
                    s -= 60.0 * visits[cy * 32 + cx];
                s -= 1.0; /* prefer shorter routes */
                printf("  try %-8s -> (%3d,%3d) key=%d dead=%d term=%d score=%.1f\n",
                       aname[a], r.mx, r.my, r.key, r.dead, r.term, s);
                if (!r.dead) any_alive = 1;
                if (s > best) { best = s; bestr = r; }
            }
            fflush(stdout);
            if (!any_alive || best <= -1e6 + 1) {
                printf("chunk %d: ALL actions die -- backtracking\n", nchunks);
                /* fall through to backtrack below with chosen = -1 */
                chosen = -1;
            } else {
                chosen = bestr.action;
                if (bestr.term) {
                    printf("chunk %d: TERMINAL timer=%d via %s at (%d,%d)\n",
                           nchunks, bestr.term, aname[chosen], bestr.mx, bestr.my);
                    done = 1;
                }
                if (best > best_score + 0.5) { best_score = best; stall = 0; }
                else stall++;
                printf("chunk %d: choose %s score=%.1f stall=%d\n",
                       nchunks, aname[chosen], best, stall);
                fflush(stdout);
            }
        }
        if (chosen < 0 || (stall >= STALL_MAX && nchunks >= nseed)) {
            /* ---- backtrack: find the latest chunk with an untried action ---- */
            int back = -1;
            for (int c = nchunks - 1; c >= 0; c--) {
                int untried = 0;
                for (int a = 0; a < NACTIONS; a++)
                    if (!tried[c * NACTIONS + a]) untried++;
                if (untried && c >= nseed) { back = c; break; }
            }
            if (back < 0) {
                printf("BACKTRACK FAILED: no decision point left; giving up at chunk %d\n", nchunks);
                break;
            }
            printf("backtracking to chunk %d (was at %d)\n", back, nchunks);
            /* mark the failed choice tried, truncate the schedule */
            tried[back * NACTIONS + sched[back]] = 1;
            for (int c = back + 1; c < MAX_CHUNKS; c++)
                for (int a = 0; a < NACTIONS; a++) tried[c * NACTIONS + a] = 0;
            nchunks = back;
            best_score = -1e18; stall = 0;
            memset(visits, 0, sizeof visits);
            cur_wp = 0;
            cur_postwp = 0;
            /* replay from scratch to the backtrack point */
            gb_destroy(gb);
            gb = load_fresh();
            int fr = run_intro(gb);
            (void)fr;
            for (int c = 0; c < nchunks; c++) {
                int dead, term;
                run_chunk(gb, abits[sched[c]], CHUNK, &dead, &term);
                int mx, my, key, lives;
                read_state(gb, &mx, &my, &key, &lives);
                int cx = mx / 8, cy = my / 8;
                if (cx >= 0 && cx < 32 && cy >= 0 && cy < 32) visits[cy * 32 + cx]++;
                maybe_advance_wp(mx, my, key);
            }
            printf("replayed to chunk %d\n", nchunks);
            fflush(stdout);
            step++;
            continue;
        }
        /* apply the chosen action to the parent emulator */
        {
            int dead, term;
            run_chunk(gb, abits[chosen], CHUNK, &dead, &term);
            sched[nchunks] = chosen;
            tried[nchunks * NACTIONS + chosen] = 1;
            int mx, my, key, lives;
            read_state(gb, &mx, &my, &key, &lives);
            int cx = mx / 8, cy = my / 8;
            if (cx >= 0 && cx < 32 && cy >= 0 && cy < 32) visits[cy * 32 + cx]++;
            if (key0 && !key) {
                printf("chunk %d: KEY COLLECTED at (%d,%d)\n", nchunks, mx, my);
                dump_state(gb, "key");
            }
            /* Periodic dump every 25 chunks: lets us watch [$ff91]
             * (handler-5 ORs $c3 into it) and $c200 rec0 byte 18
             * (handler 5 sets bit 3) while Mario explores the door
             * block, without waiting for a terminal event. */
            if (nchunks % 25 == 0) {
                char tag[32];
                snprintf(tag, sizeof tag, "chunk%03d", nchunks);
                dump_state(gb, tag);
            }
            /* Block-proximity dump: Mario's OAM box overlapping the
             * $c0-$c3 block (screen x 112-127, y 72-87; OAM x 120-135,
             * y 88-103 for feet, but he stands ON it at y~72, so
             * watch a generous box). This is the decisive record:
             * if handler 5 ($56cc) fires here, rec0 byte 18 gains
             * bit 3 and [$ff91] gains $c3. */
            if (mx >= 108 && mx <= 140 && my >= 56 && my <= 104) {
                char tag[32];
                snprintf(tag, sizeof tag, "block%03d", nchunks);
                dump_state(gb, tag);
            }
            maybe_advance_wp(mx, my, key);
            printf("chunk %d: %s -> (%d,%d) key=%d lives=%d state=%d timer=%d\n",
                   nchunks, aname[chosen], mx, my, key, lives,
                   gb->hram[0x0e], gb->hram[0x10]);
            fflush(stdout);
            if (term) {
                printf("STAGE CLEAR (timer %d) at chunk %d\n", gb->hram[0x10], nchunks);
                dump_state(gb, "clear");
                done = 1;
            }
            nchunks++;
        }
        step++;
    }
    printf("final: %d chunks, done=%d\n", nchunks, done);
    /* print the winning schedule as a gb_headless press spec */
    printf("SCHEDULE f0=%d chunks=%d:\n", f0, nchunks);
    {
        /* merge consecutive chunks with the same buttons into windows */
        int start = f0;
        for (int c = 0; c <= nchunks; c++) {
            if (c == nchunks || (c > 0 && sched[c] != sched[c - 1])) {
                int a = sched[c - 1], end = f0 + c * CHUNK;
                /* emit one window per button in the action */
                for (int b = 0; b < GB_BUTTON_COUNT; b++) {
                    if ((abits[a] >> b) & 1) {
                        static const char *names[GB_BUTTON_COUNT] = {
                            "right", "left", "up", "down", "a", "b", "select", "start" };
                        printf("  %s:%d:%d\n", names[b], start, end);
                    }
                }
                start = end;
            }
        }
    }
    printf("ACTIONS:");
    for (int c = 0; c < nchunks; c++) printf(" %d", sched[c]);
    printf("\n");
    gb_destroy(gb);
    return done ? 0 : 1;
}
