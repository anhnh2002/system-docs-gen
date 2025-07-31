# Copyright (c) Meta Platforms, Inc. and affiliates
"""
Configuration handler for the docstring generation web interface.

This module handles reading, writing, and validating the configuration for
the docstring generation process.
"""

import os
import yaml
import json
import tempfile
from pathlib import Path

def get_default_config():
    """
    Get the default configuration from agent_config.yaml.
    
    Returns:
        Dictionary containing the default configuration
    """
    default_config_path = Path('config/agent_config.yaml')
    
    if not default_config_path.exists():
        return {
            'llm': {
                'type': 'claude',
                'api_key': '',
                'model': 'claude-3-5-haiku-latest',
                'temperature': 0.1,
                'max_tokens': 4096
            },
            'flow_control': {
                'max_reader_search_attempts': 2,
                'max_verifier_rejections': 1,
                'status_sleep_time': 1
            },
            'docstring_options': {
                'overwrite_docstrings': False
            }
        }
    
    with open(default_config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config

def validate_config(config):
    """
    Validate that the configuration has the required fields.
    
    Args:
        config: Dictionary containing the configuration to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_keys = ['llm', 'flow_control', 'docstring_options']
    
    for key in required_keys:
        if key not in config:
            return False, f"Missing required configuration section: {key}"
    
    # Check specific required fields in llm section
    llm_required = ['type', 'api_key', 'model']
    for key in llm_required:
        if key not in config['llm']:
            return False, f"Missing required field in llm section: {key}"
    
    return True, ""

def save_config(config):
    """
    Save the configuration to a temporary file for use by the generation process.
    
    Args:
        config: Dictionary containing the configuration to save
        
    Returns:
        Path to the saved configuration file
    """
    # Validate configuration
    is_valid, error_message = validate_config(config)
    if not is_valid:
        raise ValueError(f"Invalid configuration: {error_message}")
    
    # Create a temporary file
    temp_dir = tempfile.gettempdir()
    config_file = os.path.join(temp_dir, 'docstring_generator_config.yaml')
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return config_file 