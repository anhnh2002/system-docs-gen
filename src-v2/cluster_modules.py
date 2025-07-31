from typing import List, Dict, Any
from collections import defaultdict

from dependency_analyzer.ast_parser import CodeComponent
from llm_services import call_llm

PROMPT = """
After statically analyzing the repository, here is list of all root components (there is no other components depend on them and it's normal that some root components are not essential to the repository):
<root_components>
{root_components}
</root_components>

Please group the components into groups such that each group is a set of components that are closely related to each other and together they form a module. DO NOT include components that are not essential to the repository.
Firstly reason about the components and then group them and return the result in the following format:
<grouped_components>
{{
    "module_name_1": {{
        "path": <path_to_the_module>, # the path to the module can be file or directory
        "components": [
            <component_name_1>,
            <component_name_2>,
            ...
        ]
    }},
    "module_name_2": {{
        "path": <path_to_the_module>,
        "components": [
            <component_name_1>,
            <component_name_2>,
            ...
        ]
    }},
    ...
}}
</grouped_components>
""".strip()

def cluster_modules(leaf_nodes: List[str], components: Dict[str, CodeComponent]) -> Dict[str, Any]:
    """
    Cluster the root components into modules.
    """
    #group leaf nodes by file
    leaf_nodes_by_file = defaultdict(list)
    for leaf_node in leaf_nodes:
        leaf_nodes_by_file[components[leaf_node].relative_path].append(leaf_node)

    root_components = ""
    for file, leaf_nodes in dict(sorted(leaf_nodes_by_file.items())).items():
        root_components += f"# {file}\n"
        for leaf_node in leaf_nodes:
            root_components += f"\t{leaf_node}\n"

    prompt = PROMPT.format(root_components=root_components)
    response = call_llm(prompt, model="claude-sonnet-4")

    #parse the response
    response = eval(response.split("<grouped_components>")[1].split("</grouped_components>")[0])

    return response