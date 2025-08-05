#!/usr/bin/env python3
"""
Simple documentation server for hosting documentation folders.

This server serves documentation folders with the following structure:
- overview.md: The main overview document
- module_tree.json: Hierarchical structure of modules
- Various .md files for different modules

Usage:
    python docs_server.py --docs-folder path/to/docs --port 8080
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, render_template_string, request, send_from_directory, abort
from markdown_it import MarkdownIt

app = Flask(__name__)

# Global variables to store configuration
DOCS_FOLDER = None
MODULE_TREE = None

# Markdown parser
md = MarkdownIt()

# HTML template for the documentation pages
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11.9.0/dist/mermaid.min.js"></script>
    <style>
        :root {
            --primary-color: #2563eb;
            --secondary-color: #f1f5f9;
            --text-color: #334155;
            --border-color: #e2e8f0;
            --hover-color: #f8fafc;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: #ffffff;
        }
        
        .container {
            display: flex;
            min-height: 100vh;
        }
        
        .sidebar {
            width: 300px;
            background-color: var(--secondary-color);
            border-right: 1px solid var(--border-color);
            padding: 20px;
            overflow-y: auto;
            position: fixed;
            height: 100vh;
        }
        
        .content {
            flex: 1;
            margin-left: 300px;
            padding: 40px 60px;
            max-width: calc(100% - 300px);
        }
        
        .logo {
            font-size: 24px;
            font-weight: bold;
            color: var(--primary-color);
            margin-bottom: 30px;
            text-decoration: none;
        }
        
        .nav-section {
            margin-bottom: 25px;
        }
        
        .nav-section h3 {
            font-size: 14px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 10px;
        }
        
        .nav-item {
            display: block;
            padding: 8px 12px;
            color: var(--text-color);
            text-decoration: none;
            border-radius: 6px;
            font-size: 14px;
            transition: all 0.2s ease;
            margin-bottom: 2px;
        }
        
        .nav-item:hover {
            background-color: var(--hover-color);
            color: var(--primary-color);
        }
        
        .nav-item.active {
            background-color: var(--primary-color);
            color: white;
        }
        
        .nav-subsection {
            margin-left: 15px;
            margin-top: 8px;
        }
        
        .nav-subsection .nav-item {
            font-size: 13px;
            color: #64748b;
        }
        
        .markdown-content {
            max-width: none;
        }
        
        .markdown-content h1 {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 1rem;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }
        
        .markdown-content h2 {
            font-size: 2rem;
            font-weight: 600;
            color: #334155;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        
        .markdown-content h3 {
            font-size: 1.5rem;
            font-weight: 600;
            color: #475569;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
        }
        
        .markdown-content p {
            margin-bottom: 1rem;
            color: #475569;
        }
        
        .markdown-content ul, .markdown-content ol {
            margin-bottom: 1rem;
            padding-left: 1.5rem;
        }
        
        .markdown-content li {
            margin-bottom: 0.5rem;
            color: #475569;
        }
        
        .markdown-content code {
            background-color: #f1f5f9;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.875rem;
        }
        
        .markdown-content pre {
            background-color: #f8fafc;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 1rem;
            overflow-x: auto;
            margin-bottom: 1rem;
        }
        
        .markdown-content pre code {
            background-color: transparent;
            padding: 0;
        }
        
        .markdown-content blockquote {
            border-left: 4px solid var(--primary-color);
            padding-left: 1rem;
            margin-bottom: 1rem;
            font-style: italic;
            color: #64748b;
        }
        
        .markdown-content table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1rem;
        }
        
        .markdown-content th, .markdown-content td {
            border: 1px solid var(--border-color);
            padding: 0.75rem;
            text-align: left;
        }
        
        .markdown-content th {
            background-color: var(--secondary-color);
            font-weight: 600;
        }
        
        .markdown-content a {
            color: var(--primary-color);
            text-decoration: underline;
        }
        
        .markdown-content a:hover {
            text-decoration: none;
        }
        
        @media (max-width: 768px) {
            .sidebar {
                width: 100%;
                position: relative;
                height: auto;
            }
            
            .content {
                margin-left: 0;
                padding: 20px;
                max-width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <nav class="sidebar">
            <a href="/" class="logo">📚 Documentation</a>
            
            {% if navigation %}
            {% for section_key, section_data in navigation.items() %}
            <div class="nav-section">
                <h3>{{ section_key.replace('_', ' ').title() }}</h3>
                
                {% if section_data.components %}
                <a href="/{{ section_key }}.md" class="nav-item {% if current_page == section_key + '.md' %}active{% endif %}">
                    Overview
                </a>
                {% endif %}
                
                {% if section_data.children %}
                {% for child_key, child_data in section_data.children.items() %}
                <div class="nav-subsection">
                    <a href="/{{ child_key }}.md" class="nav-item {% if current_page == child_key + '.md' %}active{% endif %}">
                        {{ child_key.replace('_', ' ').title() }}
                    </a>
                </div>
                {% endfor %}
                {% endif %}
            </div>
            {% endfor %}
            {% endif %}
        </nav>
        
        <main class="content">
            <div class="markdown-content">
                {{ content | safe }}
            </div>
        </main>
    </div>
    
    <script>
        // Initialize mermaid with configuration
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            themeVariables: {
                primaryColor: '#2563eb',
                primaryTextColor: '#334155',
                primaryBorderColor: '#e2e8f0',
                lineColor: '#64748b',
                sectionBkgColor: '#f8fafc',
                altSectionBkgColor: '#f1f5f9',
                gridColor: '#e2e8f0',
                secondaryColor: '#f1f5f9',
                tertiaryColor: '#f8fafc'
            },
            flowchart: {
                htmlLabels: true,
                curve: 'basis'
            },
            sequence: {
                diagramMarginX: 50,
                diagramMarginY: 10,
                actorMargin: 50,
                width: 150,
                height: 65,
                boxMargin: 10,
                boxTextMargin: 5,
                noteMargin: 10,
                messageMargin: 35,
                mirrorActors: true,
                bottomMarginAdj: 1,
                useMaxWidth: true,
                rightAngles: false,
                showSequenceNumbers: false
            }
        });
        
        // Re-render mermaid diagrams after page load
        document.addEventListener('DOMContentLoaded', function() {
            mermaid.init(undefined, document.querySelectorAll('.mermaid'));
        });
    </script>
</body>
</html>
"""


