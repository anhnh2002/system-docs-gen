# DocAgent - Docstring Evaluation System

A web application for evaluating the quality of Python docstrings in your codebase, providing objective metrics and actionable feedback.


## Overview

DocAgentis a powerful tool that analyzes Python docstrings in a repository and evaluates them based on two key metrics:

1. **Completeness**: Automatically checks if docstrings contain all required components (summary, description, arguments, returns, etc.)
2. **Helpfulness**: Uses LLM-based evaluation to assess how helpful and informative each docstring component is on a scale of 1-5

The system provides an intuitive web interface for configuring evaluation settings, viewing results, and getting actionable feedback to improve your codebase documentation.

## Features

- **Configuration Interface**: User-friendly setup for LLM API (OpenAI or Claude) and repository path
- **API Connection Testing**: Verify API credentials before running evaluations
- **Automated Completeness Evaluation**: Scan all Python files in a repository to check for required docstring components
- **Interactive Results Dashboard**: View completeness scores for all classes and functions with detailed breakdowns
- **On-demand Helpfulness Assessment**: Use LLM-powered evaluation for specific docstring components
- **Visual Status Indicators**: Clear visual feedback for required vs. optional components and their quality
- **Component-specific Evaluations**: Different criteria for evaluating summaries, descriptions, parameters, etc.
- **Refresh Functionality**: Re-run evaluation after making code changes
- **Detailed Explanations**: Get specific feedback on why a component received its score and how to improve it

## System Architecture

DocAgent's web evaluation system consists of several key components:

```
src/web_eval/
│
├── app.py                     # Main Flask application 
├── helpers.py                 # Utility functions (parsing, extraction, etc.)
├── requirements.txt           # Python dependencies
├── start_server.sh            # Convenience script for starting the server
├── test_docstring_parser.py   # Tests for the docstring parser
│
├── templates/                 # HTML templates
│   ├── index.html             # Configuration page
│   └── results.html           # Results display page
│
└── static/                    # Static assets
    ├── css/                   # CSS stylesheets
    ├── js/                    # JavaScript files
    └── assets/                # Images and other assets
```

The system follows a Model-View-Controller architecture:

- **Model**: Evaluation logic in the imported evaluator modules and parsing functions in helpers.py
- **View**: HTML templates with Jinja2 for rendering the UI
- **Controller**: Flask routes in app.py that handle requests and connect the model with views

The application integrates with two key external components:

1. **DocAgent Evaluator Modules**: Core evaluation logic for assessing docstring quality
2. **LLM APIs**: OpenAI or Anthropic Claude for helpfulness evaluation

