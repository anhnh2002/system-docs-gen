# Copyright (c) Meta Platforms, Inc. and affiliates
"""
Web application for docstring generation visualization.

This module provides a web-based interface for configuring and visualizing
the progress of docstring generation in a Python codebase.
"""

from .app import create_app

__all__ = ['create_app'] 