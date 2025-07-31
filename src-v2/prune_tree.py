from typing import List, Dict, Tuple
from collections import defaultdict
import logging
import json
import os

from dependency_analyzer.ast_parser import CodeComponent
from llm_services import call_llm

logger = logging.getLogger(__name__)


PROMPT = """
You are a developer who is responsible for maintaining the codebase of a software project.
You must do following task in order to onboard a new developer to the project, the goal is to help him understand the core system of the project.

Given an implementation of a code component in the project:
<implementation>
{code}
</implementation>

Based on statically analyzing the code, I found that this code component depends on the following other code components (static analysis may be insufficient):
<dependencies>
{dependencies}
</dependencies>

Please CHERRY-PICK the critical dependencies which are necessary to understand the main functionality of this code component.
Firstly reasoning about the dependencies, then return the list of critical dependencies in the following format:
<critical_dependencies>
<given>
{{critical_dependencies_already_given_in_the_dependencies_section}} (separated by \n)
</given>
<additional>
{{critical_dependencies_not_given_in_the_dependencies_section}} (separated by \n)
</additional>
</critical_dependencies>
""".strip()

def parse_critical_dependencies(response: str) -> Tuple[List[str], List[str]]:
    """
    Parse the response from the LLM to get the critical dependencies.
    """
    # extract the <critical_dependencies> section
    critical_dependencies = response.split("<critical_dependencies>")[1].split("</critical_dependencies>")[0]
    # extract the <given> section
    given = critical_dependencies.split("<given>")[1].split("</given>")[0].strip()
    # extract the <additional> section
    additional = critical_dependencies.split("<additional>")[1].split("</additional>")[0].strip()
    return given.split("\n"), additional.split("\n")


def prune_tree(leaf_nodes: List[str], components: Dict[str, CodeComponent], pruned_file_path: str):

    cache = {}

    # if pruned_file_path exists, load the cache from it
    if os.path.exists(pruned_file_path):
        with open(pruned_file_path, "r") as f:
            cache = json.load(f)["cache"]
    
    def prune_component(component: CodeComponent):

        if len(component.depends_on) == 0:
            return
        
        dependencies = []

        # cache hit
        if component.id in cache:
            logger.info(f"Cache hit for {component.id}")
            dependencies = cache[component.id]
        
        else:
            logger.info(f"Cache miss for {component.id}")

            code = component.source_code
            dependencies = [dep for dep in component.depends_on if components[dep].source_code not in code]
            prompt = PROMPT.format(code=code, dependencies="\n".join(dependencies))

            try:
                # logger.info(f"-------------PROMPT-------------:\n{prompt}\n-------------END PROMPT-------------")

                response = call_llm(prompt)

                # logger.info(f"-------------RESPONSE-------------:\n{response}\n-------------END RESPONSE-------------")

                given, additional = parse_critical_dependencies(response)

                additional = [dep for dep in additional if dep in components]

                dependencies = given# + additional

                # logger.info(f"-------------GIVEN-------------:\n{given}\n-------------END GIVEN-------------")
                # logger.info(f"-------------ADDITIONAL-------------:\n{additional}\n-------------END ADDITIONAL-------------")
            except Exception as e:
                logger.error(f"Error parsing critical dependencies: {e}\nFallback to using original dependencies")
            
            cache[component.id] = dependencies
        
        # recursively prune the dependencies
        for dep in dependencies:
            if dep in components:
                prune_component(components[dep])
    
    for leaf_node in leaf_nodes:
        prune_component(components[leaf_node])

    # save the pruned tree to a file
    pruned_tree = {
        "leaf_nodes": leaf_nodes,
        "cache": cache
    }

    with open(pruned_file_path, "w") as f:
        json.dump(pruned_tree, f, indent=4)


