#!/usr/bin/env python3
import eventlet
eventlet.monkey_patch()  
# Copyright (c) Meta Platforms, Inc. and affiliates
"""
Web UI Launcher for DocAgent Docstring Generator

This script launches the web-based user interface for the docstring generation tool.
The UI provides a more interactive and visual way to use the docstring generator,
with real-time feedback and progress tracking.

Usage:
    python run_web_ui.py [--host HOST] [--port PORT] [--debug]
"""

import argparse
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("docstring_web")

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import flask
        import flask_socketio
        import eventlet
        import yaml
        import tabulate
        import colorama
        return True
    except ImportError as e:
        missing_module = str(e).split("'")[1]
        logger.error(f"Missing dependency: {missing_module}")
        logger.error("Please install all required dependencies with:")
        logger.error("pip install -r requirements-web.txt")
        return False

def main():
    """Parse command line arguments and start the web UI."""
    parser = argparse.ArgumentParser(description='Launch the DocAgent Web UI')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind the server to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind the server to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Print banner
    print("\n" + "=" * 80)
    print("DocAgent Web Interface".center(80))
    print("=" * 80)
    
    # Import and run the web app
    try:
        # First try to import eventlet to ensure it's properly initialized
        import eventlet
        eventlet.monkey_patch()
        
        from src.web.app import create_app
        
        app, socketio = create_app(debug=args.debug)
        
        logger.info(f"Starting DocAgent Web UI at: http://{args.host}:{args.port}")
        logger.info("Press Ctrl+C to stop the server")
        
        # Start the server
        socketio.run(app, host=args.host, port=args.port, debug=args.debug, allow_unsafe_werkzeug=True)
        
        return 0
    except ImportError as e:
        logger.error(f"Error importing web application: {e}")
        logger.error("Make sure the src/web directory exists and contains the necessary files.")
        return 1
    except Exception as e:
        logger.error(f"Error running web application: {e}")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0) 