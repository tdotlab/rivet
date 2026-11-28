#ifndef GAME_H
#define GAME_H

typedef struct {
  int x10, y, base_y, jump_tick, facing, carrying, key_available, won;
  int jump_latch, action_latch;
} Game;
typedef struct { int left, right, jump, action; } Input;
void game_init(Game *g);
void game_step(Game *g, Input input);
#endif
