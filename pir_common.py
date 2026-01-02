import sys
import time
import logging

logging.basicConfig(level=logging.INFO)

sys.path.insert(0, 'bazel-bin/hintless_simplepir')
import hintless_pir_cpp

# Grid configuration, BEIJING specific
GRID_ROWS = 256 
GRID_COLS = 256 
LAT_MIN = 39.84
LAT_MAX = 39.99
LON_MIN = 116.28
LON_MAX = 116.48
LAT_STEP = (LAT_MAX - LAT_MIN) / GRID_ROWS
LON_STEP = (LON_MAX - LON_MIN) / GRID_COLS

# Database parameters, BEIJING specific
STREET_DB_RECORD_SIZE = 60 
STREET_DB_RECORD_ROWS = 134 
STREET_DB_RECORD_COLS = 134 
STREET_DB_SIZE = STREET_DB_RECORD_ROWS*STREET_DB_RECORD_COLS
SEGMENT_DB_RECORD_SIZE = 2 
SEGMENT_DB_RECORD_ROWS = 256 
SEGMENT_DB_RECORD_COLS = 256 
SEGMENT_DB_SIZE = SEGMENT_DB_RECORD_ROWS*SEGMENT_DB_RECORD_COLS

# Setup PIR parameters. Optimized for this use-case
def setup_parameters(db_rows, db_cols, record_size_bytes):
    params = hintless_pir_cpp.Parameters()
    params.db_rows = db_rows 
    params.db_cols = db_cols 
    params.db_record_bit_size = record_size_bytes * 8
    params.lwe_secret_dim = 1024
    params.lwe_modulus_bit_size = 32
    params.lwe_plaintext_bit_size = 8
    params.lwe_error_variance = 8
    params.prng_type = hintless_pir_cpp.PrngType.PRNG_TYPE_HKDF

    linpir_params = hintless_pir_cpp.LinPirRlweParameters()
    linpir_params.log_n = 12
    linpir_params.qs = [35184371884033, 35184371703809]
    linpir_params.ts = [2056193, 1990657]
    linpir_params.gadget_log_bs = [16, 16]
    linpir_params.error_variance = 8
    linpir_params.prng_type = hintless_pir_cpp.PrngType.PRNG_TYPE_HKDF
    linpir_params.rows_per_block = 1024

    params.linpir_params = linpir_params
    return params

# Load segment ID database
def load_segment_db():
    try:
        
        with open('data/database/beijing_grid_to_id.bin', 'rb') as f:
        
            database_records = []
            for i in range(SEGMENT_DB_SIZE):
                f.seek(i * SEGMENT_DB_RECORD_SIZE)
                record = f.read(SEGMENT_DB_RECORD_SIZE)
                database_records.append(record)

        for i in range(SEGMENT_DB_SIZE):
            record = database_records[i]

        return database_records 
    except FileNotFoundError:
        return None

# Load street name database 
def load_street_name_db():
    try:
        
        with open('data/database/street_names.bin', 'rb') as f:
        
            database_records = []
            for i in range(STREET_DB_SIZE):
                f.seek(i * STREET_DB_RECORD_SIZE)
                record = f.read(STREET_DB_RECORD_SIZE)
                database_records.append(record)

        for i in range(STREET_DB_SIZE):
            record = database_records[i]
            text = record.decode('utf-8', errors='ignore').rstrip('\x00')

        return database_records 
    except FileNotFoundError:
        return None

# Initialize PIR Client
def init_client(params, public_params):

    try:
        client = hintless_pir_cpp.Client.Create(params, public_params)
        return client 
    except Exception as e:
        logging.info(f"Error creating client: {e}")
        return False

# Initialize PIR Server 
def init_server(database_records, db_rows, db_cols, record_size):
    params = setup_parameters(db_rows, db_cols, record_size)

    logging.info("\nCreating PIR server...")
    start = time.time()
    try:
        server = hintless_pir_cpp.Server.Create(params)
        server_create_time = time.time() - start
    except Exception as e:
        logging.info(f"Error creating server: {e}")
        return False

    # Load database into server
    logging.info("\nLoading database into server")
    start = time.time()
    database = server.GetDatabase()
    for record in database_records:
        database.Append(record)
    db_load_time = time.time() - start

    # Preprocess server
    logging.info("\n Preprocessing server (please wait, this takes up to 1 minute)...")
    start = time.time()
    try:
        server.Preprocess()
        preprocess_time = time.time() - start
        logging.info(f"Preprocessing completed in {preprocess_time:.3f}s ({preprocess_time/60:.2f} min)")
    except Exception as e:
        logging.info(f"Error during preprocessing: {e}")
        return False

    # Get public parameters to be sent to client
    start = time.time()
    public_params = server.GetPublicParams()
    pubparam_time = time.time() - start
    return server, params, public_params

# Client generates query
def gen_query(client, query_index):
        try:
            request_bytes = client.GenerateRequest(query_index)
            return request_bytes
        except Exception as e:
            logging.info(f"Error generating request: {e}")
            return 0

# Client recovers data after receiving encrypted response
def recover_record(client, response_bytes):
        try:
            recovered_record = client.RecoverRecord(response_bytes)
            return recovered_record
        except Exception as e:
            logging.info(f"Error recovering record: {e}")
            return 0 

# Server handles request
def server_response(server, request_bytes):
        logging.info(f"Server processing request (should take under 2s)")
        start = time.time()
        try:
            response_bytes = server.HandleRequest(request_bytes)
            server_response_time = time.time() - start
            logging.info(f"Response generated in {server_response_time:.3f}s")
            return response_bytes
        except Exception as e:
            logging.info(f"Error handling request: {e}")
            return str(e).encode() 
