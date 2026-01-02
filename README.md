# Private Geocoder with Hintless PIR

A simple setup to do privacy-preserving reverse geocoding service using Hintless PIR. Client and server scripts to query location data without revealing queries to the server.

## Prerequisites

- Python 3.8+
- Bazel 6.0+ ([Installation Guide](https://bazel.build/install))
- GCC 9+ or Clang 10+
- Linux (tested on Ubuntu 20.04+)

## Quick Start

### 1. Clone and Build Hintless PIR

```bash
# Clone the repository
git clone https://github.com/google/hintless_pir.git
cd hintless_pir

# Checkout the version this project was built with
git checkout 4be2ae8  # Based on IACR ePrint 2023/1733

# Build the Python bindings (optimized)
bazel build -c opt //hintless_simplepir:hintless_pir_cpp.so
```

### 2. Copy the Compiled Library

```bash
# Create directory structure in your geocoder project
mkdir -p /path/to/private_geocoder/bazel-bin/hintless_simplepir

# Copy the compiled library
cp bazel-bin/hintless_simplepir/hintless_pir_cpp.so \
   /path/to/private_geocoder/bazel-bin/hintless_simplepir/
```
### 3. Prepare Database
Currently, there is an exisiting database for Beijing. Adding scripts for automatic database generation is work-in-progress.
- `data/database/beijing_grid_to_id.bin` - Segment database (256×256, 2 bytes/record)
- `data/database/street_names.bin` - Street names database (134×134, 60 bytes/record)
  

## Usage

### Start Server

```bash
python3 pir_server.py 0.0.0.0 8083
```

Wait for preprocessing to complete (~2-5 minutes).

### Query from Client

```bash
python3 pir_client.py <latitude> <longitude>

# Example (Beijing coordinates)
python3 pir_client.py 39.9075 116.3974
```

## How It Works

1. Client requests server parameters: `GET /pir?init=1`
2. Client generates PIR query for segment database: `POST /segment`
3. Client generates PIR query for street database: `POST /street`
4. Server responds without learning what was queried

## Files

- `pir_server.py` - PIR server
- `pir_client.py` - PIR client
- `pir_common.py` - Shared utilities

## References

- Paper: [Hintless Single-Server PIR (IACR ePrint 2023/1733)](https://eprint.iacr.org/2023/1733)
- Code: [google/hintless_pir](https://github.com/google/hintless_pir)

## License

Uses Google's Hintless PIR library (Apache 2.0).
