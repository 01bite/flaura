from __future__ import annotations

from pathlib import Path

import networkx as nx
from graphify.build import build_merge

from .store import load_graph, save_graph


class KnowledgeGraph:
    def __init__(self, graph_path: Path) -> None:
        self._path = graph_path
        self._g: nx.Graph | None = None

    @property
    def _graph(self) -> nx.Graph:
        if self._g is None:
            self._g = load_graph(self._path)
        return self._g

    def add_patch(self, nodes: list[dict], edges: list[dict]) -> None:
        """Merge nodes+edges into the graph and persist atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        chunk = {"nodes": nodes, "edges": edges}
        # build_merge loads existing graph.json, merges chunk, deduplicates
        self._g = build_merge([chunk], self._path)
        save_graph(self._g, self._path)

    def query(self, text: str, max_nodes: int = 20) -> list[tuple[str, dict]]:
        """Return matched nodes + 1-hop neighbors (case-insensitive substring on label)."""
        tokens = text.lower().split()
        g = self._graph
        matched: set[str] = set()
        for node_id, attrs in g.nodes(data=True):
            label = attrs.get("label", "").lower()
            if any(tok in label for tok in tokens):
                matched.add(node_id)
        expanded: set[str] = set(matched)
        for node_id in matched:
            expanded.update(g.neighbors(node_id))
        return [(n, g.nodes[n]) for n in list(expanded)[:max_nodes]]

    def query_edges(self, node_ids: set[str]) -> list[tuple[str, str, dict]]:
        """Return all edges touching any of the given node IDs."""
        g = self._graph
        return [
            (u, v, data)
            for u, v, data in g.edges(data=True)
            if u in node_ids or v in node_ids
        ]

    def neighbors(self, node_id: str) -> list[str]:
        return list(self._graph.neighbors(node_id))
