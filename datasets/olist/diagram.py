#!/usr/bin/env python3
"""Produce human-only ERD pages (SVG, draw.io, HTML) for the Olist snapshot.

All three diagrams share one layout and one list of FK relationships, taken
only from the declared ``foreign_keys`` in ``input/data_dictionary.json``.
Every FK is drawn as an arrow from the child FK column to the parent PK column
(Child -> Parent). Tables without a declared FK are drawn with a dashed border;
no relationship is invented for them.
"""
from __future__ import annotations
import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent
BLUE, YELLOW = "#c9edff", "#fff0b2"
PK_COLOR, FK_COLOR, EDGE_COLOR = "#1e3a8a", "#0f766e", "#0f766e"
GROUPS = [
    ("Order & Fulfillment", ["orders", "order_items", "order_payments", "order_reviews"]),
    ("People & Catalog", ["customers", "sellers", "products", "product_category_name_translation"]),
    ("Location Reference", ["geolocation"]),
]

# ---------------------------------------------------------------- layout
# Shared geometry (pixels) for SVG and draw.io. Business-aligned placement:
# customers <- orders <- order_items -> products / sellers, with payments and
# reviews directly below orders / order_items. Reference tables without a
# declared FK sit next to the tables they describe (geolocation near
# customers, the category translation near products).
W, HDR, ROW, PAD = 340, 34, 24, 8
TOP = 150
COL = [40, 500, 1000, 1500]                      # x of the four table columns
POS = {
    "customers": (COL[0], TOP + ROW),           # customer_id row aligns with orders.customer_id
    "orders": (COL[1], TOP),
    "order_items": (COL[2], TOP),
    "products": (COL[3], TOP),
    "sellers": (COL[3], TOP + 316),
    "geolocation": (COL[0], TOP + 296),
    "order_payments": (COL[1], TOP + 296),
    "order_reviews": (COL[2], TOP + 296),
    "product_category_name_translation": (COL[3], TOP + 500),
}
CANVAS_W = COL[3] + W + 40


def temporal(col):
    return col["source_type"] == "datetime"
def maintenance(col):
    return col["name"] in {"modified_date", "updated_at"}
def color(col):
    return YELLOW if maintenance(col) else BLUE if temporal(col) else "#ffffff"
def is_pk(col):
    return bool(col["primary_key_position"])
def is_fk(col):
    return bool(col["foreign_keys"])


def ordered_columns(table):
    """PK columns (by key position), then FK columns, then the rest in source order."""
    cols = table["columns"]
    pks = sorted((c for c in cols if is_pk(c)), key=lambda c: c["primary_key_position"])
    fks = [c for c in cols if is_fk(c) and not is_pk(c)]
    rest = [c for c in cols if not is_pk(c) and not is_fk(c)]
    return pks + fks + rest


def table_height(table):
    return HDR + ROW * len(table["columns"]) + PAD


def row_center(tables, name, column):
    x, y = POS[name]
    idx = [c["name"] for c in ordered_columns(tables[name])].index(column)
    return y + HDR + ROW * idx + ROW // 2


def fk_edges(tables):
    """Declared single-column FKs as (fk_name, child, child_col, parent, parent_col)."""
    edges = []
    for name, t in tables.items():
        for f in t["foreign_keys"]:
            for cc, pc in zip(f["columns"], f["referenced_columns"]):
                edges.append((f["name"], name, cc, f["referenced_table"], pc))
    return edges


# Orthogonal routes, one per declared FK: (exit side of child, entry side of
# parent, corridor x for the vertical segment or None, entry y offset on the
# parent PK row). Offsets fan the three order_id arrows apart on orders.order_id
# so none of the six connectors cross each other or any table.
ROUTES = {
    ("orders", "customers"): ("left", "right", None, 0),
    ("order_items", "orders"): ("left", "right", None, -9),
    ("order_reviews", "orders"): ("left", "right", COL[2] - 60, 0),
    ("order_payments", "orders"): ("right", "right", COL[1] + W + 20, 9),
    ("order_items", "products"): ("right", "left", COL[3] - 80, 0),
    ("order_items", "sellers"): ("right", "left", COL[3] - 40, 0),
}


