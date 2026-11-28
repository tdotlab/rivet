#ifndef RENDER_H
#define RENDER_H
#include "game.h"
#include <stdint.h>
#define WIDTH 160
#define HEIGHT 144
void render_game(const Game *game, uint8_t pixels[WIDTH*HEIGHT]);
#endif
