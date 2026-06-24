"""
Module 8: Architecture Diagram Generator.

Design decision: the original spec called for Graphviz, but Graphviz requires
installing a system-level binary (not just a pip package) — on Windows this
means a separate installer + adding it to PATH, which is exactly the kind of
"works on my machine" install step that breaks for someone else running the
project. Instead we generate the architecture diagram as inline SVG directly
from Python, so there is zero extra system dependency and the diagram is
trivial to render in the React frontend (just an <img> or inline <svg>).

The diagram layout is derived from the structure analyzer's category
breakdown — Frontend / Backend / Database / Services etc. — connected based
on common architectural convention (frontend talks to backend, backend talks
to database), giving a clean high-level architecture view.
"""

NODE_COLORS = {
    "Frontend": "#5B8DEF",
    "Backend": "#22C55E",
    "Database": "#F59E0B",
    "Services": "#A855F7",
    "Tests": "#94A3B8",
    "Config": "#64748B",
    "Documentation": "#94A3B8",
    "Other": "#475569",
}

LAYER_ORDER = ["Frontend", "Backend", "Services", "Database"]


def generate_architecture_svg(category_counts: dict[str, int], languages: dict[str, int]) -> str:
    present_layers = [layer for layer in LAYER_ORDER if category_counts.get(layer, 0) > 0]
    if not present_layers:
        present_layers = [k for k in category_counts.keys() if k != "Other"][:4] or ["Other"]

    box_w, box_h = 240, 90
    gap_y = 70
    width = 420
    height = len(present_layers) * (box_h + gap_y) + 40

    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="ui-monospace, Menlo, monospace">',
        '<defs>'
        '<marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 Z" fill="#64748B"/></marker></defs>',
    ]

    x = (width - box_w) / 2
    y = 20
    centers = []

    for layer in present_layers:
        color = NODE_COLORS.get(layer, "#475569")
        count = category_counts.get(layer, 0)
        cx, cy = x + box_w / 2, y + box_h / 2
        centers.append((cx, y + box_h))

        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="14" '
            f'fill="{color}22" stroke="{color}" stroke-width="2"/>'
        )
        svg_parts.append(
            f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" fill="{color}" '
            f'font-size="18" font-weight="700">{layer}</text>'
        )
        svg_parts.append(
            f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" fill="#94A3B8" '
            f'font-size="13">{count} file{"s" if count != 1 else ""}</text>'
        )
        y += box_h + gap_y

    # Arrows connecting consecutive layers top-to-bottom.
    for i in range(len(centers) - 1):
        x1, y1 = centers[i]
        x2 = x1
        y2 = y1 + gap_y - box_h - 20
        svg_parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2 + box_h}" '
            f'stroke="#64748B" stroke-width="2" marker-end="url(#arrow)"/>'
        )

    svg_parts.append("</svg>")
    return "".join(svg_parts)


def generate_architecture_description(category_counts: dict[str, int], languages: dict[str, int]) -> str:
    top_languages = list(languages.items())[:3]
    lang_str = ", ".join(f"{name} ({count} files)" for name, count in top_languages)
    layers_present = [layer for layer in LAYER_ORDER if category_counts.get(layer, 0) > 0]
    layers_str = " → ".join(layers_present) if layers_present else "a single-layer structure"
    return (
        f"This project is primarily written in {lang_str}. "
        f"Its architecture follows a {layers_str} flow based on folder structure conventions detected "
        f"during analysis."
    )