def route(tables, child, ccol, parent, pcol):
    """Return the absolute polyline from the child FK row to the parent PK row."""
    exit_side, entry_side, corridor, offset = ROUTES[(child, parent)]
    cx, _ = POS[child]
    px, _ = POS[parent]
    sy = row_center(tables, child, ccol)
    ey = row_center(tables, parent, pcol) + offset
    sx = cx if exit_side == "left" else cx + W
    ex = px if entry_side == "left" else px + W
    if corridor is None:
        # straight connector: both rows are aligned; the offset stays inside the child row
        assert abs(sy - ey) < ROW // 2, (child, parent)
        return [(sx, ey), (ex, ey)]
    return [(sx, sy), (corridor, sy), (corridor, ey), (ex, ey)]


def check_routes(tables, edges):
    """Fail loudly if a route is missing, crosses another route, or enters a table."""
    pairs = {(c, p) for _, c, _, p, _ in edges}
    assert pairs == set(ROUTES), (pairs ^ set(ROUTES))
    segs = []
    for e in edges:
        pts = route(tables, e[1], e[2], e[3], e[4])
        segs.append([(pts[i], pts[i + 1]) for i in range(len(pts) - 1)])
    boxes = {n: (x, y, x + W, y + table_height(tables[n])) for n, (x, y) in POS.items()}
    for i, s in enumerate(segs):
        for (a, b) in s:
            lo_x, hi_x = sorted((a[0], b[0])); lo_y, hi_y = sorted((a[1], b[1]))
            for n, (x0, y0, x1, y1) in boxes.items():
                # a segment may touch a table edge (its endpoint) but never run through it
                if lo_y == hi_y and y0 < lo_y < y1 and lo_x < x1 - 1 and hi_x > x0 + 1:
                    raise AssertionError(("horizontal segment crosses table", n, a, b))
                if lo_x == hi_x and x0 < lo_x < x1 and lo_y < y1 - 1 and hi_y > y0 + 1:
                    raise AssertionError(("vertical segment crosses table", n, a, b))
        for j in range(i + 1, len(segs)):
            for (a, b) in s:
                for (c, d) in segs[j]:
                    h1 = a[1] == b[1]; h2 = c[1] == d[1]
                    if h1 == h2:
                        k = 1 if h1 else 0          # shared coordinate axis
                        o = 0 if h1 else 1          # extent axis
                        if a[k] == c[k] and min(max(a[o], b[o]), max(c[o], d[o])) > \
                                max(min(a[o], b[o]), min(c[o], d[o])):
                            raise AssertionError(("routes overlap", edges[i][0], edges[j][0]))
                        continue
                    (h0, h1p), (v0, v1p) = ((a, b), (c, d)) if h1 else ((c, d), (a, b))
                    hx0, hx1 = sorted((h0[0], h1p[0])); vy0, vy1 = sorted((v0[1], v1p[1]))
                    if hx0 < v0[0] < hx1 and vy0 < h0[1] < vy1:
                        raise AssertionError(("routes cross", edges[i][0], edges[j][0]))


