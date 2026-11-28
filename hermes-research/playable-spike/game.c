#include "game.h"
#include <stdlib.h>

/* One observed stationary jump, simplified at landing. This is sampled
   motion, not a reconstruction of the original physics routine. */
static const int arc[] = {0,-2,-3,-5,-6,-8,-9,-10,-11,-12,-14,-14,-15,
  -16,-16,-16,-16,-16,-16,-16,-16,-16,-15,-15,-15,-14,-13,-13,-12,
  -11,-10,-8,-7,-6,-5,-3,-2,-1,0};
#define ARC_N ((int)(sizeof arc / sizeof arc[0]))

void game_init(Game *g) {
 *g=(Game){180,120,120,-1,1,0,1,0,0,0};
}
void game_step(Game *g, Input in) {
 int dx, x, previous;
 if(g->won) return;
 dx=(in.right!=0)-(in.left!=0);
 if(dx) {g->x10+=dx*7; g->facing=dx;}
 if(g->x10<80) g->x10=80;
 if(g->x10>1510) g->x10=1510;
 x=g->x10/10;
 if(g->jump_tick==-1 && g->base_y==108 && (x<67 || x>103)) {
   g->jump_tick=-2; /* walk off an edge and fall */
 }
 if(in.jump && !g->jump_latch && g->jump_tick==-1) {
   g->jump_tick=0; g->base_y=g->y;
 }
 g->jump_latch=!!in.jump;
 if(g->jump_tick==-2) {
   g->y+=1;
   if(g->y>=120){g->y=120;g->base_y=120;g->jump_tick=-1;}
 }
 if(g->jump_tick>=0) {
   previous=g->y;
   g->y=g->base_y+arc[g->jump_tick];
   if(g->jump_tick>20 && previous<=108 && g->y>=108 &&
      x>=67 && x<=103 && g->base_y>108) {
      g->y=108;g->base_y=108;g->jump_tick=-1;
   } else if(g->y>=120 && g->jump_tick>20) {
      g->y=120;g->base_y=120;g->jump_tick=-1;
   } else if(++g->jump_tick>=ARC_N) {
      if(g->base_y==108 && (x<67 || x>103)) {
         g->base_y=120; g->y=120;
      }
      g->jump_tick=-1;
   }
 }
 if(in.action && !g->action_latch && g->key_available &&
    abs(x-85)<=9 && abs(g->y-108)<=10) {
    g->carrying=1; g->key_available=0;
 }
 g->action_latch=!!in.action;
 if(g->carrying && x>=139 && g->y>=115) g->won=1;
}
