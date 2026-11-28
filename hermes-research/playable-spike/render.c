#include "render.h"
#include <string.h>
/* Indices 0..3: paper, light grey, dark grey, ink. All sprites are
   hand-authored for this experiment, not extracted from the game. */
static void pixel(uint8_t *p,int x,int y,int c){if(x>=0&&x<WIDTH&&y>=0&&y<HEIGHT)p[y*WIDTH+x]=(uint8_t)c;}
static void box(uint8_t *p,int x,int y,int w,int h,int c){int i,j;for(j=0;j<h;j++)for(i=0;i<w;i++)pixel(p,x+i,y+j,c);}
static void sprite(uint8_t *p,int x,int y,const char *const *s,int h,int flip){
 int j,i,w=(int)strlen(s[0]);for(j=0;j<h;j++)for(i=0;i<w;i++){
  int c=s[j][flip ? w-1-i : i]-'0'; if(c>=0&&c<=3)pixel(p,x+i,y+j,c);
 }
}
static const char *const explorer[]={
 "...33333...",
 "..3222223..",
 ".321111123.",
 ".321333123.",
 ".321113123.",
 "..3211113..",
 "...33333...",
 "..3211123..",
 ".332111233.",
 ".321222123.",
 ".321212123.",
 "..3222223..",
 "..331.133..",
 "..33...33..",
 ".333...333."
};
static const char *const key[]={
 ".3333....",
 "321123...",
 "321123...",
 ".3333333.",
 "....3.3..",
 "....3.33."
};
static void small_text(uint8_t *p,int x,int y,const char *s){
 /* Five rows per glyph, fixed-width, enough for a small in-game banner. */
 static const struct {char c;const char *r[5];} f[]={
 {'D',{"110","101","101","101","110"}},{'O',{"111","101","101","101","111"}},
 {'N',{"101","111","111","111","101"}},{'E',{"111","100","110","100","111"}},
 {'!',{"1","1","1","0","1"}}};
 for(;*s;s++){unsigned k;for(k=0;k<sizeof(f)/sizeof(f[0]);k++)if(f[k].c==*s){int a,b,w=(int)strlen(f[k].r[0]);for(b=0;b<5;b++)for(a=0;a<w;a++)if(f[k].r[b][a]=='1')pixel(p,x+a,y+b,3);x+=w+1;break;}}
}
void render_game(const Game *g,uint8_t p[WIDTH*HEIGHT]){
 int x,y,i;
 memset(p,0,WIDTH*HEIGHT);
 /* Fine masonry suggests a room without copying the reference stage. */
 box(p,0,0,160,2,3);box(p,0,2,160,1,1);
 box(p,0,16,160,1,1);
 for(y=30;y<105;y+=16){
  for(x=8+(y%32?0:8);x<155;x+=16){pixel(p,x,y,1);pixel(p,x+1,y,1);pixel(p,x,y+1,1);}
 }
 box(p,8,9,2,2,3);box(p,12,9,2,2,2);box(p,16,9,2,2,1);
 /* Portal, placed at the existing exit collision area. */
 box(p,138,93,19,27,3);box(p,140,95,15,25,1);box(p,142,97,11,23,3);
 box(p,144,99,7,20,2);box(p,149,108,1,2,0);
 /* Elevated scaffold and two supports. */
 box(p,67,107,37,5,3);box(p,68,108,35,2,1);
 for(x=70;x<102;x+=6)box(p,x,108,3,1,0);
 box(p,69,112,2,8,2);box(p,99,112,2,8,2);
 for(y=113;y<120;y+=3){box(p,69,y,2,1,3);box(p,99,y,2,1,3);}
 /* A solid floor with staggered seams, rendered with hard pixels. */
 box(p,0,120,160,24,3);box(p,0,121,160,2,1);box(p,0,123,160,20,2);
 for(y=126;y<144;y+=6){box(p,0,y,160,1,3);for(x=((y/6)%2)*8;x<160;x+=16)box(p,x,y+1,1,5,3);}
 if(g->key_available)sprite(p,81,101,key,6,0);
 i=g->x10/10; sprite(p,i-5,g->y-15,explorer,15,g->facing<0);
 if(g->carrying)sprite(p,i-4,g->y-22,key,6,0);
 if(g->won){box(p,57,44,46,13,3);box(p,59,46,42,9,0);small_text(p,70,48,"DONE!");}
}
