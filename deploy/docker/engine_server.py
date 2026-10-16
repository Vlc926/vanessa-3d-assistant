import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class DedicatedEngineHTTPHandler(SimpleHTTPRequestHandler):
    extensions_map = SimpleHTTPRequestHandler.extensions_map.copy()
    extensions_map.update({
        '.pmx': 'application/octet-stream',
        '.pmd': 'application/octet-stream',
        '.vmd': 'application/octet-stream',
        '.vrma': 'model/gltf-binary',
        '.vrm': 'model/gltf-binary',
        '.tga': 'image/x-tga',
        '.spa': 'application/octet-stream',
        '.sph': 'application/octet-stream',
        '.js': 'application/javascript',
        '.mjs': 'application/javascript',
        '.json': 'application/json',
        '.wasm': 'application/wasm'
    })

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return

def run_server(port=8899, root_dir=None):
    if root_dir and os.path.exists(root_dir):
        os.chdir(root_dir)
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, DedicatedEngineHTTPHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    run_server(port, root)
