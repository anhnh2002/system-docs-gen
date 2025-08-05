from dataclasses import dataclass
from dependency_analyzer import CodeComponent

@dataclass
class DocAgentDeps:
    absolute_docs_path: str
    registry: dict
    components: dict[str, CodeComponent]
    path_to_current_module: list[str]
    current_module_name: str
    module_tree: dict[str, any]