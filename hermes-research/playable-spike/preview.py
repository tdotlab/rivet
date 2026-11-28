"""Local-only C core visual test server; not used by the Windows executable."""
import ctypes as C
import base64
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
class Game(C.Structure):
    _fields_ = [(name, C.c_int) for name in ('x10','y','base_y','jump_tick','facing','carrying','key_available','won','jump_latch','action_latch')]
class Input(C.Structure):
    _fields_ = [(name, C.c_int) for name in ('left','right','jump','action')]
lib=C.CDLL(str(HERE/'game.so'))
lib.game_init.argtypes=[C.POINTER(Game)]
lib.game_step.argtypes=[C.POINTER(Game),Input]
lib.render_game.argtypes=[C.POINTER(Game),C.POINTER(C.c_uint8)]
game=Game();lib.game_init(C.byref(game))
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data=(HERE/'preview.html').read_bytes()
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(data)
    def do_POST(self):
        size=int(self.headers.get('Content-Length','0'))
        if size > 2048: self.send_error(413);return
        try: data=json.loads(self.rfile.read(size) or b'{}')
        except (ValueError,UnicodeDecodeError): self.send_error(400);return
        if self.path=='/reset': lib.game_init(C.byref(game))
        elif self.path=='/tick':
            inp=Input(*(int(bool(data.get(n,False))) for n in ('left','right','jump','action')))
            lib.game_step(C.byref(game),inp)
        else: self.send_error(404);return
        pixels=(C.c_uint8*(160*144))()
        lib.render_game(C.byref(game),pixels)
        result=json.dumps({**{n:getattr(game,n) for n,_ in Game._fields_},'pixels':base64.b64encode(pixels).decode()}).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(result)));self.end_headers();self.wfile.write(result)
    def log_message(self,*args): pass
if __name__=='__main__':
    print('Preview: http://127.0.0.1:8767',flush=True)
    HTTPServer(('127.0.0.1',8767),Handler).serve_forever()
