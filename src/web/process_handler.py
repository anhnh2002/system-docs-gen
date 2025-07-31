# Copyright (c) Meta Platforms, Inc. and affiliates
"""
Process handler for running the docstring generation.

This module handles starting, monitoring, and stopping the docstring generation
process, as well as capturing its output and sending it to the web interface.
"""

import os
import sys
import subprocess
import threading
import tempfile
import signal
import re
from pathlib import Path
from typing import Optional, Dict, Any

from . import visualization_handler

# Global variables to track the process
process = None
should_stop = False

# Custom output handler to intercept and parse the output
class OutputHandler(threading.Thread):
    """Thread to handle output from the docstring generation process."""
    
    def __init__(self, process, socketio):
        """
        Initialize the output handler.
        
        Args:
            process: The subprocess.Popen object for the docstring generation process
            socketio: The Flask-SocketIO instance for sending updates to clients
        """
        threading.Thread.__init__(self)
        self.process = process
        self.socketio = socketio
        self.daemon = True
    
    def run(self):
        """Read output from the process and update the visualization state."""
        global should_stop
        
        # Regular expressions for parsing different types of output
        status_regex = re.compile(r'STATUS: Agent: (\w+), Message: (.+)')
        component_regex = re.compile(r'COMPONENT: (.+) in file (.+)')
        progress_regex = re.compile(r'PROGRESS: (\d+)/(\d+) components processed')
        log_regex = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - (\w+) - (\w+) - (.+)')
        
        # Additional regex to detect agent activity from regular logs
        agent_activity_regex = re.compile(r'(reader|writer|searcher|verifier)', re.IGNORECASE)
        docstring_update_regex = re.compile(r'Successfully updated docstring for (.+)|Completed docstring generation for (.+)', re.IGNORECASE)
        
        # Patterns to filter out visualization-related output from logs
        visualization_patterns = [
            r'┌─+┐',     # Box top
            r'│.*│',     # Box content
            r'└─+┘',     # Box bottom
            r'Agent:',   # Agent status
            r'Status:',  # Status message
            r'Component:',  # Component info
            r'╔═+╗',     # Double-line box top
            r'║.*║',     # Double-line box content
            r'╚═+╝',     # Double-line box bottom
            r'▶ ',       # Progress indicators
            r'→ ',       # Arrow indicators
            r'⦿',        # Bullet indicators
            r'Processing component \d+/\d+',  # Progress messages
            r'╡.*╞',     # Table separators
            r'═+',       # Table lines
            r'DocAgent (?:Workflow )?Status',  # Workflow status header
            r'Processing: ',    # Processing status line
            r'File: ',          # File status line
            r'Active Agent: ',  # Agent status line
            r'Status: ',        # Status message line
            r'Workflow Input:',  # Input section
            r'Component Name:',  # Input component name
            r'File Path:',       # Input file path
            r'Dependencies:',    # Input dependencies
            r'Code:',            # Input code
            r'^Input:',          # Input header
            r'\[.*?\]',          # Status messages in brackets
        ]
        visualization_filter = re.compile('|'.join(visualization_patterns))
        
        # Read each line from the process output
        for line in iter(self.process.stdout.readline, b''):
            if should_stop:
                break
                
            # Decode the line
            try:
                line = line.decode('utf-8').rstrip()
            except UnicodeDecodeError:
                continue
            
            # Process workflow status lines separately to update agent status
            if 'Processing:' in line or 'File:' in line:
                if 'Processing:' in line:
                    component = line.split('Processing:')[1].strip()
                    if component:
                        visualization_handler.update_component_focus(component, "")
                if 'File:' in line:
                    file_path = line.split('File:')[1].strip()
                    if file_path:
                        # Update the current file without changing the component
                        current_status = visualization_handler.get_current_status()
                        if 'status' in current_status and current_status['status'].get('current_component'):
                            visualization_handler.update_component_focus(
                                current_status['status']['current_component'], 
                                file_path
                            )
                self.socketio.emit('status_update', visualization_handler.get_current_status())
            
            # Add to log messages - filter out visualization
            if not visualization_filter.search(line):
                visualization_handler.add_log_message(line)
                self.socketio.emit('log_line', line)
            
            # Check for status updates
            status_match = status_regex.search(line)
            if status_match:
                agent, message = status_match.groups()
                visualization_handler.update_agent_status(agent, message)
                self.socketio.emit('status_update', visualization_handler.get_current_status())
                continue
            
            # Check for agent activity in regular logs
            if not status_match:  # Only check if we didn't already match a status
                agent_match = agent_activity_regex.search(line)
                if agent_match and ('active' in line.lower() or 'using' in line.lower() or 'processing' in line.lower()):
                    # Extract agent name from logs
                    agent = agent_match.group(1).capitalize()
                    visualization_handler.update_agent_status(agent, "Processing")
                    self.socketio.emit('status_update', visualization_handler.get_current_status())
            
            # Check for component updates
            component_match = component_regex.search(line)
            if component_match:
                component, file_path = component_match.groups()
                visualization_handler.update_component_focus(component, file_path)
                visualization_handler.update_file_status(file_path, 'in_progress')
                self.socketio.emit('status_update', visualization_handler.get_current_status())
                continue
            
            # Check for progress updates
            progress_match = progress_regex.search(line)
            if progress_match:
                processed, total = progress_match.groups()
                # We don't have the current component or component status from this regex,
                # so we'll just update the counts
                visualization_handler.update_progress(int(total), int(processed), '', {})
                self.socketio.emit('status_update', visualization_handler.get_current_status())
                continue
            
            # Also check for progress updates in normal log lines
            progress_in_log = re.search(r'Processing component (\d+)/(\d+)', line)
            if progress_in_log:
                current, total = progress_in_log.groups()
                visualization_handler.update_progress(int(total), int(current), '', {})
                self.socketio.emit('status_update', visualization_handler.get_current_status())
            
            # Check for docstring updates
            docstring_update_match = docstring_update_regex.search(line)
            if docstring_update_match:
                component = docstring_update_match.group(1) or docstring_update_match.group(2)
                # If this is a file path, extract it
                if component and '/' in component:
                    file_path = component
                    visualization_handler.update_file_status(file_path, 'complete')
                    self.socketio.emit('status_update', visualization_handler.get_current_status())
                    # Emit a special event for docstring updates
                    self.socketio.emit('docstring_updated', {'component': component})
            
            # Try to extract component information from other log lines
            if 'Processing' in line and ':' in line and 'file' in line:
                parts = line.split('file')
                if len(parts) > 1:
                    file_path = parts[1].strip()
                    component = parts[0].split('Processing')[-1].strip()
                    if component and file_path:
                        visualization_handler.update_component_focus(component, file_path)
                        visualization_handler.update_file_status(file_path, 'in_progress')
                        self.socketio.emit('status_update', visualization_handler.get_current_status())
            
            # Check for log messages
            log_match = log_regex.search(line)
            if log_match:
                _, level, message = log_match.groups()
                # If the message indicates completion of a file, update the file status
                if 'Completed docstring generation for' in message or 'Successfully updated docstring for' in message:
                    # Try to extract the file path from the message
                    file_match = re.search(r'for file (.+)$|for (.+)', message)
                    if file_match:
                        file_path = file_match.group(1) or file_match.group(2)
                        if file_path and '.' in file_path:  # Simple check to ensure it looks like a filename
                            visualization_handler.update_file_status(file_path, 'complete')
                            self.socketio.emit('status_update', visualization_handler.get_current_status())
                            # Emit a special event for docstring updates
                            self.socketio.emit('docstring_updated', {'component': file_path})
                
                self.socketio.emit('log_message', {'level': level, 'message': message})

