from __future__ import annotations

import json
import os
from pathlib import Path

import networkx as nx
from graphify.build import build_from_json


def load_graph(path: Path) -> nx.Graph:
    if not path.exists():
        return build_from_json({"nodes": [], "edges": []})
    raw = json.loads(path.read_text(encoding="utf-8"))
    # build_from_json handles both "edges" and "links" key natively
    return build_from_json(raw)


def save_graph(G: nx.Graph, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = nx.node_link_data(G, edges="links")
    # build_from_json expects "edges"; rename for consistency
    data["edges"] = data.pop("links")
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
