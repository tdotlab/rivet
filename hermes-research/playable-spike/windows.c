#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include "game.h"
#include "render.h"
static Game game;
static Input input;
static HWND window;
static void paint(HDC dc){
 RECT client; BITMAPINFO info; static uint8_t pixels[WIDTH*HEIGHT]; static uint32_t rgb[WIDTH*HEIGHT];
 static const uint8_t grey[4]={252,188,104,24};int i,scale,ox,oy;
 GetClientRect(window,&client);FillRect(dc,&client,(HBRUSH)GetStockObject(DKGRAY_BRUSH));
 scale=(client.right/WIDTH < client.bottom/HEIGHT ? client.right/WIDTH : client.bottom/HEIGHT);if(scale<1)scale=1;
 ox=(client.right-WIDTH*scale)/2;oy=(client.bottom-HEIGHT*scale)/2;
 render_game(&game,pixels);
 for(i=0;i<WIDTH*HEIGHT;i++){uint32_t c=grey[pixels[i]];rgb[i]=(c<<16)|(c<<8)|c;}
 ZeroMemory(&info,sizeof(info));info.bmiHeader.biSize=sizeof(info.bmiHeader);info.bmiHeader.biWidth=WIDTH;
 info.bmiHeader.biHeight=-HEIGHT;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
 SetStretchBltMode(dc,COLORONCOLOR);
 StretchDIBits(dc,ox,oy,WIDTH*scale,HEIGHT*scale,0,0,WIDTH,HEIGHT,rgb,&info,DIB_RGB_COLORS,SRCCOPY);
}
static LRESULT CALLBACK proc(HWND h,UINT msg,WPARAM wp,LPARAM lp){
 switch(msg){
 case WM_CREATE:SetTimer(h,1,17,NULL);return 0;
 case WM_TIMER:game_step(&game,input);InvalidateRect(h,NULL,FALSE);return 0;
 case WM_ERASEBKGND:return 1;
 case WM_PAINT:{PAINTSTRUCT ps;HDC dc=BeginPaint(h,&ps);paint(dc);EndPaint(h,&ps);return 0;}
 case WM_KEYDOWN:case WM_KEYUP:{int down=(msg==WM_KEYDOWN);switch(wp){
 case VK_LEFT:input.left=down;break;case VK_RIGHT:input.right=down;break;
 case VK_SPACE:case 'Z':input.jump=down;break;case 'X':input.action=down;break;
 case 'R':if(down && !(lp & (1L<<30))){game_init(&game);input=(Input){0};}break;
 case VK_ESCAPE:if(down)DestroyWindow(h);break;}return 0;}
 case WM_KILLFOCUS:input=(Input){0};return 0;
 case WM_DESTROY:KillTimer(h,1);PostQuitMessage(0);return 0;
 }return DefWindowProc(h,msg,wp,lp);
}
int WINAPI WinMain(HINSTANCE instance,HINSTANCE previous,LPSTR command,int show){
 WNDCLASSA wc={0};MSG msg;(void)previous;(void)command;
 game_init(&game);wc.lpfnWndProc=proc;wc.hInstance=instance;wc.hCursor=LoadCursor(NULL,IDC_ARROW);wc.lpszClassName="RivetMotionSpike";
 if(!RegisterClassA(&wc))return 1;
 window=CreateWindowA(wc.lpszClassName,"Key & Door | arrows move | Z jump | X pick up | R reset",WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,656,615,NULL,NULL,instance,NULL);
 if(!window)return 1;
 ShowWindow(window,show);UpdateWindow(window);
 while(GetMessageA(&msg,NULL,0,0)>0){TranslateMessage(&msg);DispatchMessageA(&msg);}return (int)msg.wParam;
}
