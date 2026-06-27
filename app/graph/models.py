from dataclasses import dataclass, field


@dataclass
class GraphNode:
    label: str
    properties: dict


@dataclass
class GraphEdge:
    source_qualified_name: str
    target_qualified_name: str
    relationship_type: str
    properties: dict = field(default_factory=dict)
