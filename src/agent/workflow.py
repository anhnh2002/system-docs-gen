# Copyright (c) Meta Platforms, Inc. and affiliates
from typing import Optional
from pathlib import Path
from .orchestrator import Orchestrator
from .reader import CodeComponentType

def generate_docstring(
    repo_path: str,
    file_path: str,
    focal_component: str,
    component_type: CodeComponentType,
    instruction: Optional[str] = None
) -> str:
    """Generate a high-quality docstring for a code component using the multi-agent system.
    
    Args:
        repo_path: Path to the repository containing the code
        file_path: Path to the file containing the component
        focal_component: The code component needing a docstring
        component_type: The type of the code component (function, method, or class)
        instruction: Optional specific instructions for docstring generation
        
    Returns:
        The generated and verified docstring
        
    Raises:
        FileNotFoundError: If the repository or file path doesn't exist
        ValueError: If the component type is invalid
    """
    # Validate inputs
    repo_path = str(Path(repo_path).resolve())
    file_path = str(Path(file_path).resolve())
    
    if not Path(repo_path).exists():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File path does not exist: {file_path}")
    
    # Use default instruction if none provided
    if instruction is None:
        instruction = """Generate a comprehensive and helpful docstring that includes:
        1. A clear description of what the component does
        2. All parameters and their types
        3. Return value and type
        4. Any exceptions that may be raised
        5. Usage examples where appropriate
        The docstring should follow PEP 257 style guidelines."""
    
    # Create orchestrator and generate docstring
    orchestrator = Orchestrator(repo_path)
    return orchestrator.process(
        instruction=instruction,
        focal_component=focal_component,
        component_type=component_type,
        file_path=file_path
    ) 