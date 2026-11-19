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
LAYOUT = {
    "customers": (900, 100), "orders": (900, 420), "order_items": (900, 930),
    "order_payments": (260, 465), "order_reviews": (1570, 455),
    "products": (600, 1390), "sellers": (1200, 1390),
    "geolocation": (100, 1490), "product_category_name_translation": (1700, 1490),
}
# Child table -> parent table: routing in SVG; draw.io uses equivalent border anchors.
EDGE_ROUTES = {
    ("orders", "customers"): ("M1100 420 V301", (1110, 368), (0.5, 0), (0.5, 1)),
    ("order_items", "orders"): ("M1100 930 V708", (1110, 823), (0.5, 0), (0.5, 1)),
    ("order_items", "products"): ("M1010 1189 V1280 H800 V1390", (823, 1311), (0.28, 1), (0.5, 0)),
    ("order_items", "sellers"): ("M1190 1189 V1305 H1400 V1390", (1260, 1337), (0.72, 1), (0.5, 0)),
    ("order_payments", "orders"): ("M660 568 H900", (760, 541), (1, 0.5), (0, 0.5)),
    ("order_reviews", "orders"): ("M1570 568 H1300", (1392, 541), (0, 0.5), (1, 0.5)),
}
def temporal(col):
    # order_approved_at is a timestamp despite the legacy dictionary's text source_type.
    return col["source_type"] == "datetime" or col["name"] == "order_approved_at"
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
                          gridSize="10", page="1", pageScale="1", pageWidth="2250",
                          pageHeight="1850", math="0", shadow="0")
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    positions = LAYOUT
    for name, table in tables.items():
        x, y = positions[name]
        cols = sorted(table["columns"], key=lambda c: (not temporal(c), c["name"]))
        h = 56 + 29 * len(cols)
        cell = ET.SubElement(root, "mxCell", id=name, value=name + " (" + str(counts.get(name, 0)) + " rows)",
                             style="swimlane;horizontal=1;startSize=44;rounded=1;fillColor=#e2e8f0;fontStyle=1;whiteSpace=wrap;",
                             vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width="400",
                      height=str(h), **{"as": "geometry"})
        for idx, c in enumerate(cols):
            fk_cols = {v for fk in table["foreign_keys"] for v in fk["columns"]}
            key = " / ".join(x for x in ("PK" if c["primary_key_position"] else "",
                                         "FK" if c["name"] in fk_cols else "") if x)
            val = (key + "  " if key else "") + c["name"] + " : " + c["sql_type"]
            child = ET.SubElement(root, "mxCell", id=name + "." + c["name"], value=val,
                                  style="text;html=1;whiteSpace=wrap;align=left;spacingLeft=10;"
                                        "fillColor=" + color(c) + ";strokeColor=#cbd5e1;",
                                  vertex="1", parent=name)
            ET.SubElement(child, "mxGeometry", x="0", y=str(48 + 29 * idx),
                          width="400", height="29", **{"as": "geometry"})
    for name, t in tables.items():
        for f in t["foreign_keys"]:
            parent = f["referenced_table"]
            if (name, parent) not in EDGE_ROUTES:
                raise ValueError(f"Unknown FK routing: {name} -> {parent}")
            _, _, src, dst = EDGE_ROUTES[(name, parent)]
            label = name + "." + ",".join(f["columns"]) + " → " + parent + "." + ",".join(f["referenced_columns"])
            style = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;"
                     "endFill=1;strokeWidth=3;strokeColor=#0f766e;fontSize=12;"
                     "fontColor=#115e59;labelBackgroundColor=#ffffff;"
                     f"exitX={src[0]};exitY={src[1]};entryX={dst[0]};entryY={dst[1]};")
            edge = ET.SubElement(root, "mxCell", id=f["name"], value=label,
                                 style=style, edge="1", parent="1",
                                 source=name, target=parent)
            ET.SubElement(edge, "mxGeometry", relative="1", **{"as": "geometry"})
    ET.ElementTree(graph).write(doc / "schema.drawio", encoding="utf-8", xml_declaration=True)
    # Browser explorer embeds the same SVG, preserving visible links and all columns.
    rows = []
    for lane, names in GROUPS:
        rows.append("<h2>" + html.escape(lane) + "</h2><div class='lane'>")
        for name in names:
            t = tables[name]
            rows.append("<section class='table' id='" + name + "'><h3>" + name +
                        " <small>" + format(counts.get(name, 0), ",") + " records</small></h3>")
            fk_cols = {v for fk in t["foreign_keys"] for v in fk["columns"]}
            for c in sorted(t["columns"], key=lambda c: (not temporal(c), c["name"])):
                cls = "maintenance" if maintenance(c) else "timestamp" if temporal(c) else ""
                key = " / ".join(x for x in ("PK" if c["primary_key_position"] else "",
                                             "FK" if c["name"] in fk_cols else "") if x)
                prefix = "<b class='key'>" + key + "</b> " if key else ""
                rows.append("<div class='column " + cls + "'>" + prefix + html.escape(c["name"]) +
                            " <small>" + html.escape(c["sql_type"]) + "</small></div>")
            if t["foreign_keys"]:
                linked = []
                for f in t["foreign_keys"]:
                    target = f["referenced_table"]
                    linked.append("<li>" + html.escape(name + "." + ",".join(f["columns"])) +
                                  " → <a href='#" + target + "'>" +
                                  html.escape(target + "." + ",".join(f["referenced_columns"])) +
                                  "</a></li>")
                rows.append("<aside><strong>FK: Child → Parent</strong><ul>" +
                            "".join(linked) + "</ul></aside>")
            rows.append("</section>")
        rows.append("</div>")
    css = """body{font:14px Arial,sans-serif;color:#172033;margin:25px;background:#f8fafc}
.diagram-scroll{max-width:100%;overflow:auto;border:1px solid #cbd5e1;border-radius:10px;background:white;padding:10px}
.diagram-scroll img{display:block;width:2220px;height:auto;max-width:none}
.lane{display:flex;flex-wrap:nowrap;gap:22px;overflow-x:auto;padding:10px 0 24px}
.table{min-width:340px;max-width:450px;flex:1;background:white;border:1px solid #94a3b8;border-radius:10px;overflow:hidden}
h3{margin:0;padding:12px 15px;background:#dfe7f2}small{color:#475569;font-size:11px}
.column{padding:7px 15px;border-bottom:1px solid #e2e8f0}
.timestamp{background:#c9edff}.maintenance{background:#fff0b2}
.key{font-size:11px;color:#115e59}
aside{padding:10px 15px;font-size:12px;background:#f1f5f9;line-height:1.7}
aside ul{margin:5px 0;padding-left:20px}a{color:#0f766e}"""
    count_columns = sum(len(t["columns"]) for t in tables.values())
    page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Olist schema</title><style>" + css + "</style></head><body>"
            "<h1>Olist — relational database schema</h1><p>9 tables · " +
            str(count_columns) + " columns · 6 declared FK relations. Arrows point from "
            "child FK to parent PK. Blue: timestamp; yellow: maintenance time. "
            "Planned times may not represent observed events.</p>"
            "<div class='diagram-scroll'><img src='schema.svg' "
            "alt='Olist ERD with nine tables and six directed FK relationships'></div>"
            "<h2>Table &amp; column explorer</h2>" + "".join(rows) + "</body></html>\n")
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
    # Full SVG overview, with edge corridors kept outside the table bodies.
    count_columns = sum(len(t["columns"]) for t in tables.values())
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2220 1840" width="2220" height="1840" role="img" aria-labelledby="schema-title schema-desc">',
        '<title id="schema-title">Olist relational database schema</title>',
        '<desc id="schema-desc">Nine complete tables, fifty-two columns and six directed foreign keys; arrows point from child tables to referenced parent tables.</desc>',
        '<defs><marker id="fk-arrow" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0 L10 5 L0 10 Z" fill="#0f766e"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="100" y="51" font-family="Arial,sans-serif" font-size="27" font-weight="700" fill="#0f172a">Olist — Relational Database Schema</text>',
        f'<text x="100" y="77" font-family="Arial,sans-serif" font-size="15" fill="#475569">9 tables · {count_columns} columns · 6 declared FK relations · arrows: Child → Parent</text>',
        '<rect x="1350" y="35" width="22" height="19" fill="#c9edff" stroke="#94a3b8"/><text x="1379" y="51" font-family="Arial,sans-serif" font-size="14" fill="#334155">Timestamp</text>',
        '<rect x="1510" y="35" width="22" height="19" fill="#fff0b2" stroke="#94a3b8"/><text x="1539" y="51" font-family="Arial,sans-serif" font-size="14" fill="#334155">Maintenance time</text>',
        '<text x="1750" y="51" font-family="Arial,sans-serif" font-size="14" fill="#334155">PK = Primary Key   FK = Foreign Key</text>',
        '<text x="100" y="1381" font-family="Arial,sans-serif" font-size="16" font-weight="600" fill="#64748b">Independent reference tables (no declared FK)</text>',
    ]
    for name, t in tables.items():
        for f in t["foreign_keys"]:
            parent = f["referenced_table"]
            if (name, parent) not in EDGE_ROUTES:
                raise ValueError(f"Unknown FK routing: {name} -> {parent}")
            path, label_xy, _, _ = EDGE_ROUTES[(name, parent)]
            caption = ",".join(f["columns"]) + " → " + ",".join(f["referenced_columns"])
            details = name + "." + ",".join(f["columns"]) + " → " + parent + "." + ",".join(f["referenced_columns"])
            svg.append(f'<path data-fk="{html.escape(f["name"])}" data-child="{name}" data-parent="{parent}" d="{path}" fill="none" stroke="#0f766e" stroke-width="3.5" stroke-linejoin="round" marker-end="url(#fk-arrow)"><title>{html.escape(details)}</title></path>')
            x, y = label_xy
            label_width = max(80, len(caption) * 7.4) + 18
            svg.append(f'<g transform="translate({x},{y})"><rect x="-9" y="-17" width="{label_width}" height="24" rx="5" fill="white" stroke="#99c3ba"/><text x="0" y="0" font-family="Arial,sans-serif" font-size="13" font-weight="600" fill="#115e59">{html.escape(caption)}</text></g>')
    for name, t in tables.items():
        x, y = LAYOUT[name]
        h = 56 + 29 * len(t["columns"])
        svg.append(f'<g id="table-{name}" data-table="{name}">')
        svg.append(f'<rect x="{x}" y="{y}" width="400" height="{h}" rx="9" fill="white" stroke="#64748b" stroke-width="1.8"/>')
        svg.append(f'<path d="M{x+9} {y} H{x+391} Q{x+400} {y} {x+400} {y+9} V{y+48} H{x} V{y+9} Q{x} {y} {x+9} {y} Z" fill="#dfe7f2"/>')
        svg.append(f'<text x="{x+15}" y="{y+30}" font-family="Arial,sans-serif" font-size="17" font-weight="700" fill="#0f172a">{html.escape(name)}</text>')
        svg.append(f'<text x="{x+384}" y="{y+29}" text-anchor="end" font-family="Arial,sans-serif" font-size="12" fill="#475569">{counts.get(name, 0):,} rows</text>')
        fk_cols = {v for fk in t["foreign_keys"] for v in fk["columns"]}
        cols = sorted(t["columns"], key=lambda c: (not temporal(c), c["name"]))
        for j, c in enumerate(cols):
            yy = y + 48 + j * 29
            key = " / ".join(k for k in ("PK" if c["primary_key_position"] else "",
                                         "FK" if c["name"] in fk_cols else "") if k)
            svg.append(f'<g class="field" data-column="{name}.{c["name"]}"><rect x="{x+5}" y="{yy}" width="390" height="29" fill="{color(c)}"/><text x="{x+14}" y="{yy+19}" font-family="Arial,sans-serif" font-size="13.3" fill="#334155">{html.escape(c["name"])}</text>' +
                       (f'<text x="{x+384}" y="{yy+19}" text-anchor="end" font-family="Arial,sans-serif" font-size="12" font-weight="700" fill="#0f766e">{html.escape(key)}</text>' if key else "") + '</g>')
        svg.append('</g>')
    svg.append('</svg>')
    (doc / "schema.svg").write_text("\n".join(svg) + "\n", encoding="utf-8")

if __name__=="__main__":
    p=json.loads((BASE/"input/data_dictionary.json").read_text())
    provenance = BASE / "source" / "provenance.json"
    counts = json.loads(provenance.read_text())["row_counts"] if provenance.exists() else {t["table"]: 0 for t in p["tables"]}
    generate(p, counts)
