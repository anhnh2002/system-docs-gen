# Copyright (c) Meta Platforms, Inc. and affiliates
"""
Web bridge for the docstring generation visualizers.

This module provides adapters that connect the existing terminal-based
visualizers to the web interface. When enabled, the visualizers will send
updates to the web interface in addition to their normal terminal output.
"""

import threading
import time
import functools
from typing import Dict, Any, Optional

# Singleton pattern for the web socket manager
class WebSocketManager:
    """Manages the connection to the web socket for sending visualization updates."""
    
    _instance = None
    _socket = None
    _enabled = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def set_socket(cls, socket):
        """Set the socket.io instance for sending updates."""
        cls._socket = socket
        cls._enabled = True
    
    @classmethod
    def is_enabled(cls):
        """Check if web visualization is enabled."""
        return cls._enabled and cls._socket is not None
    
    @classmethod
    def emit(cls, event, data):
        """Emit an event to the web interface."""
        if cls.is_enabled():
            try:
                cls._socket.emit(event, data)
            except Exception as e:
                print(f"Error sending web update: {e}")
                
    @classmethod
    def disable(cls):
        """Disable web visualization."""
        cls._enabled = False


class WebStatusAdapter:
    """Adapter for the StatusVisualizer to send updates to the web interface."""
    
    def __init__(self, original_visualizer):
        """
        Initialize the web status adapter.
        
        Args:
            original_visualizer: The original StatusVisualizer instance
        """
        self.original = original_visualizer
        self.socket_manager = WebSocketManager()
        
        # Store original methods to avoid recursion
        self._original_set_active_agent = original_visualizer.set_active_agent
        self._original_set_status_message = original_visualizer.set_status_message
        self._original_set_current_component = original_visualizer.set_current_component
    
    def set_active_agent(self, agent_name):
        """
        Set the active agent and send update to web interface.
        
        Args:
            agent_name: Name of the active agent
        """
        # Call the original method directly
        result = self._original_set_active_agent(agent_name)
        
        # Send update to web interface
        if self.socket_manager.is_enabled():
            self.socket_manager.emit('status_update', {
                'status': {
                    'active_agent': agent_name,
                    'status_message': self.original._status_message,
                    'current_component': self.original._current_component,
                    'current_file': self.original._current_file
                }
            })
        
        return result
    
    def set_status_message(self, message):
        """
        Set the status message and send update to web interface.
        
        Args:
            message: The status message
        """
        # Call the original method directly
        result = self._original_set_status_message(message)
        
        # Send update to web interface
        if self.socket_manager.is_enabled():
            self.socket_manager.emit('status_update', {
                'status': {
                    'active_agent': self.original.active_agent,
                    'status_message': message,
                    'current_component': self.original._current_component,
                    'current_file': self.original._current_file
                }
            })
        
        return result
    
    def set_current_component(self, focal_component, file_path):
        """
        Set the current component being processed and send update to web interface.
        
        Args:
            focal_component: The component being processed
            file_path: The path to the file containing the component
        """
        # Call the original method directly
        result = self._original_set_current_component(focal_component, file_path)
        
        # Send update to web interface
        if self.socket_manager.is_enabled():
            self.socket_manager.emit('status_update', {
                'status': {
                    'active_agent': self.original.active_agent,
                    'status_message': self.original._status_message,
                    'current_component': focal_component,
                    'current_file': file_path
                }
            })
            
            # Special message format for the web interface to parse
            print(f"COMPONENT: {focal_component} in file {file_path}")
        
        return result


class WebProgressAdapter:
    """Adapter for the ProgressVisualizer to send updates to the web interface."""
    
    def __init__(self, original_visualizer):
        """
        Initialize the web progress adapter.
        
        Args:
            original_visualizer: The original ProgressVisualizer instance
        """
        self.original = original_visualizer
        self.socket_manager = WebSocketManager()
        
        # Store original methods to avoid recursion
        self._original_update = original_visualizer.update
        if hasattr(original_visualizer, 'mark_complete'):
            self._original_mark_complete = original_visualizer.mark_complete
    
    def update(self, component_id=None, status="processing"):
        """
        Update the progress visualization and send update to web interface.
        
        Args:
            component_id: ID of the component being processed
            status: Status of the component
        """
        # Call the original method directly
        result = self._original_update(component_id, status)
        
        # Send update to web interface
        if self.socket_manager.is_enabled():
            # Get the component status from the original visualizer
            component_status = {}
            for comp_id in self.original.components:
                if comp_id in self.original.processed:
                    component_status[comp_id] = "complete"
                elif comp_id == self.original.current:
                    component_status[comp_id] = "in_progress"
                else:
                    component_status[comp_id] = "not_started"
            
            self.socket_manager.emit('status_update', {
                'progress': {
                    'total_components': len(self.original.sorted_order),
                    'processed_components': len(self.original.processed),
                    'current_component': self.original.current,
                    'component_status': component_status
                }
            })
            
            # Special message format for the web interface to parse
            print(f"PROGRESS: {len(self.original.processed)}/{len(self.original.sorted_order)} components processed")
        
        return result
    
    def mark_complete(self, component_id):
        """
        Mark a component as complete and send update to web interface.
        
        Args:
            component_id: ID of the component to mark as complete
        """
        # Check if the original visualizer has mark_complete
        if not hasattr(self, '_original_mark_complete'):
            # Fall back to update
            return self.update(component_id, "complete")
            
        # Call the original method directly
        result = self._original_mark_complete(component_id)
        
        # Update web interface
        if self.socket_manager.is_enabled():
            # Use the update method to send progress
            self.update(component_id, "complete")
        
        return result


def patch_visualizers():
    """
    Patch the existing visualizer classes to add web interface support.
    
    This function should be called before creating any visualizer instances
    to ensure they have web support.
    """
    from . import StatusVisualizer, ProgressVisualizer
    
    # Check if already patched to avoid double patching
    if hasattr(StatusVisualizer, '_web_patched'):
        return
    
    # Mark as patched
    StatusVisualizer._web_patched = True
    ProgressVisualizer._web_patched = True
    
    # Store the original __init__ methods
    original_status_init = StatusVisualizer.__init__
    original_progress_init = ProgressVisualizer.__init__
    
    # Create patched __init__ methods
    def patched_status_init(self, *args, **kwargs):
        original_status_init(self, *args, **kwargs)
        # Create adapter and store original methods
        adapter = WebStatusAdapter(self)
        # Replace methods with adapter methods
        self.set_active_agent = adapter.set_active_agent
        self.set_status_message = adapter.set_status_message
        self.set_current_component = adapter.set_current_component
    
    def patched_progress_init(self, *args, **kwargs):
        original_progress_init(self, *args, **kwargs)
        # Create adapter and store original methods
        adapter = WebProgressAdapter(self)
        # Replace methods with adapter methods
        self.update = adapter.update
        if hasattr(self, 'mark_complete'):
            self.mark_complete = adapter.mark_complete
    
    # Apply the patches
    StatusVisualizer.__init__ = patched_status_init
    ProgressVisualizer.__init__ = patched_progress_init 