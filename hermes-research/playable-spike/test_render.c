#include "game.h"
#include "render.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void){
 Game g; static uint8_t a[WIDTH*HEIGHT],b[WIDTH*HEIGHT]; int i, seen[4]={0};
 game_init(&g); render_game(&g,a);
 for(i=0;i<WIDTH*HEIGHT;i++){assert(a[i]<4);seen[a[i]]=1;}
 assert(seen[0]&&seen[1]&&seen[2]&&seen[3]);
 g.key_available=0;g.carrying=1;render_game(&g,b);assert(memcmp(a,b,sizeof a));
 g.won=1;render_game(&g,a);assert(memcmp(a,b,sizeof a));
 printf("PASS: four shades only, carrying and victory change the actual framebuffer\n");return 0;
}
