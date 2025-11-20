from dataclasses import dataclass
import json
import os
import platform
import threading
import time
import traceback
import binascii
import http.server
import socketserver
import requests

HTTP_PORT = 8088

class HttpHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        if "favicon" in str(self.requestline):
            resp = ""
        else:
            resp = open("subtitles.html","r").read()
        self.wfile.write(resp.encode("utf-8"))

    
    def do_POST(self):
        global _cur_text
        #print("postreq:", self.request)
        while not _cur_text:
            time.sleep(.1)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(_cur_text.encode("utf-8"))
        _cur_text = ""

    def log_message(self, format, *args):
        return
        return super().log_message(format, *args)
_cur_text = ""
def set_text(text:str):
    global _cur_text
    if _cur_text != text:
        print(text)
        _cur_text = text

_server: socketserver.TCPServer = None
def start_server():
    if _server:
        print("Server already running")
        return
    def listen():
        global _server
        set_text("*")
        # Run server
        with socketserver.TCPServer(("", HTTP_PORT), HttpHandler) as httpd:
            _server = httpd
            print(f"Serving on port {HTTP_PORT}...")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down server.")
                httpd.server_close()

    threading.Thread(target=listen, daemon=True).start()

if __name__ == "__main__":
    start_server()

    subs = ["Apa","asdfdfasdkj asdf jklö asdf df", "gfagfgh sdgfas"]
    idx = 0
    while True:
        set_text(subs[idx%len(subs)])
        idx += 1
        time.sleep(2)

