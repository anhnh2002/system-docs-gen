from dataclasses import dataclass
from dependency_analyzer import CodeComponent

@dataclass
class DocAgentDeps:
    absolute_docs_path: str
    registry: dict
    components: dict[str, CodeComponent]