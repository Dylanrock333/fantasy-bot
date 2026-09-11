"""Renders the bot's ```chart``` JSON payload (`bar`/`comparison` shapes) to
a PNG. Shared by api/server.py's /api/chart (returns the bytes straight to
the Discord bot) and scripts/chat_audit.py (writes the bytes to a report
file) so the chart schema is defined in exactly one place.
"""
import io
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render_chart_png(chart: dict) -> Optional[bytes]:
    """Returns PNG bytes, or None for an unrecognized chart shape."""
    fig = None

    if chart.get("type") == "bar" and chart.get("categories"):
        categories = chart["categories"]
        series = chart.get("series") or []
        x = range(len(categories))
        width = 0.8 / max(len(series), 1)
        fig, ax = plt.subplots(figsize=(6, 4))
        for i, s in enumerate(series):
            offset = (i - (len(series) - 1) / 2) * width
            ax.bar([xi + offset for xi in x], s.get("values", []), width, label=s.get("name", f"Series {i + 1}"))
        ax.set_xticks(list(x))
        ax.set_xticklabels(categories)
        ax.set_ylabel(chart.get("unit", ""))
        ax.set_title(chart.get("title", ""))
        if len(series) > 1:
            ax.legend()

    elif chart.get("type") == "comparison" and chart.get("rows"):
        rows = chart["rows"]
        names = [str(s) for s in chart.get("series") or []]
        cols = min(len(rows), 3)
        grid_rows = -(-len(rows) // cols)  # ceil div
        fig, axes = plt.subplots(grid_rows, cols, figsize=(3.2 * cols, 2.8 * grid_rows), squeeze=False)
        for i, row in enumerate(rows):
            ax = axes[i // cols][i % cols]
            ax.bar(names, row.get("values", []))
            ax.set_title(row.get("label", ""), fontsize=10)
            ax.set_ylabel(row.get("unit", ""), fontsize=8)
            ax.tick_params(axis="x", labelsize=8)
        for j in range(len(rows), grid_rows * cols):
            axes[j // cols][j % cols].axis("off")
        if chart.get("title"):
            fig.suptitle(chart["title"])

    if fig is None:
        return None

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
