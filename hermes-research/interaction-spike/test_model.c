#include "model.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    Game g;
    unsigned i;
    game_init(&g);
    assert(!try_door(&g, true));
    assert(!try_pickup(&g, false, true));
    assert(!try_pickup(&g, true, false));
    assert(g.key_on_map && !g.carrying_key);
    assert(try_pickup(&g, true, true));
    assert(!g.key_on_map && g.carrying_key);
    assert(!try_pickup(&g, true, true));
    assert(!try_door(&g, false));
    assert(try_door(&g, true));
    assert(!try_door(&g, true));
    assert(!try_pickup(&g, true, true));
    for (i = 0; i < 350; ++i) step_clear(&g);
    assert(g.phase == PHASE_CLEAR_SEQUENCE);
    step_clear(&g);
    assert(g.phase == PHASE_ADVANCE_REQUESTED);
    step_clear(&g);
    assert(g.phase == PHASE_ADVANCE_REQUESTED);
    puts("PASS: pickup/door conditions, one-shot transitions, 351-tick replay milestone");
    return 0;
}
