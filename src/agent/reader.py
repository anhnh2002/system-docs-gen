# Copyright (c) Meta Platforms, Inc. and affiliates
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseAgent


class CodeComponentType(Enum):
    """Enum for different types of code components."""

    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"


@dataclass
class InformationRequest:
    """Data class for structured information requests."""

    internal_requests: List[str]


class Reader(BaseAgent):
    """Agent responsible for determining if more context is needed for docstring generation."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the Reader agent.

        Args:
            config_path: Optional path to the configuration file
        """
        super().__init__("Reader", config_path)
        self.system_prompt = """You are a Reader agent responsible for determining if more context
        is needed to generate a high-quality docstring. You should analyze the code component and
        current context to make this determination.

        You have access to Internal Codebase Information (from local code repository):
            For Functions:
            - Code components called within the function body
            - Places where this function is called

            For Methods:
            - Code components called within the method body
            - Places where this method is called
            - The class this method belongs to

            For Classes:
            - Code components called in the __init__ method
            - Places where this class is instantiated
            - Complete class implementation beyond __init__


        Your response should:
        1. First provide a free text analysis of the current code and context
        2. Explain what additional information might be needed (if any)
        3. Include an <INFO_NEED>true</INFO_NEED> tag if more information is needed,
           or <INFO_NEED>false</INFO_NEED> if current context is sufficient
        4. If more information is needed, end your response with a structured request in XML format:

        <REQUEST>
            <INTERNAL>
                <CALLS>
                    <CLASS>class1,class2</CLASS>
                    <FUNCTION>func1,func2</FUNCTION>
                    <METHOD>self.method1,instance.method2,class.method3</METHOD>
                </CALLS>
                <CALL_BY>true/false</CALL_BY>
            </INTERNAL>
        </REQUEST>

        Important rules for structured request:
        1. For CALLS sections, only include names that are explicitly needed
        2. If no items exist for a category, use empty tags (e.g., <CLASS></CLASS>)
        3. CALL_BY should be "true" only if you need to know what calls/uses a component
        4. Use comma-separated values without spaces for multiple items
        5. For METHODS, keep dot notation in the same format as the input.
        6. Only first-level calls of the focal code component are accessible. Do not request information on code components that are not directly called by the focal component.


        Important rules:
        1. Only request internal codebase information that you think is necessary for docstring generation task. For some components that is simple and obvious, you do not need any other information for docstring generation.

        <Example_response>
        The current code shows a database connection function. To write a comprehensive docstring, we need to understand:
        1. Where this function is called - this will reveal the expected input patterns and common use cases
        2. What internal database functions it relies on - this will help document any dependencies or prerequisites

        This additional context is necessary because database connections often have specific setup requirements and usage patterns that should be documented for proper implementation.

        <INFO_NEED>true</INFO_NEED>

        <REQUEST>
            <INTERNAL>
                <CALLS>
                    <CLASS></CLASS>
                    <FUNCTION>execute_query,connect_db</FUNCTION>
                    <METHOD>self.process_data,data_processor._internal_process</METHOD>
                </CALLS>
                <CALL_BY>true</CALL_BY>
            </INTERNAL>
        </REQUEST>

        </Example_response>

        Keep in mind that:

        3. You do not need to generate docstring for the component. Just determine if more information is needed.
        """
        self.add_to_memory("system", self.system_prompt)

    def process(self, focal_component: str, context: str = "") -> str:
        """Process the input and determine if more context is needed.

        Args:
            instruction: The instruction for docstring generation
            focal_component: The code component needing a docstring (full code snippet)
            component_type: The type of the code component (function, method, or class)
            context: Current context information (if any)

        Returns:
            A string containing the analysis and <INFO_NEED> tag indicating if more information is needed
        """
        # Add the current task to memory
        task_description = f"""
        <context>
        Current context:
        {context if context else 'No context provided yet.'}
        </context>

        <component>
        Analyze the following code component:

        {focal_component}
        </component>
        """
        self.add_to_memory("user", task_description)

        # Generate response using LLM
        response = self.generate_response()
        return response
