"""Renders the ```chart JSON the personality prompt emits (see
_personality_system in graph.py) into a PNG, server-side, with matplotlib.

Exists so /api/chart can hand back a real image instead of the raw JSON -
the webapp renders the same JSON as an HTML table client-side, but a
rendered PNG is also the right input for a later image-to-image pass (e.g.
restyling the chart with a generative model), which needs pixels, not a
table spec. It's also what the Discord bot attaches directly.

Only one shape is supported, deliberately kept simple: a plain table.
  {"type": "table", "title": "...", "columns": ["", "Name A", "Name B"],
   "rows": [["Points Scored (pts)", 344, 474], ["Sacks", 30, 41]]}
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FACE = "#2b2d31"
ROW_FACE = "#33353b"
HEADER_FACE = "#3987e5"
TEXT = "#ececec"
GRID = "#454850"


def render_chart_png(data: dict[str, Any]) -> bytes:
    """Takes one parsed ```chart JSON object, returns PNG bytes."""
    if data.get("type") != "table" or not isinstance(data.get("columns"), list) \
            or not isinstance(data.get("rows"), list):
        raise ValueError(f"unsupported chart type: {data.get('type')!r}")

    fig = _render_table(data)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=FACE)
    plt.close(fig)
    return buf.getvalue()


def _cell_text(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value)


def _render_table(data: dict[str, Any]):
    columns = [str(c) for c in data["columns"]]
    rows = data["rows"]
    cell_text = [[_cell_text(v) for v in row] for row in rows]

    n_rows, n_cols = len(rows), len(columns)
    fig_w = max(4.0, 1.4 * n_cols)
    fig_h = max(1.2, 0.4 * (n_rows + 1) + 0.6)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor=FACE)
    ax.axis("off")

    table = ax.table(cellText=cell_text, colLabels=columns, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)
    table.auto_set_column_width(col=list(range(n_cols)))

    for (r, _c), cell in table.get_celld().items():
        cell.set_edgecolor(GRID)
        if r == 0:
            cell.set_facecolor(HEADER_FACE)
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor(ROW_FACE if r % 2 else FACE)
            cell.set_text_props(color=TEXT)

    if data.get("title"):
        ax.set_title(str(data["title"]), color=TEXT, fontsize=12, pad=14)

    fig.tight_layout()
    return fig
