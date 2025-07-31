#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates

# Default values
HOST="0.0.0.0"
PORT="8080"
DEBUG=""

# Show help function
show_help() {
  echo "Usage: ./start_server.sh [options]"
  echo ""
  echo "Options:"
  echo "  -h, --host HOST     Host address to bind to (default: 0.0.0.0)"
  echo "  -p, --port PORT     Port to run the server on (default: 8080)"
  echo "  -d, --debug         Run in debug mode"
  echo "  --help              Show this help message"
  echo ""
  echo "Examples:"
  echo "  ./start_server.sh                   # Run on default host:port (0.0.0.0:8080)"
  echo "  ./start_server.sh -p 9090           # Run on port 9090"
  echo "  ./start_server.sh -h 127.0.0.1      # Run on localhost only"
  echo "  ./start_server.sh -d                # Run in debug mode"
  echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--host)
      HOST="$2"
      shift 2
      ;;
    -p|--port)
      PORT="$2"
      shift 2
      ;;
    -d|--debug)
      DEBUG="--debug"
      shift
      ;;
    --help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      show_help
      exit 1
      ;;
  esac
done

# Display startup message
echo "Starting DocAgent Web Server..."
echo "Host: $HOST"
echo "Port: $PORT"
if [ -n "$DEBUG" ]; then
  echo "Mode: DEBUG (not recommended for production)"
else
  echo "Mode: Production"
fi
echo ""

# Run the Flask app with the specified options
python app.py --host "$HOST" --port "$PORT" $DEBUG 