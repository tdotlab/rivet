#include "game.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
 Game g; Input none={0},right={0,1,0,0},jump={0,0,1,0},action={0,0,0,1}; int i, min;
 game_init(&g); assert(g.x10==180 && g.y==120 && g.key_available && !g.won);
 for(i=0;i<20;i++) game_step(&g,right);
 assert(g.x10>180);
 game_init(&g); min=g.y; game_step(&g,jump);
 for(i=1;i<45;i++){game_step(&g,jump);if(g.y<min)min=g.y;}
 assert(min==104 && g.y==120);
 game_step(&g,none); game_step(&g,action); assert(!g.carrying);
 g.x10=850; g.y=108; g.base_y=108; game_step(&g,none);game_step(&g,action);assert(g.carrying&&!g.key_available);
 g.x10=1410; g.y=120; g.base_y=120; game_step(&g,none);assert(g.won);
 puts("PASS: walking, grounded jump arc, pickup range, key and exit");
 game_init(&g);
 for(i=0;i<58;i++)game_step(&g,right);
 {Input jump_right={0,1,1,0};game_step(&g,jump_right);}
 for(i=0;i<38;i++)game_step(&g,right);
 assert(g.base_y==108 && g.y==108 && g.x10/10>=67 && g.x10/10<=103);
 while(g.x10/10<85)game_step(&g,right);
 game_step(&g,action);assert(g.carrying);
 for(i=0;i<120 && !g.won;i++)game_step(&g,right);
 assert(g.won);
 puts("PASS: full route from spawn via platform to key and door"); return 0;
}
