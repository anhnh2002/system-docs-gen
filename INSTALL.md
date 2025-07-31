# Installation Guide

This guide details how to set up the environment for DocAgent.

## Option 1: Installation with pip (Recommended)

### Basic Installation
To install the basic package with core dependencies:

```bash
# For all dependencies
pip install -e ".[all]"
```



## Development Setup

For development, we recommend installing in editable mode with dev dependencies:

```bash
# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Troubleshooting

### GraphViz Dependencies

For visualization components, you may need to install system-level dependencies for GraphViz:

```bash
# Ubuntu/Debian
sudo apt-get install graphviz graphviz-dev

# CentOS/RHEL
sudo yum install graphviz graphviz-devel

# macOS
brew install graphviz
```

### CUDA Support

If you're using CUDA for accelerated processing, ensure you have the correct CUDA toolkit installed that matches your PyTorch version. 