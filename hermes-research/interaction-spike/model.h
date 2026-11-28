#ifndef INTERACTION_MODEL_H
#define INTERACTION_MODEL_H
#include <stdbool.h>

typedef enum { PHASE_PLAY, PHASE_CLEAR_SEQUENCE, PHASE_ADVANCE_REQUESTED } Phase;
typedef struct {
    Phase phase;
    bool carrying_key;
    bool key_on_map;
    unsigned ticks_since_door;
} Game;

void game_init(Game *game);
bool try_pickup(Game *game, bool pickup_pressed, bool eligible_key_in_reach);
bool try_door(Game *game, bool at_door);
void step_clear(Game *game);
#endif
