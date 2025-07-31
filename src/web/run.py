# Copyright (c) Meta Platforms, Inc. and affiliates
"""
Entry point for running the docstring generation visualization web application.

This script creates and starts the Flask application for visualizing the
docstring generation process.
"""

import os
import sys
import argparse
from pathlib import Path

from .app import create_app

def main():
    """
    Parse command line arguments and start the web application.
    """
    parser = argparse.ArgumentParser(description='Start the docstring generation visualization web application')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind the server to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind the server to')
    parser.add_argument('--debug', action='store_true', help='Run the application in debug mode')
    
    args = parser.parse_args()
    
    # Create the Flask application
    app, socketio = create_app(debug=args.debug)
    
    print(f"Starting docstring generation visualization web application on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop the server")
    
    # Start the server
    socketio.run(app, host=args.host, port=args.port, debug=args.debug, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    # Add the parent directory to the path so we can import the module
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    main() 