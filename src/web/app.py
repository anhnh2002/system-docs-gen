# Copyright (c) Meta Platforms, Inc. and affiliates
"""
Main Flask application for the docstring generation visualization.

This module defines the Flask application, routes, and event handlers for
the web-based docstring generation visualization system.
"""

import os
import json
import yaml
import threading
import eventlet
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO

# Patch standard library for async support with eventlet
eventlet.monkey_patch()

from . import config_handler
from . import visualization_handler
from . import process_handler

def create_app(debug=True):
    """
    Create and configure the Flask application.
    
    Args:
        debug: Whether to run the application in debug mode
        
    Returns:
        The configured Flask application instance
    """
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    app.config['SECRET_KEY'] = 'docstring-generator-secret!'
    app.config['DEBUG'] = debug
    
    # Initialize SocketIO for real-time updates with async mode
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
    
    # Store application state
    app.config['APP_STATE'] = {
        'is_running': False,
        'config': {},
        'repo_path': '',
        'process': None
    }
    
    # Routes
    @app.route('/')
    def index():
        """Render the main application page."""
        return render_template('index.html')
    
    @app.route('/api/default_config')
    def get_default_config():
        """Get the default configuration from agent_config.yaml."""
        return jsonify(config_handler.get_default_config())
    
    @app.route('/api/test_api', methods=['POST'])
    def test_api():
        """Test the LLM API connection with a simple query."""
        data = request.json
        
        if not data or 'api_key' not in data or not data['api_key']:
            return jsonify({
                'status': 'error',
                'message': 'API key is required'
            })
        
        # Get the configuration
        llm_type = data.get('llm_type', 'claude')
        api_key = data.get('api_key', '')
        model = data.get('model', 'claude-3-5-haiku-latest')
        
        try:
            # Import the appropriate LLM client based on type
            if llm_type.lower() == 'claude':
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)
                    
                    # Send a simple test message
                    response = client.messages.create(
                        model=model,
                        max_tokens=100,
                        messages=[
                            {"role": "user", "content": "Who are you? Please keep your answer very brief."}
                        ]
                    )
                    
                    # Extract the response text
                    if response and hasattr(response, 'content') and len(response.content) > 0:
                        model_response = response.content[0].text
                    else:
                        model_response = "No response content"
                    
                    return jsonify({
                        'status': 'success',
                        'message': 'Successfully connected to Claude API',
                        'model_response': model_response
                    })
                    
                except Exception as e:
                    return jsonify({
                        'status': 'error',
                        'message': f'Error connecting to Claude API: {str(e)}'
                    })
                    
            elif llm_type.lower() == 'openai':
                try:
                    import openai
                    client = openai.OpenAI(api_key=api_key)
                    
                    # Send a simple test message
                    response = client.chat.completions.create(
                        model=model,
                        max_tokens=100,
                        messages=[
                            {"role": "user", "content": "Who are you? Please keep your answer very brief."}
                        ]
                    )
                    
                    # Extract the response text
                    if response and hasattr(response, 'choices') and len(response.choices) > 0:
                        model_response = response.choices[0].message.content
                    else:
                        model_response = "No response content"
                    
                    return jsonify({
                        'status': 'success',
                        'message': 'Successfully connected to OpenAI API',
                        'model_response': model_response
                    })
                    
                except Exception as e:
                    return jsonify({
                        'status': 'error',
                        'message': f'Error connecting to OpenAI API: {str(e)}'
                    })
            
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Unsupported LLM type: {llm_type}'
                })
                
        except ImportError as e:
            return jsonify({
                'status': 'error',
                'message': f'Missing required dependency: {str(e)}'
            })
    
    @app.route('/api/start', methods=['POST'])
    def start_generation():
        """Start the docstring generation process."""
        if app.config['APP_STATE']['is_running']:
            return jsonify({'status': 'error', 'message': 'Generation already in progress'})
        
        data = request.json
        
        # Validate repo path
        repo_path = data['repo_path']
        if not os.path.exists(repo_path):
            return jsonify({'status': 'error', 'message': f'Repository path not found: {repo_path}'})
        
        # Save configuration
        try:
            config_path = config_handler.save_config(data['config'])
        except ValueError as e:
            return jsonify({'status': 'error', 'message': str(e)})
        
        # Store in application state
        app.config['APP_STATE']['config'] = data['config']
        app.config['APP_STATE']['repo_path'] = repo_path
        app.config['APP_STATE']['is_running'] = True
        
        # Start the generation process
        thread = socketio.start_background_task(
            process_handler.start_generation_process,
            socketio, repo_path, config_path
        )
        
        app.config['APP_STATE']['process'] = thread
        
        return jsonify({'status': 'success', 'message': 'Generation started'})
    
    @app.route('/api/stop', methods=['POST'])
    def stop_generation():
        """Stop the docstring generation process."""
        if not app.config['APP_STATE']['is_running']:
            return jsonify({'status': 'error', 'message': 'No generation in progress'})
        
        process_handler.stop_generation_process()
        app.config['APP_STATE']['is_running'] = False
        
        return jsonify({'status': 'success', 'message': 'Generation stopped'})
    
    @app.route('/api/status')
    def get_status():
        """Get the current status of the generation process."""
        return jsonify({
            'is_running': app.config['APP_STATE']['is_running'],
            'repo_path': app.config['APP_STATE']['repo_path']
        })
    
    @app.route('/api/completeness')
    def get_completeness():
        """Get the current completeness evaluation of the repository."""
        if not app.config['APP_STATE']['repo_path']:
            return jsonify({'status': 'error', 'message': 'No repository selected'})
        
        results = visualization_handler.get_completeness_data(app.config['APP_STATE']['repo_path'])
        return jsonify(results)
    
    # Socket.IO event handlers
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection to Socket.IO."""
        if app.config['APP_STATE']['is_running']:
            # Send current state to newly connected client
            socketio.emit('status_update', visualization_handler.get_current_status())
    
    # Additional routes and event handlers can be added here
    
    return app, socketio 