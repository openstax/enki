#!/usr/bin/env python

# Python SimpleHTTPServer with CORS, supporting both Python 2 and 3
# Thanks to source https://gist.github.com/khalidx/6d6ebcd66b6775dae41477cffaa601e5
#
# Usage: python simple_http_server_cors.py <port>

try:
    # try to use Python 3
    from http.server import HTTPServer, SimpleHTTPRequestHandler, test as test_orig
    import sys
    def test (*args):
        test_orig(*args, port=int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
except ImportError: # fall back to Python 2
    from BaseHTTPServer import HTTPServer, test
    from SimpleHTTPServer import SimpleHTTPRequestHandler

class CORSRequestHandler (SimpleHTTPRequestHandler):
    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

if __name__ == '__main__':
    test(CORSRequestHandler, HTTPServer)