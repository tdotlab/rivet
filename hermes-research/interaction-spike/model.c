#include "model.h"

/* This is an interpretation of one observed route, not a port or complete
   model of the original game. Input eligibility and proximity are supplied
   by the caller; they are not inferred here. */
void game_init(Game *game) {
    *game = (Game){ PHASE_PLAY, false, true, 0 };
}

bool try_pickup(Game *game, bool pickup_pressed, bool eligible_key_in_reach) {
    if (game->phase != PHASE_PLAY || game->carrying_key ||
        !game->key_on_map || !pickup_pressed || !eligible_key_in_reach)
        return false;
    game->key_on_map = false;
    game->carrying_key = true;
    return true;
}

bool try_door(Game *game, bool at_door) {
    if (game->phase != PHASE_PLAY || !game->carrying_key || !at_door)
        return false;
    game->phase = PHASE_CLEAR_SEQUENCE;
    game->ticks_since_door = 0;
    return true;
}

void step_clear(Game *game) {
    if (game->phase != PHASE_CLEAR_SEQUENCE)
        return;
    ++game->ticks_since_door;
    /* Calibrated from one recorded frame-3345 to frame-3696 transition.
       Not established to be a universal constant or the original mechanism. */
    if (game->ticks_since_door >= 351)
        game->phase = PHASE_ADVANCE_REQUESTED;
}