def start_generation_process(socketio, repo_path: str, config_path: str):
    """
    Start the docstring generation process.
    
    Args:
        socketio: The Flask-SocketIO instance for sending updates to clients
        repo_path: Path to the repository to generate docstrings for
        config_path: Path to the configuration file
    """
    global process, should_stop
    
    should_stop = False
    
    # Set an initial status to show we're starting
    visualization_handler.update_agent_status("System", "Starting docstring generation...")
    socketio.emit('status_update', visualization_handler.get_current_status())
    
    # Connect the socket to the web bridge
    try:
        from src.visualizer.web_bridge import WebSocketManager
        WebSocketManager.set_socket(socketio)
    except ImportError:
        socketio.emit('log_message', {
            'level': 'warning',
            'message': 'Web bridge not available. Some features may not work correctly.'
        })
    
    # Get the repository structure and update the visualization state
    try:
        structure = visualization_handler.get_repo_structure(repo_path)
        socketio.emit('status_update', visualization_handler.get_current_status())
        socketio.emit('log_message', {
            'level': 'info',
            'message': f'Repository structure loaded with {len(structure["children"])} top-level items'
        })
    except Exception as e:
        socketio.emit('log_message', {
            'level': 'error',
            'message': f'Error loading repository structure: {str(e)}'
        })
    
    # Find the generate_docstrings.py script
    script_path = Path(__file__).parent.parent.parent / 'generate_docstrings.py'
    
    if not script_path.exists():
        socketio.emit('error', {
            'message': f'Could not find docstring generation script at {script_path}'
        })
        return
    
    # Start the process
    try:
        # Create a temporary file for redirecting stdout and stderr
        process = subprocess.Popen(
            [sys.executable, str(script_path), 
             '--repo-path', repo_path, 
             '--config-path', config_path,
             '--enable-web'],  # Enable web integration
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=False
        )
        
        # Start the output handler
        handler = OutputHandler(process, socketio)
        handler.start()
        
        # Wait for the process to complete
        return_code = process.wait()
        
        if return_code == 0:
            socketio.emit('complete', {
                'message': 'Docstring generation completed successfully'
            })
        else:
            socketio.emit('error', {
                'message': f'Docstring generation failed with return code {return_code}'
            })
    
    except Exception as e:
        socketio.emit('error', {
            'message': f'Error starting docstring generation process: {str(e)}'
        })
    
    finally:
        process = None

def stop_generation_process():
    """
    Stop the docstring generation process.
    
    Returns:
        True if the process was stopped, False otherwise
    """
    global process, should_stop
    
    if process is None:
        return False
    
    should_stop = True
    
    try:
        # Disconnect from the web bridge
        try:
            from src.visualizer.web_bridge import WebSocketManager
            WebSocketManager.disable()
        except ImportError:
            pass
        
        # Try to terminate the process gracefully first
        process.terminate()
        
        # Wait for up to 5 seconds for the process to terminate
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # If the process didn't terminate, kill it
            process.kill()
        
        return True
    
    except Exception as e:
        print(f"Error stopping process: {e}")
        return False 