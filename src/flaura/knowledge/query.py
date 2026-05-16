from __future__ import annotations

from dataclasses import dataclass, field

from .graph import KnowledgeGraph


@dataclass
class ContextBundle:
    nodes: list[tuple[str, dict]] = field(default_factory=list)
    edges: list[tuple[str, str, dict]] = field(default_factory=list)


def query(graph: KnowledgeGraph, text: str, max_nodes: int = 20) -> ContextBundle:
    nodes = graph.query(text, max_nodes=max_nodes)
    node_ids = {n for n, _ in nodes}
    edges = graph.query_edges(node_ids)
    return ContextBundle(nodes=nodes, edges=edges)
