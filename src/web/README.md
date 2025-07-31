# DocAgent Web Interface

A real-time web visualization system for the DocAgent docstring generation tool.

## Overview

The DocAgent Web Interface provides a modern, interactive web UI for generating and tracking Python docstring generation. The application visualizes the agent-based docstring generation process in real-time, allowing users to monitor progress, view code structure, track completeness metrics, and manage the configuration.

## Features

- **Configuration Management**: Easily configure all aspects of the docstring generation process (Repository Path, LLM settings, Flow Control, Docstring Options) through a user-friendly web form. Test LLM API connectivity before starting.
- **Real-time Visualization**: Observe the docstring generation process as it happens.
- **Agent Status Tracking**: View which agent (Reader, Searcher, Writer, Verifier) is currently active in the generation workflow via a visual graph.
- **Repository Structure Visualization**: Interactive tree visualization of your Python codebase, highlighting files as they are processed (White: unprocessed, Yellow: processing, Green: completed).
- **Dynamic Progress Tracking**: Real-time progress bars and component completion tracking.
- **Completeness Metrics Visualization**: Visual representation of docstring completeness across your codebase, updated as the generation progresses (visible in the left sidebar).
- **Log Viewer**: Consolidated view of the generation process logs.
- **Process Control**: Start and stop the generation process via UI buttons.

## Architecture

### Backend

The web application is built using:

- **Flask**: Web framework for the backend server
- **Socket.IO**: Real-time bidirectional communication between client and server
- **Eventlet**: Asynchronous networking library for handling concurrent connections

### Frontend

The frontend uses:

- **Bootstrap 5**: CSS framework for responsive design
- **D3.js**: Data visualization library for interactive repository and agent visualizations
- **Socket.IO Client**: Real-time communication with the backend
- **jQuery**: DOM manipulation and event handling

### Directory Structure

```
src/web/
├── app.py                 - Main Flask application
├── config_handler.py      - Handles configuration loading/saving
├── process_handler.py     - Manages the docstring generation process
├── visualization_handler.py - Handles visualization state management
├── static/                - Static assets
│   ├── css/               - CSS stylesheets
│   │   └── style.css      - Custom styling
│   └── js/                - JavaScript files
│       ├── completeness.js     - Completeness visualization
│       ├── config.js           - Configuration handling
│       ├── log-handler.js      - Log display handling
│       ├── main.js             - Main application logic
│       ├── repo-structure.js   - Repository structure visualization
│       └── status-visualizer.js - Agent status visualization
└── templates/             - HTML templates
    └── index.html         - Main application page
```

## Data Flow

1.  User configures settings via the web form.
2.  User clicks "Start Generation".
3.  Flask backend spawns a subprocess running the `generate_docstrings.py` script (expected in the project root).
4.  Process output (status updates, logs, metrics) is captured and parsed in real-time by the backend.
5.  Parsed events are emitted via Socket.IO to the frontend.
6.  Frontend components (Agent Status, Repo Structure, Logs, Progress, Completeness) update dynamically based on the received events.
7.  User receives real-time feedback on the generation process.
8.  User can stop the process using the "Stop Generation" button.



## Usage Guide

### 1. Starting the Web Interface

Run the web application from the project root directory:

```bash
python run_web_ui.py
```

By default, the web interface will be available at `http://127.0.0.1:5000`.

You can customize the host and port:

```bash
# Example: Run on port 8080, accessible externally
python run_web_ui.py --host 0.0.0.0 --port 8080
```

### 2. Configuration

The initial screen presents configuration options:

- **Repository Path**: Path to the Python codebase for docstring generation.
- **LLM Configuration**: Settings for the language model (Type, API Key, Model, Temperature, Max Tokens). Use the "Test API" button to verify credentials.
- **Flow Control**: Advanced settings for the generation process.
- **Docstring Options**: Control options like overwriting existing docstrings.

### 3. Starting the Generation Process

1.  Fill in the configuration form accurately.
2.  Click "Start Generation".
3.  The interface will switch to the monitoring/visualization view.

### 4. Monitoring the Generation Process

The visualization interface consists of several panels:

- **Agent Status Panel**: Shows the current active agent in the workflow graph.
- **Repository Structure Panel**: Displays the interactive codebase tree, highlighting the currently processed file.
- **Logs and Progress Panel**: Shows real-time logs and overall progress.
- **Completeness Panel (Sidebar)**: Shows statistics about docstring completeness.

### 5. Stopping the Process

Click the "Stop Generation" button in the header to terminate the process early.
