#!/usr/bin/env python3

import struct
import sys
import time
import requests
import json
import argparse
import threading
import random
import base64
import logging

logging.basicConfig(level=logging.INFO)


# import common functions
from pir_common import setup_parameters, load_segment_db, load_street_name_db, init_client, gen_query, recover_record 
from pir_common import GRID_ROWS, GRID_COLS, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, LAT_STEP, LON_STEP, STREET_DB_RECORD_SIZE, STREET_DB_RECORD_ROWS, STREET_DB_RECORD_COLS, STREET_DB_SIZE, SEGMENT_DB_RECORD_SIZE, SEGMENT_DB_RECORD_ROWS, SEGMENT_DB_RECORD_COLS, SEGMENT_DB_SIZE

sys.path.insert(0, 'bazel-bin/hintless_simplepir')
import hintless_pir_cpp

# Convert to Grid ID
def latlon_to_grid(lat, lon):
    if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
        return None

    row = int((lat - LAT_MIN) / LAT_STEP)
    col = int((lon - LON_MIN) / LON_STEP)

    row = min(max(row, 0), GRID_ROWS - 1)
    col = min(max(col, 0), GRID_COLS - 1)

    return (row, col)

def main():

    if len(sys.argv) < 4:
        logging.info("Usage: ./pir_client.py <latitude> <longitude> <init_server_url_and_port> <query_server_url_and_port>")
        logging.info("\nExample:")
        logging.info("  ./pir_client.py 39.9075 116.3974 localhost:8083")
        logging.info("  <query_server_url_and_port> is optional and should be used if a different port is used for queries")
        logging.info(f"\nValid range:")
        logging.info(f"  Latitude:  [{LAT_MIN}, {LAT_MAX}]")
        logging.info(f"  Longitude: [{LON_MIN}, {LON_MAX}]")
        sys.exit(1)
    server_url = str(sys.argv[3])
    if len(sys.argv) > 4:
        query_server_url = str(sys.argv[4])
    else:
        query_server_url = server_url 

    # Requests parameters from server and process received data 
    response = requests.get(f"http://{server_url}/pir?init=1").json()
    segment_params = hintless_pir_cpp.Parameters()
    segment_resp = response['segment_params']
    segment_params = setup_parameters(segment_resp['db_rows'], segment_resp['db_cols'], int(segment_resp['db_record_bit_size'] / 8))
    segment_public_params = hintless_pir_cpp.HintlessPirServerPublicParams()
    segment_public_params.ParseFromString(
        base64.b64decode(response['segment_public_params'])
    )
    street_params = hintless_pir_cpp.Parameters()
    street_resp = response['street_params']
    street_params = setup_parameters(street_resp['db_rows'], street_resp['db_cols'], int(street_resp['db_record_bit_size'] / 8))
    street_public_params = hintless_pir_cpp.HintlessPirServerPublicParams()
    street_public_params.ParseFromString(
        base64.b64decode(response['street_public_params'])
    )

    # initialize both PIR clients
    segment_client = init_client(segment_params, segment_public_params)
    street_client = init_client(street_params, street_public_params)

    try:
        lat = float(sys.argv[1])
        lon = float(sys.argv[2])
    except ValueError:
        logging.info("Error: Invalid coordinates. Must be numbers.")
        sys.exit(1)

    if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
        logging.info('Coordinates out of bounds. Valid range: Lat [{LAT_MIN}, {LAT_MAX}], Lon [{LON_MIN}, {LON_MAX}]')
        sys.exit(1)

    # Convert coordinates to grid id and then to query_index
    grid_coords = latlon_to_grid(lat, lon)
    if grid_coords is None:
        logging.info('Failed to convert coordinates to grid')
        sys.exit(1)
    row, col = grid_coords
    query_index = row * GRID_COLS + col

    # Send PIR query to get street segment ID from Grid ID
    query = gen_query(segment_client, query_index) 
    server_response = requests.post(
        f"http://{query_server_url}/reverse/segment",
        data=query,
        headers={'Content-Type': 'application/octet-stream'}
    )
    if server_response.status_code != 200:
        logging.info(f"Fail: {server_response.status_code}")
    #else:
    #    logging.info("Success")
    
    # Recover segment ID from response 
    recovered_record =  recover_record(segment_client, server_response.content)
    segment_id = struct.unpack('<H', recovered_record)[0]
    #logging.info(f"recovered_id: {segment_id}")

    # just for testing
    #segment_db = load_segment_db() 
    #expected_record = segment_db[query_index]
    #if recovered_record == expected_record:
    #    logging.info(f"   ✓ SUCCESS - Record matches!")
    #    logging.info(f"   Expected: {expected_record.hex()}")
    #    logging.info(f"   Got:      {recovered_record.hex()}")
    #    logging.info(f"   Dec:      {recovered_record}")
    #else:
    #    logging.info(f"   ✗ FAILURE - Record mismatch!")
    #    logging.info(f"   Expected: {expected_record.hex()}")
    #    logging.info(f"   Got:      {recovered_record.hex()}")

    #
    # Get street name
    #
    #


    # Send query to response segment ID to street name 
    query = gen_query(street_client, segment_id) 
    server_response = requests.post(
        f"http://{query_server_url}/reverse/street",
        data=query,
        headers={'Content-Type': 'application/octet-stream'}
    )
    if server_response.status_code != 200:
        logging.info(f"Fail: {server_response.status_code}")
    #else:
    #    logging.info("Success")
    
    # Recover Street name from received data
    street_name =  recover_record(street_client, server_response.content)
    # Hex
    #logging.info(f"Hex: {street_name.hex()}")
    # UTF-8
    text = street_name.decode('utf-8', errors='ignore').rstrip('\x00')
    print(text)

    # just for testing
    #street_db = load_street_name_db() 
    #expected_record = street_db[segment_id]
    #if street_name == expected_record:
    #    logging.info(f"   ✓ SUCCESS - Record matches!")
    #    logging.info(f"   Expected: {expected_record.hex()}")
    #    logging.info(f"   Got:      {recovered_record.hex()}")
    #    logging.info(f"   Dec:      {recovered_record}")
    #else:
    #    logging.info(f"   ✗ FAILURE - Record mismatch!")
    #    logging.info(f"   Expected: {expected_record.hex()}")
    #    logging.info(f"   Got:      {recovered_record.hex()}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
