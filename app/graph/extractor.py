from app.graph.models import GraphEdge, GraphNode
from app.parser.models import IntermediateRepresentation, ParsedEntity, ParsedRelationship


ENTITY_LABELS = {
    "function": "Function",
    "class": "Class",
    "file": "File",
    "requirement": "Requirement",
    "documentation": "Documentation",
    "commit": "Commit",
}


class EntityExtractor:
    def extract(self, ir: IntermediateRepresentation) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes = [self._node_from_entity(entity, ir) for entity in ir.entities]
        edges = [self._edge_from_relationship(relationship) for relationship in ir.relationships]
        edges.extend(self._belongs_to_edges(ir.entities))
        return nodes, edges

    def _node_from_entity(self, entity: ParsedEntity, ir: IntermediateRepresentation) -> GraphNode:
        label = ENTITY_LABELS[entity.entity_type]
        properties = {
            "name": entity.name,
            "qualified_name": entity.qualified_name,
            "file_path": entity.file_path,
            "source_hash": ir.source_hash,
            "language": entity.language,
        }

        if entity.entity_type == "file":
            properties = {
                "path": entity.file_path,
                "name": entity.name,
                "qualified_name": entity.qualified_name,
                "language": entity.language,
                "source_hash": ir.source_hash,
            }
        elif entity.entity_type == "function":
            properties.update(
                {
                    "line_start": entity.line_start,
                    "line_end": entity.line_end,
                    "docstring": entity.docstring,
                    "chunk_id": None,
                }
            )
        elif entity.entity_type == "class":
            properties.update(
                {
                    "line_start": entity.line_start,
                    "line_end": entity.line_end,
                    "docstring": entity.docstring,
                    "chunk_id": None,
                }
            )
        elif entity.entity_type == "documentation":
            properties = {
                "title": entity.name,
                "qualified_name": entity.qualified_name,
                "source_file": entity.file_path,
                "doc_type": entity.language,
                "chunk_id": None,
            }
        elif entity.entity_type == "requirement":
            properties = {
                "req_id": entity.name,
                "title": entity.qualified_name,
                "qualified_name": entity.qualified_name,
                "source_file": entity.file_path,
                "chunk_id": None,
            }
        elif entity.entity_type == "commit":
            properties = {
                "commit_hash": entity.qualified_name,
                "qualified_name": entity.qualified_name,
                "message": entity.content,
                "author": None,
                "timestamp": None,
            }

        return GraphNode(label=label, properties={key: value for key, value in properties.items() if value is not None})

    def _edge_from_relationship(self, relationship: ParsedRelationship) -> GraphEdge:
        return GraphEdge(
            source_qualified_name=relationship.source_qualified_name,
            target_qualified_name=relationship.target_qualified_name,
            relationship_type=relationship.relationship_type,
            properties=relationship.metadata,
        )

    def _belongs_to_edges(self, entities: list[ParsedEntity]) -> list[GraphEdge]:
        file_entities = [entity for entity in entities if entity.entity_type == "file"]
        if not file_entities:
            return []

        file_name = file_entities[0].qualified_name
        edges = []
        for entity in entities:
            if entity.entity_type in {"function", "class"}:
                edges.append(GraphEdge(entity.qualified_name, file_name, "BELONGS_TO"))
        return edges
