#!/usr/bin/env python3

import sys
import struct
import requests
import json
from urllib.parse import urlparse, parse_qs
import argparse
import http.server
import socketserver
import threading
import random
import base64

# import common functions
from pir_common import setup_parameters, load_segment_db, load_street_name_db, init_server, server_response
from pir_common import GRID_ROWS, GRID_COLS, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, LAT_STEP, LON_STEP, STREET_DB_RECORD_SIZE, STREET_DB_RECORD_ROWS, STREET_DB_RECORD_COLS, STREET_DB_SIZE, SEGMENT_DB_RECORD_SIZE, SEGMENT_DB_RECORD_ROWS, SEGMENT_DB_RECORD_COLS, SEGMENT_DB_SIZE

# Global variables for server state
segment_server = None
segment_params = None
segment_p_params = None
street_server = None
street_params = None
street_p_params = None

def pack_params(params):
    linpir = params.linpir_params
    return {
        'db_rows': params.db_rows,
        'db_cols': params.db_cols,
        'db_record_bit_size': params.db_record_bit_size,
    }

class CustomHandler(http.server.SimpleHTTPRequestHandler):

    # handle client initialization request
    def do_GET(self):
        try:
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)

            if 'init' in params:
                segment_public_params_bytes = segment_p_params.SerializeToString()
                street_public_params_bytes = street_p_params.SerializeToString()
                segment_params_dict = pack_params(segment_params)
                street_params_dict = pack_params(street_params)

                response = {
                    "status": "success",
                    "segment_params": segment_params_dict,
                    "segment_public_params": base64.b64encode(segment_public_params_bytes).decode('ascii'),
                    "street_params": street_params_dict,
                    "street_public_params": base64.b64encode(street_public_params_bytes).decode('ascii')
                }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                print("Sent params and public params to client")


        except Exception as e:
            import traceback
            print(f"ERROR in do_GET: {type(e).__name__}: {e}")
            traceback.print_exc()
            self.send_error(500, f"{type(e).__name__}: {str(e)}")

    # handle client queriees 
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])

        post_data = self.rfile.read(content_length)
        if self.path == '/reverse/street':
            response = server_response(street_server, post_data)
        elif self.path == '/reverse/segment':
            response = server_response(segment_server, post_data)


        self.send_response(200)
        headers={'Content-Type': 'application/octet-stream'}
        self.end_headers()

        response_message = response
        self.wfile.write(response_message)

def main():
    if len(sys.argv) != 3:
        logging.info("Usage: ./pir_server.py <listen_ip> <port_number>")
        logging.info("\nExample:")
        logging.info("  ./pir_server.py 0.0.0.0 8083")
        sys.exit(1)
    server_url = str(sys.argv[1])
    port = int(sys.argv[2])
    global segment_server, segment_params, segment_p_params, street_server, street_params, street_p_params

    # load segment ID database and initalize server
    segment_db = load_segment_db()
    segment_server, segment_params, segment_p_params = init_server(segment_db, SEGMENT_DB_RECORD_ROWS, SEGMENT_DB_RECORD_COLS, SEGMENT_DB_RECORD_SIZE)

    # load street name database and initalize server
    street_db = load_street_name_db()
    street_server, street_params, street_p_params = init_server(street_db, STREET_DB_RECORD_ROWS, STREET_DB_RECORD_COLS, STREET_DB_RECORD_SIZE)

    # start http server
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer((server_url, port), CustomHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    print("Press Ctrl+C to stop...")
    try:
        server_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
        httpd.shutdown()
    return 0

if __name__ == "__main__":
    main()