def load_module_tree(docs_folder: Path) -> Optional[Dict]:
    """Load the module tree structure from module_tree.json."""
    tree_file = docs_folder / "module_tree.json"
    if not tree_file.exists():
        print(f"Warning: module_tree.json not found in {docs_folder}")
        return None
    
    try:
        with open(tree_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading module_tree.json: {e}")
        return None


def markdown_to_html(content: str) -> str:
    """Convert markdown content to HTML, with special handling for mermaid diagrams."""
    # First, convert markdown to HTML
    html = md.render(content)
    
    # Post-process to ensure mermaid code blocks are properly formatted
    # Look for code blocks with language-mermaid class and convert them to mermaid divs
    import re
    
    # Pattern to match mermaid code blocks
    pattern = r'<pre><code class="language-mermaid">(.*?)</code></pre>'
    
    def replace_mermaid(match):
        mermaid_code = match.group(1)
        # Decode HTML entities that might have been encoded
        import html
        mermaid_code = html.unescape(mermaid_code)
        return f'<div class="mermaid">{mermaid_code}</div>'
    
    # Replace mermaid code blocks with proper mermaid divs
    html = re.sub(pattern, replace_mermaid, html, flags=re.DOTALL)
    
    return html


def get_file_title(file_path: Path) -> str:
    """Extract title from markdown file, fallback to filename."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('# '):
                return first_line[2:].strip()
    except Exception:
        pass
    
    # Fallback to filename without extension
    return file_path.stem.replace('_', ' ').title()


@app.route('/')
def index():
    """Serve the overview page as the main page."""
    overview_file = Path(DOCS_FOLDER) / "overview.md"
    
    if not overview_file.exists():
        abort(404, "overview.md not found in the documentation folder")
    
    try:
        with open(overview_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        html_content = markdown_to_html(content)
        title = get_file_title(overview_file)
        
        return render_template_string(
            HTML_TEMPLATE,
            title=title,
            content=html_content,
            navigation=MODULE_TREE,
            current_page="overview.md"
        )
    except Exception as e:
        abort(500, f"Error reading overview.md: {e}")


@app.route('/<path:filename>')
def serve_doc(filename):
    """Serve individual documentation files."""
    # Security check: ensure we're only serving .md files and they exist in the docs folder
    if not filename.endswith('.md'):
        abort(404, "Only markdown files are supported")
    
    file_path = Path(DOCS_FOLDER) / filename
    
    # Ensure the file is within the docs folder (prevent directory traversal)
    try:
        file_path = file_path.resolve()
        docs_folder_resolved = Path(DOCS_FOLDER).resolve()
        if not str(file_path).startswith(str(docs_folder_resolved)):
            abort(403, "Access denied")
    except Exception:
        abort(403, "Invalid file path")
    
    if not file_path.exists():
        abort(404, f"File {filename} not found")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        html_content = markdown_to_html(content)
        title = get_file_title(file_path)
        
        return render_template_string(
            HTML_TEMPLATE,
            title=title,
            content=html_content,
            navigation=MODULE_TREE,
            current_page=filename
        )
    except Exception as e:
        abort(500, f"Error reading {filename}: {e}")


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from the docs folder (images, etc.)."""
    return send_from_directory(DOCS_FOLDER, filename)


def main():
    """Main function to run the documentation server."""
    parser = argparse.ArgumentParser(
        description="Simple documentation server for hosting markdown documentation folders"
    )
    parser.add_argument(
        "--docs-folder",
        type=str,
        required=True,
        help="Path to the documentation folder containing markdown files and module_tree.json"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run the server in debug mode"
    )
    
    args = parser.parse_args()
    
    # Validate docs folder
    docs_folder = Path(args.docs_folder)
    if not docs_folder.exists():
        print(f"Error: Documentation folder '{docs_folder}' does not exist")
        sys.exit(1)
    
    if not docs_folder.is_dir():
        print(f"Error: '{docs_folder}' is not a directory")
        sys.exit(1)
    
    # Check for overview.md
    overview_file = docs_folder / "overview.md"
    if not overview_file.exists():
        print(f"Warning: overview.md not found in '{docs_folder}'")
    
    # Set global variables
    global DOCS_FOLDER, MODULE_TREE
    DOCS_FOLDER = str(docs_folder.resolve())
    MODULE_TREE = load_module_tree(docs_folder)
    
    print(f"📚 Starting documentation server...")
    print(f"📁 Documentation folder: {DOCS_FOLDER}")
    print(f"🌐 Server running at: http://{args.host}:{args.port}")
    print(f"📖 Main page: overview.md")
    
    if MODULE_TREE:
        modules_count = len(MODULE_TREE)
        print(f"🗂️  Found {modules_count} main modules in module_tree.json")
    
    print("\nPress Ctrl+C to stop the server")
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")


if __name__ == "__main__":
    main()