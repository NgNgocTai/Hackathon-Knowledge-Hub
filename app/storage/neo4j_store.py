from neo4j import GraphDatabase

from app.graph.models import GraphEdge, GraphNode
from app.storage.exceptions import GraphStoreError
from app.storage.interfaces import GraphStore


ALLOWED_LABELS = {"File", "Function", "Class", "Requirement", "Documentation", "Commit", "Unknown"}
ALLOWED_RELATIONSHIPS = {"CALLS", "INHERITS", "DEFINES", "IMPLEMENTS", "DESCRIBES", "MODIFIES", "BELONGS_TO"}


class Neo4jGraphStore(GraphStore):
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def merge_nodes(self, nodes: list[GraphNode]) -> None:
        try:
            with self.driver.session() as session:
                for node in nodes:
                    label = self._safe_label(node.label)
                    key, value = self._identity(node)
                    session.execute_write(self._merge_node_tx, label, key, value, node.properties)
        except Exception as exc:
            raise GraphStoreError(f"Failed to merge graph nodes: {exc}") from exc

    def merge_edges(self, edges: list[GraphEdge]) -> None:
        try:
            with self.driver.session() as session:
                for edge in edges:
                    rel_type = self._safe_relationship(edge.relationship_type)
                    session.execute_write(self._merge_edge_tx, rel_type, edge)
        except Exception as exc:
            raise GraphStoreError(f"Failed to merge graph edges: {exc}") from exc

    def expand(
        self,
        entity_names: list[str],
        max_hops: int = 2,
        rel_types: list[str] | None = None,
        max_nodes: int = 50,
    ) -> list[GraphNode]:
        if not entity_names:
            return []

        rel_types = rel_types or ["CALLS", "IMPLEMENTS", "DESCRIBES"]
        rel_clause = "|".join(self._safe_relationship(rel_type) for rel_type in rel_types)
        query = (
            f"MATCH path = (n)-[r:{rel_clause}*1..{max_hops}]->(m) "
            "WHERE n.qualified_name IN $entity_names OR n.name IN $entity_names "
            "RETURN labels(m)[0] AS label, properties(m) AS properties, "
            "length(path) AS hop, type(last(relationships(path))) AS relationship "
            "ORDER BY hop ASC "
            "LIMIT $max_nodes"
        )
        try:
            with self.driver.session() as session:
                records = session.run(query, entity_names=entity_names, max_nodes=max_nodes)
                return [
                    GraphNode(
                        record["label"],
                        {
                            **record["properties"],
                            "hop": record["hop"],
                            "relationship": record["relationship"],
                        },
                    )
                    for record in records
                ]
        except Exception as exc:
            raise GraphStoreError(f"Graph expansion failed: {exc}") from exc

    def delete_by_file(self, file_path: str) -> tuple[int, int]:
        query = (
            "MATCH (n) "
            "WHERE n.file_path = $file_path OR n.source_file = $file_path OR n.path = $file_path "
            "WITH collect(n) AS nodes "
            "UNWIND nodes AS n "
            "DETACH DELETE n "
            "RETURN size(nodes) AS nodes_deleted"
        )
        try:
            with self.driver.session() as session:
                record = session.run(query, file_path=file_path).single()
                nodes_deleted = record["nodes_deleted"] if record else 0
                return nodes_deleted, 0
        except Exception as exc:
            raise GraphStoreError(f"Failed to delete graph nodes for {file_path}: {exc}") from exc

    def fetch_nodes_by_file(self, file_path: str) -> tuple[list[GraphNode], list[GraphEdge]]:
        node_query = (
            "MATCH (n) "
            "WHERE n.file_path = $file_path OR n.source_file = $file_path OR n.path = $file_path "
            "RETURN labels(n)[0] AS label, properties(n) AS properties"
        )
        edge_query = (
            "MATCH (a)-[r]->(b) "
            "WHERE a.file_path = $file_path OR a.source_file = $file_path OR a.path = $file_path "
            "RETURN a.qualified_name AS source, b.qualified_name AS target, type(r) AS type, properties(r) AS properties"
        )
        try:
            with self.driver.session() as session:
                nodes = [
                    GraphNode(record["label"], record["properties"])
                    for record in session.run(node_query, file_path=file_path)
                ]
                edges = [
                    GraphEdge(record["source"], record["target"], record["type"], record["properties"])
                    for record in session.run(edge_query, file_path=file_path)
                    if record["source"] and record["target"]
                ]
                return nodes, edges
        except Exception as exc:
            raise GraphStoreError(f"Failed to backup graph nodes for {file_path}: {exc}") from exc

    def restore(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
        self.merge_nodes(nodes)
        self.merge_edges(edges)

    def link_chunk_ids(self, chunk_mapping: dict[str, str]) -> None:
        query = "MATCH (n {qualified_name: $qualified_name}) SET n.chunk_id = $chunk_id"
        try:
            with self.driver.session() as session:
                for qualified_name, chunk_id in chunk_mapping.items():
                    session.run(query, qualified_name=qualified_name, chunk_id=chunk_id)
        except Exception as exc:
            raise GraphStoreError(f"Failed to link chunk ids: {exc}") from exc

    def health_check(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    @staticmethod
    def _merge_node_tx(tx, label: str, key: str, value: str, properties: dict) -> None:
        query = f"MERGE (n:{label} {{{key}: $value}}) SET n += $properties"
        tx.run(query, value=value, properties=properties)

    @staticmethod
    def _merge_edge_tx(tx, rel_type: str, edge: GraphEdge) -> None:
        query = (
            "MERGE (a {qualified_name: $source}) "
            "ON CREATE SET a:Unknown, a.qualified_name = $source "
            "MERGE (b {qualified_name: $target}) "
            "ON CREATE SET b:Unknown, b.qualified_name = $target "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            "SET r += $properties"
        )
        tx.run(
            query,
            source=edge.source_qualified_name,
            target=edge.target_qualified_name,
            properties=edge.properties,
        )

    def _identity(self, node: GraphNode) -> tuple[str, str]:
        properties = node.properties
        for key in ("qualified_name", "path", "req_id", "source_file", "commit_hash", "name"):
            if properties.get(key):
                return key, properties[key]
        raise GraphStoreError(f"Graph node has no identity property: {node}")

    def _safe_label(self, label: str) -> str:
        if label not in ALLOWED_LABELS:
            raise GraphStoreError(f"Unsupported graph label: {label}")
        return label

    def _safe_relationship(self, relationship_type: str) -> str:
        if relationship_type not in ALLOWED_RELATIONSHIPS:
            raise GraphStoreError(f"Unsupported graph relationship: {relationship_type}")
        return relationship_type
