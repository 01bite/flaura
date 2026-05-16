from __future__ import annotations

from .query import ContextBundle

_BYTE_LIMIT = 2000


def format_context(bundle: ContextBundle) -> str:
    """Render a ContextBundle as a compact 'Known facts' block."""
    if not bundle.nodes:
        return ""
    label_map = {n: a.get("label", n) for n, a in bundle.nodes}
    lines = []
    for node_id, attrs in bundle.nodes:
        label = attrs.get("label", node_id)
        kind = attrs.get("file_type", "concept")
        lines.append(f"{label} ({kind})")
    for src_id, dst_id, attrs in bundle.edges:
        src_label = label_map.get(src_id, src_id)
        dst_label = label_map.get(dst_id, dst_id)
        rel = attrs.get("relation", "related_to")
        lines.append(f"  {src_label} — {rel} → {dst_label}")
    return "\n".join(lines)[:_BYTE_LIMIT]
