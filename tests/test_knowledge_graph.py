from __future__ import annotations

import pytest

from flaura.knowledge import KnowledgeGraph, format_context, query


def _three_node_graph(tmp_path):
    kg = KnowledgeGraph(tmp_path / "graph.json")
    kg.add_patch(
        nodes=[
            {"id": "alice", "label": "Alice Smith", "file_type": "concept", "source_file": "test"},
            {"id": "bob", "label": "Bob Jones", "file_type": "concept", "source_file": "test"},
            {"id": "standup", "label": "Team Standup", "file_type": "concept", "source_file": "test"},
        ],
        edges=[
            {"source": "alice", "target": "standup", "relation": "attends", "confidence": "EXTRACTED", "source_file": "test"},
            {"source": "bob", "target": "standup", "relation": "attends", "confidence": "EXTRACTED", "source_file": "test"},
        ],
    )
    return kg


def test_round_trip(tmp_path):
    graph_path = tmp_path / "graph.json"
    kg = _three_node_graph(tmp_path)
    assert graph_path.exists()

    kg2 = KnowledgeGraph(graph_path)
    assert kg2._graph.number_of_nodes() == 3
    assert kg2._graph.number_of_edges() == 2
    labels = {a.get("label") for _, a in kg2._graph.nodes(data=True)}
    assert "Alice Smith" in labels
    assert "Bob Jones" in labels
    assert "Team Standup" in labels


def test_dedup_on_merge(tmp_path):
    kg = KnowledgeGraph(tmp_path / "graph.json")
    patch = {"id": "alice", "label": "Alice Smith", "file_type": "concept", "source_file": "test"}
    kg.add_patch(nodes=[patch], edges=[])
    kg.add_patch(nodes=[patch], edges=[])
    assert kg._graph.number_of_nodes() == 1


def test_query_returns_context_with_edge(tmp_path):
    kg = _three_node_graph(tmp_path)
    bundle = query(kg, "alice standup")
    node_labels = {a.get("label") for _, a in bundle.nodes}
    assert "Alice Smith" in node_labels
    assert "Team Standup" in node_labels
    text = format_context(bundle)
    assert "Alice Smith" in text
    assert "Team Standup" in text
    assert "attends" in text
