#!/usr/bin/env python3
"""Produce human-only ERD pages with timestamp columns and related business lanes."""
from __future__ import annotations
import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent
BLUE, YELLOW = "#c9edff", "#fff0b2"
GROUPS = [
    ("Order & Fulfillment", ["orders", "order_items", "order_payments", "order_reviews"]),
    ("People & Catalog", ["customers", "sellers", "products", "product_category_name_translation"]),
    ("Location Reference", ["geolocation"]),
]
def temporal(col):
    return col["source_type"] == "datetime"
def maintenance(col):
    return col["name"] in {"modified_date", "updated_at"}
def color(col):
    return YELLOW if maintenance(col) else BLUE if temporal(col) else "#ffffff"
def generate(data, counts):
    tables = {t["table"]: t for t in data["tables"]}
    doc = BASE / "docs"
    doc.mkdir(exist_ok=True)
    graph = ET.Element("mxfile", host="app.diagrams.net", modified="2026-11-19T00:00:00.000Z")
    page = ET.SubElement(graph, "diagram", name="Business-aligned Schema", id="olist")
    model = ET.SubElement(page, "mxGraphModel", dx="1600", dy="900", grid="1",
                          gridSize="10", page="1", pageScale="1", pageWidth="2800",
                          pageHeight="1600", math="0", shadow="0")
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    positions = {}
    for group_index, (_, names) in enumerate(GROUPS):
        for idx, name in enumerate(names):
            positions[name] = (80 + (idx % 2) * 640 + group_index * 160,
                               100 + (idx // 2) * 530 + group_index * 1050)
    for name, table in tables.items():
        x, y = positions[name]
        cols = sorted(table["columns"], key=lambda c: (not temporal(c), c["name"]))
        h = 60 + 31 * len(cols)
        cell = ET.SubElement(root, "mxCell", id=name, value=name + " (" + str(counts.get(name, 0)) + " rows)",
                             style="swimlane;horizontal=1;startSize=44;rounded=1;fillColor=#e2e8f0;fontStyle=1;whiteSpace=wrap;",
                             vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width="550",
                      height=str(h), **{"as": "geometry"})
        for idx, c in enumerate(cols):
            val = ("PK " if c["primary_key_position"] else "") + c["name"] + " : " + c["sql_type"]
            child = ET.SubElement(root, "mxCell", id=name + "." + c["name"], value=val,
                                  style="text;html=1;whiteSpace=wrap;align=left;spacingLeft=10;"
                                        "fillColor=" + color(c) + ";strokeColor=#cbd5e1;",
                                  vertex="1", parent=name)
            ET.SubElement(child, "mxGeometry", x="0", y=str(44 + 31 * idx),
                          width="550", height="31", **{"as": "geometry"})
    for name, t in tables.items():
        for f in t["foreign_keys"]:
            label = ", ".join(f["columns"]) + " → " + ", ".join(f["referenced_columns"])
            edge = ET.SubElement(root, "mxCell", id=f["name"], value=label,
                                 style="edgeStyle=orthogonalEdgeStyle;rounded=1;endArrow=block;"
                                       "strokeColor=#64748b;fontSize=10;",
                                 edge="1", parent="1", source=name, target=f["referenced_table"])
            ET.SubElement(edge, "mxGeometry", relative="1", **{"as": "geometry"})
    ET.ElementTree(graph).write(doc / "schema.drawio", encoding="utf-8", xml_declaration=True)
    # Browser-oriented SVG with horizontal scrolling, FK metadata and all columns.
    rows = []
    for lane, names in GROUPS:
        rows.append("<h2>" + html.escape(lane) + "</h2><div class='lane'>")
        for name in names:
            t = tables[name]
            rows.append("<section class='table' id='" + name + "'><h3>" + name + 
                        " <small>" + str(counts.get(name, 0)) + " records</small></h3>")
            for c in sorted(t["columns"], key=lambda c: (not temporal(c), c["name"])):
                cls = "maintenance" if maintenance(c) else "timestamp" if temporal(c) else ""
                pk = "<b>PK</b> " if c["primary_key_position"] else ""
                rows.append("<div class='column " + cls + "'>" + pk + html.escape(c["name"]) +
                            " <small>" + c["sql_type"] + "</small></div>")
            fks = t["foreign_keys"]
            if fks:
                rows.append("<aside>FK: " + "; ".join(html.escape(", ".join(f["columns"]) +
                  " → " + f["referenced_table"] + "(" + ", ".join(f["referenced_columns"]) + ")")
                  for f in fks) + "</aside>")
            rows.append("</section>")
        rows.append("</div>")
    css = """body{font:14px Arial,sans-serif;color:#172033;margin:25px;background:#f8fafc}
    .lane{display:flex;flex-wrap:nowrap;gap:22px;overflow-x:auto;padding:10px 0 24px}
    .table{min-width:340px;max-width:450px;flex:1;background:white;border:1px solid #94a3b8;border-radius:10px;overflow:hidden}
    h3{margin:0;padding:12px 15px;background:#e2e8f0}small{color:#475569;font-size:11px}
    .column{padding:7px 15px;border-bottom:1px solid #e2e8f0}
    .timestamp{background:#c9edff}.maintenance{background:#fff0b2}
    aside{padding:10px 15px;font-size:12px;background:#f1f5f9;line-height:1.7}"""
    page = "<!doctype html><html><head><meta charset='utf-8'><title>Olist schema</title><style>"+css+"</style></head><body>"
    page += "<h1>Olist — relational database schema</h1><p>Blue: time fields; yellow: modification time. Planned times are blue too, not necessarily occurrence times. FK links are structural, not semantic event attribution.</p>"
    page += "".join(rows) + "</body></html>"
    (doc / "schema.html").write_text(page, encoding="utf-8")
    txt = ["# Olist Data Dictionary", "",
           "Author descriptions derived from published CSV headers and dataset documentation. "
           "No Gold events or Entity Types are included.", ""]
    for t in data["tables"]:
        txt += ["## " + t["table"], "", t["definition"], "",
                "| Column | Type | Key | Description |",
                "|---|---|---|---|"]
        for c in t["columns"]:
            txt.append("| " + c["name"] + " | " + c["sql_type"] + " | " +
                       ("PK" if c["primary_key_position"] else "FK" if c["foreign_keys"] else "") +
                       " | " + c["definition"].replace("|", "\\|") + " |")
        txt.append("")
    (doc / "data_dictionary.md").write_text("\n".join(txt), encoding="utf-8")
    # Compact SVG ERD table map (full columns in draw.io and HTML).
    width, height = 1700, 1710
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
           '<defs><marker id="fk-arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="#0f766e"/></marker></defs>',
           '<rect width="100%" height="100%" fill="white"/>']
    # All declared child-FK -> parent-PK edges, routed outside table boxes.
    # Draw connectors first so table cards remain above connectors.
    box_xy = {}
    for gi, (_, names) in enumerate(GROUPS):
        for idx, name in enumerate(names):
            box_xy[name] = (35 + (idx % 4) * 414, 35 + gi * 560 + 28 + (idx // 4) * 230)
    route_index = 0
    for name, table in tables.items():
        for fk in table["foreign_keys"]:
            parent = fk["referenced_table"]
            if parent not in box_xy or name not in box_xy:
                continue
            sx, sy = box_xy[name]
            px, py = box_xy[parent]
            route_index += 1
            start_x = sx + 190 + (route_index % 3) * 8
            end_x = px + 190 + (route_index % 3) * 8
            if sy == py:
                # Same-row child and parent: use a separate corridor below cards.
                gap_y = sy + 210 + (route_index % 6) * 17 + 12
                # Arrow toward parent from below.
                path = f"M{start_x} {sy+210} V{gap_y} H{end_x} V{py+210}"
            else:
                gap_y = sy + 260 + (route_index % 5) * 12
                path = f"M{start_x} {sy+210} V{gap_y} H{end_x} V{py}"
            label = (name + "." + ",".join(fk["columns"]) + " → " +
                     parent + "." + ",".join(fk["referenced_columns"]))
            svg.append(f'<path d="{path}" fill="none" stroke="#0f766e" stroke-width="2.5" opacity="0.85" marker-end="url(#fk-arrow)"><title>{html.escape(label)}</title></path>')
    for gi, (lane, names) in enumerate(GROUPS):
        by = 35 + gi * 560
        svg.append(f'<text x="35" y="{by}" font-size="22" font-weight="bold" fill="#0f172a">{html.escape(lane)}</text>')
        for idx, name in enumerate(names):
            t=tables[name]; x=35+(idx%4)*414;y=by+28+(idx//4)*230
            svg.append(f'<g><rect x="{x}" y="{y}" width="395" height="210" rx="7" fill="#fff" stroke="#64748b"/>')
            svg.append(f'<rect x="{x}" y="{y}" width="395" height="32" fill="#e2e8f0"/>')
            svg.append(f'<text x="{x+10}" y="{y+22}" font-size="15" fill="#0f172a" font-weight="bold">{html.escape(name)}</text>')
            for j,c in enumerate(sorted(t["columns"],key=lambda c:(not temporal(c),c["name"]))[:7]):
                svg.append(f'<rect x="{x+5}" y="{y+36+j*23}" width="385" height="23" fill="{color(c)}"/>')
                svg.append(f'<text x="{x+11}" y="{y+53+j*23}" font-size="12" fill="#334155">{html.escape(c["name"])}</text>')
            svg.append('</g>')
    svg.append("</svg>")
    (doc / "schema.svg").write_text("\n".join(svg), encoding="utf-8")

if __name__=="__main__":
    p=json.loads((BASE/"input/data_dictionary.json").read_text())
    counts={t["table"]:0 for t in p["tables"]}
    generate(p,counts)
