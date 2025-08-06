from dependency_analyzer import CodeComponent
import re
import mermaid as md
from pathlib import Path
from typing import List, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_complex_module(components: dict[str, CodeComponent], core_component_ids: list[str]) -> bool:
    files = set()
    for component_id in core_component_ids:
        if component_id in components:
            files.add(components[component_id].file_path)

    result = len(files) > 1

    return result


def validate_mermaid_diagrams(md_file_path: str, relative_path: str) -> str:
    """
    Validate all Mermaid diagrams in a markdown file.
    
    Args:
        md_file_path: Path to the markdown file to check
        relative_path: Relative path to the markdown file
    Returns:
        "All mermaid diagrams are syntax correct" if all diagrams are valid,
        otherwise returns error message with details about invalid diagrams
    """

    try:
        # Read the markdown file
        file_path = Path(md_file_path)
        if not file_path.exists():
            return f"Error: File '{md_file_path}' does not exist"
        
        content = file_path.read_text(encoding='utf-8')
        
        # Extract all mermaid code blocks
        mermaid_blocks = extract_mermaid_blocks(content)
        
        if not mermaid_blocks:
            return "No mermaid diagrams found in the file"
        
        # Validate each mermaid diagram in parallel
        errors = []
        with ThreadPoolExecutor(max_workers=min(len(mermaid_blocks), 10)) as executor:
            # Submit all validation tasks
            future_to_info = {}
            for i, (line_start, diagram_content) in enumerate(mermaid_blocks, 1):
                future = executor.submit(validate_single_diagram, diagram_content, i, line_start)
                future_to_info[future] = i
            
            # Collect results as they complete
            for future in as_completed(future_to_info):
                error_msg = future.result()
                if error_msg:
                    errors.append("\n")
                    errors.append(error_msg)
        
        if errors:
            logger.info(f"Mermaid syntax errors found in file: {md_file_path}: {errors}")
        
        if errors:
            return "Mermaid syntax errors found in file: " + relative_path + "\n" + "\n".join(errors)
        else:
            return "All mermaid diagrams in file: " + relative_path + " are syntax correct"
            
    except Exception as e:
        return f"Error processing file: {str(e)}"


def extract_mermaid_blocks(content: str) -> List[Tuple[int, str]]:
    """
    Extract all mermaid code blocks from markdown content.
    
    Returns:
        List of tuples containing (line_number, diagram_content)
    """
    mermaid_blocks = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for mermaid code block start
        if line == '```mermaid' or line.startswith('```mermaid'):
            start_line = i + 1
            diagram_lines = []
            i += 1
            
            # Collect lines until we find the closing ```
            while i < len(lines):
                if lines[i].strip() == '```':
                    break
                diagram_lines.append(lines[i])
                i += 1
            
            if diagram_lines:  # Only add non-empty diagrams
                diagram_content = '\n'.join(diagram_lines)
                mermaid_blocks.append((start_line, diagram_content))
        
        i += 1
    
    return mermaid_blocks


def validate_single_diagram(diagram_content: str, diagram_num: int, line_start: int) -> str:
    """
    Validate a single mermaid diagram.
    
    Args:
        diagram_content: The mermaid diagram content
        diagram_num: Diagram number for error reporting
        line_start: Starting line number in the file
        
    Returns:
        Error message if invalid, empty string if valid
    """
    try:
        # Create Mermaid object and check response
        render = md.Mermaid(diagram_content)
        response_text = render.svg_response.text
        
        # Check if response indicates a parse error
        if response_text.startswith("Parse error"):
            # Extract line number from parse error and calculate actual line in markdown file
            line_match = re.search(r'line (\d+):', response_text)
            if line_match:
                error_line_in_diagram = int(line_match.group(1))
                actual_line_in_file = line_start + error_line_in_diagram
                return f"Diagram {diagram_num}: Parse error on line {actual_line_in_file}:\n{'\n'.join(response_text.split('\n')[1:])}"
            else:
                return f"Diagram {diagram_num}: {response_text}"
        
        return ""  # No error
        
    except Exception as e:
        return f"  Diagram {diagram_num}: Exception during validation - {str(e)}"


if __name__ == "__main__":
    # Test with the provided file
    test_file = "output/docs/SWE_agent-docs/agent_hooks.md"
    result = validate_mermaid_diagrams(test_file, "agent_hooks.md")
    print(result)