# ---------------------------------------------------------------- SVG
def svg_document(tables, counts, edges):
    lane_of = {n: lane for lane, names in GROUPS for n in names}
    parents = {(p, pc) for _, _, _, p, pc in edges}
    fk_target = {(c, cc): (p, pc) for _, c, cc, p, pc in edges}
    height = max(y + table_height(tables[n]) for n, (_, y) in POS.items()) + 50
    e = html.escape
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_W} {height}" '
           f'width="{CANVAS_W}" height="{height}" font-family="Arial, Helvetica, sans-serif">',
           '<title>Olist relational database schema</title>',
           '<defs>'
           f'<marker id="fk-arrow" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="8" '
           f'refX="10" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="{EDGE_COLOR}"/></marker>'
           f'<marker id="fk-tail" markerUnits="userSpaceOnUse" markerWidth="8" markerHeight="8" '
           f'refX="4" refY="4"><circle cx="4" cy="4" r="3.2" fill="{EDGE_COLOR}"/></marker>'
           '</defs>',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           f'<text x="40" y="44" font-size="24" font-weight="bold" fill="#0f172a">Olist — relational database schema</text>',
           f'<text x="40" y="70" font-size="13" fill="#475569">{len(tables)} tables · {len(edges)} declared foreign keys · '
           'arrows point from the child FK column to the parent PK column (Child → Parent)</text>']
    # legend
    lx, ly = 40, 98
    out.append(f'<rect x="{lx}" y="{ly - 13}" width="24" height="17" rx="3" fill="{PK_COLOR}"/>'
               f'<text x="{lx + 12}" y="{ly}" font-size="11" font-weight="bold" fill="#fff" text-anchor="middle">PK</text>'
               f'<text x="{lx + 32}" y="{ly}" font-size="12" fill="#334155">primary key</text>')
    lx += 130
    out.append(f'<rect x="{lx}" y="{ly - 13}" width="24" height="17" rx="3" fill="{FK_COLOR}"/>'
               f'<text x="{lx + 12}" y="{ly}" font-size="11" font-weight="bold" fill="#fff" text-anchor="middle">FK</text>'
               f'<text x="{lx + 32}" y="{ly}" font-size="12" fill="#334155">foreign key (→ referenced table.column)</text>')
    lx += 300
    out.append(f'<rect x="{lx}" y="{ly - 13}" width="24" height="17" fill="{BLUE}" stroke="#94a3b8"/>'
               f'<text x="{lx + 32}" y="{ly}" font-size="12" fill="#334155">timestamp column</text>')
    lx += 160
    out.append(f'<path d="M{lx} {ly - 4} H{lx + 46}" stroke="{EDGE_COLOR}" stroke-width="2.2" '
               'marker-start="url(#fk-tail)" marker-end="url(#fk-arrow)"/>'
               f'<text x="{lx + 56}" y="{ly}" font-size="12" fill="#334155">FK child → PK parent</text>')
    lx += 210
    out.append(f'<rect x="{lx}" y="{ly - 13}" width="24" height="17" rx="3" fill="#fff" stroke="#94a3b8" stroke-dasharray="4 3"/>'
               f'<text x="{lx + 32}" y="{ly}" font-size="12" fill="#334155">no declared FK</text>')
    # connectors first, so table cards stay on top of them
    for fk_name, c, cc, p, pc in edges:
        pts = route(tables, c, cc, p, pc)
        d = "M" + " L".join(f"{x} {y}" for x, y in pts)
        label = f"{c}.{cc} → {p}.{pc} ({fk_name})"
        out.append(f'<path id="{e(fk_name)}" d="{d}" fill="none" stroke="{EDGE_COLOR}" stroke-width="2.2" '
                   f'stroke-linejoin="round" marker-start="url(#fk-tail)" marker-end="url(#fk-arrow)" '
                   f'data-child="{c}.{cc}" data-parent="{p}.{pc}"><title>{e(label)}</title></path>')
    for name, (x, y) in POS.items():
        t = tables[name]
        h = table_height(t)
        dashed = ' stroke-dasharray="6 4"' if not any(name in (c, p) for _, c, _, p, _ in edges) else ""
        out.append(f'<g id="table-{name}" data-lane="{e(lane_of.get(name, ""))}">')
        out.append(f'<rect x="{x}" y="{y}" width="{W}" height="{h}" rx="7" fill="#fff" stroke="#64748b" stroke-width="1.3"{dashed}/>')
        out.append(f'<path d="M{x} {y + 7} Q{x} {y} {x + 7} {y} H{x + W - 7} Q{x + W} {y} {x + W} {y + 7} V{y + HDR} H{x} Z" fill="#e2e8f0"/>')
        out.append(f'<text x="{x + 10}" y="{y + 22}" font-size="15" font-weight="bold" fill="#0f172a">{e(name)}</text>')
        out.append(f'<text x="{x + W - 10}" y="{y + 22}" font-size="11" fill="#475569" text-anchor="end">'
                   f'{counts.get(name, 0):,} rows</text>')
        for j, col in enumerate(ordered_columns(t)):
            ry = y + HDR + j * ROW
            out.append(f'<rect x="{x + 1}" y="{ry}" width="{W - 2}" height="{ROW}" fill="{color(col)}"/>')
            if j:
                out.append(f'<path d="M{x + 1} {ry} H{x + W - 1}" stroke="#e2e8f0"/>')
            bx = x + 8
            for flag, fill in (("PK", PK_COLOR), ("FK", FK_COLOR)):
                if (flag == "PK" and is_pk(col)) or (flag == "FK" and is_fk(col)):
                    out.append(f'<rect x="{bx}" y="{ry + 4}" width="22" height="16" rx="3" fill="{fill}"/>'
                               f'<text x="{bx + 11}" y="{ry + 16}" font-size="10" font-weight="bold" fill="#fff" '
                               f'text-anchor="middle">{flag}</text>')
                bx += 25
            weight = ' font-weight="bold"' if is_pk(col) else ""
            ref = (name, col["name"]) in parents
            out.append(f'<text x="{x + 60}" y="{ry + 16}" font-size="12" fill="#0f172a"{weight}>{e(col["name"])}'
                       + (f'<title>referenced by FK</title>' if ref else "") + '</text>')
            if (name, col["name"]) in fk_target:
                p, pc = fk_target[(name, col["name"])]
                out.append(f'<text x="{x + W - 8}" y="{ry + 16}" font-size="11" fill="{FK_COLOR}" '
                           f'text-anchor="end">→ {e(p)}.{e(pc)}</text>')
            else:
                out.append(f'<text x="{x + W - 8}" y="{ry + 16}" font-size="10" fill="#64748b" '
                           f'text-anchor="end">{e(col["sql_type"])}</text>')
        out.append('</g>')
    note_y = height - 18
    out.append(f'<text x="40" y="{note_y}" font-size="12" fill="#475569">geolocation and product_category_name_translation '
               'have no declared FK in the SQLite schema, so no connector is drawn for them. '
               'FK links are structural, not semantic event attribution.</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def generate(data, counts):
    tables = {t["table"]: t for t in data["tables"]}
    assert set(tables) == set(POS), set(tables) ^ set(POS)
    edges = fk_edges(tables)
    check_routes(tables, edges)
    doc = BASE / "docs"
    doc.mkdir(exist_ok=True)
    # ------------------------------------------------------------ draw.io
    graph = ET.Element("mxfile", host="app.diagrams.net", modified="2026-11-19T00:00:00.000Z")
    page = ET.SubElement(graph, "diagram", name="Business-aligned Schema", id="olist")
    model = ET.SubElement(page, "mxGraphModel", dx="1600", dy="900", grid="1",
                          gridSize="10", page="1", pageScale="1", pageWidth=str(CANVAS_W),
                          pageHeight="1000", math="0", shadow="0")
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    connected = {n for _, c, _, p, _ in edges for n in (c, p)}
    for name, table in tables.items():
        x, y = POS[name]
        cols = ordered_columns(table)
        dash = "" if name in connected else "dashed=1;"
        cell = ET.SubElement(root, "mxCell", id=name, value=name + " (" + str(counts.get(name, 0)) + " rows)",
                             style="swimlane;horizontal=1;startSize=" + str(HDR) + ";rounded=1;arcSize=4;"
                                   "fillColor=#e2e8f0;strokeColor=#64748b;fontStyle=1;whiteSpace=wrap;"
                                   "collapsible=0;" + dash,
                             vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(W),
                      height=str(table_height(table)), **{"as": "geometry"})
        for idx, c in enumerate(cols):
            tags = (["PK"] if is_pk(c) else []) + (["FK"] if is_fk(c) else [])
            ref = ""
            if is_fk(c):
                ref = " → " + ", ".join(r["table"] + "." + r["column"] for r in c["foreign_keys"])
            val = ("[" + ",".join(tags) + "] " if tags else "") + c["name"] + " : " + c["sql_type"] + ref
            style = ("text;html=1;whiteSpace=wrap;align=left;spacingLeft=10;"
                     "fillColor=" + color(c) + ";strokeColor=#cbd5e1;")
            if is_pk(c):
                style += "fontStyle=1;"
            if is_fk(c):
                style += "fontColor=" + FK_COLOR + ";"
            child = ET.SubElement(root, "mxCell", id=name + "." + c["name"], value=val,
                                  style=style, vertex="1", parent=name)
            ET.SubElement(child, "mxGeometry", x="0", y=str(HDR + ROW * idx),
                          width=str(W), height=str(ROW), **{"as": "geometry"})
    for fk_name, c, cc, p, pc in edges:
        pts = route(tables, c, cc, p, pc)
        exit_side, entry_side, _, offset = ROUTES[(c, p)]
        style = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;"
                 "startArrow=oval;startFill=1;strokeColor=" + EDGE_COLOR + ";strokeWidth=2;"
                 "exitX=" + ("0" if exit_side == "left" else "1") + ";exitY=0.5;exitDx=0;exitDy=0;"
                 "entryX=" + ("0" if entry_side == "left" else "1") + ";entryY=0.5;entryDx=0;"
                 "entryDy=" + str(offset) + ";")
        edge = ET.SubElement(root, "mxCell", id=fk_name, value="",
                             style=style, edge="1", parent="1",
                             source=c + "." + cc, target=p + "." + pc)
        geo = ET.SubElement(edge, "mxGeometry", relative="1", **{"as": "geometry"})
        if len(pts) > 2:
            arr = ET.SubElement(geo, "Array", **{"as": "points"})
            for px_, py_ in pts[1:-1]:
                ET.SubElement(arr, "mxPoint", x=str(px_), y=str(py_))
    ET.ElementTree(graph).write(doc / "schema.drawio", encoding="utf-8", xml_declaration=True)
    # ------------------------------------------------------------ SVG
    svg = svg_document(tables, counts, edges)
    (doc / "schema.svg").write_text(svg, encoding="utf-8")
    # ------------------------------------------------------------ HTML
    referenced_by = {}
    for fk_name, c, cc, p, pc in edges:
        referenced_by.setdefault(p, []).append(c + "." + cc + " → " + pc)
    rows = []
    for lane, names in GROUPS:
        rows.append("<h2>" + html.escape(lane) + "</h2><div class='lane'>")
        for name in names:
            t = tables[name]
            rows.append("<section class='table' id='" + name + "'><h3>" + name +
                        " <small>" + str(counts.get(name, 0)) + " records</small></h3>")
            for c in ordered_columns(t):
                cls = "maintenance" if maintenance(c) else "timestamp" if temporal(c) else ""
                badges = ("<span class='badge pk'>PK</span>" if is_pk(c) else "") + \
                         ("<span class='badge fk'>FK</span>" if is_fk(c) else "")
                ref = ""
                if is_fk(c):
                    ref = " <span class='ref'>→ " + ", ".join(
                        "<a href='#" + r["table"] + "'>" + r["table"] + "." + r["column"] + "</a>"
                        for r in c["foreign_keys"]) + "</span>"
                rows.append("<div class='column " + cls + (" pkcol" if is_pk(c) else "") + "'>" + badges +
                            html.escape(c["name"]) + " <small>" + c["sql_type"] + "</small>" + ref + "</div>")
            fks = t["foreign_keys"]
            notes = []
            if fks:
                notes.append("FK: " + "; ".join(html.escape(", ".join(f["columns"]) +
                  " → " + f["referenced_table"] + "(" + ", ".join(f["referenced_columns"]) + ")")
                  for f in fks))
            if name in referenced_by:
                notes.append("Referenced by: " + "; ".join(html.escape(x) for x in referenced_by[name]))
            if not fks and name not in referenced_by:
                notes.append("No declared FK.")
            rows.append("<aside>" + "<br>".join(notes) + "</aside>")
            rows.append("</section>")
        rows.append("</div>")
    css = """body{font:14px Arial,sans-serif;color:#172033;margin:25px;background:#f8fafc}
    .lane{display:flex;flex-wrap:nowrap;gap:22px;overflow-x:auto;padding:10px 0 24px}
    .table{min-width:340px;max-width:450px;flex:1;background:white;border:1px solid #94a3b8;border-radius:10px;overflow:hidden}
    h3{margin:0;padding:12px 15px;background:#e2e8f0}small{color:#475569;font-size:11px}
    .column{padding:7px 15px;border-bottom:1px solid #e2e8f0}
    .timestamp{background:#c9edff}.maintenance{background:#fff0b2}
    .pkcol{font-weight:bold}.ref{color:#0f766e;font-size:12px;font-weight:normal}.ref a{color:inherit}
    .badge{display:inline-block;min-width:20px;margin-right:5px;padding:1px 3px;border-radius:3px;color:#fff;font-size:10px;font-weight:bold;text-align:center}
    .pk{background:#1e3a8a}.fk{background:#0f766e}
    .erd{overflow:auto;background:white;border:1px solid #cbd5e1;border-radius:10px;padding:10px;margin-bottom:20px}
    aside{padding:10px 15px;font-size:12px;background:#f1f5f9;line-height:1.7}"""
    page = "<!doctype html><html><head><meta charset='utf-8'><title>Olist schema</title><style>"+css+"</style></head><body>"
    page += "<h1>Olist — relational database schema</h1><p>Blue: time fields; yellow: modification time. Planned times are blue too, not necessarily occurrence times. FK links are structural, not semantic event attribution. Arrows point from the child FK column to the parent PK column.</p>"
    page += "<div class='erd'>" + svg + "</div>"
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

if __name__=="__main__":
    p=json.loads((BASE/"input/data_dictionary.json").read_text())
    # Use the validated row counts so a standalone regeneration keeps real numbers.
    prov=BASE/"source/provenance.json"
    counts=json.loads(prov.read_text())["row_counts"] if prov.exists() else {t["table"]:0 for t in p["tables"]}
    generate(p,counts)
