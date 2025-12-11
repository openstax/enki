#!/usr/bin/env python

# Python SimpleHTTPServer with CORS, supporting both Python 2 and 3
# Thanks to source https://gist.github.com/khalidx/6d6ebcd66b6775dae41477cffaa601e5
#
# Usage: python simple_http_server_cors.py <port>

try:
    # try to use Python 3
    from http.server import HTTPServer, SimpleHTTPRequestHandler, test as test_orig
    import sys
    def test(*args):
        test_orig(*args, port=int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
except ImportError: # fall back to Python 2
    from BaseHTTPServer import HTTPServer, test
    from SimpleHTTPServer import SimpleHTTPRequestHandler

import json
import mimetypes
from pathlib import Path
class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)
    
    def guess_type(self, path):
        """Override default MIME detection"""
        first_guess, _ = mimetypes.guess_type(path)
        if first_guess is not None:
            return first_guess
        file_path = Path(path)
        metadata_path = file_path.with_suffix('.json')
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_bytes())
            from_metadata = metadata.get('mime_type', None)
            if from_metadata is not None:
                return from_metadata
        return 'application/octet-stream'

if __name__ == '__main__':
    test(CORSRequestHandler, HTTPServer)