#!/usr/bin/env python3
"""Color only recorded event timestamp columns; distinguish other temporal fields.

Gold-only review artifact, unrelated to model input. Draw.io and SVG are updated
from the *current* schema and authored Gold event-source inventory.
"""
from pathlib import Path
import json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
NAMES=("hospitalflow","plateflow","universityflow","warehouseflow")

def temporal(name,col):
    c=name.lower()
    field=(col.get("representation_class") or "").lower()
    value=col.get("unit") or ""
    # Column type/dictionary are supporting hints; do not mistake identifiers for timestamps.
    return field in ("date-time","date/time text","datetime","timestamp") or value=="UTC" or bool(
      re.search(r"(?:_at|_time|time|_date)$",c) and (
        col.get("event_activity") or "time" in (col.get("definition") or "").lower() or "date" in (col.get("definition") or "").lower()
      )
    )

def event_names(name,base):
    source=json.loads((base/"review/gold_dfg/gold_source_manifest.json").read_text())
    assert source["dataset"]==name
    return {t:set(v["timestamps"]) for t,v in source["tables"].items()}

def main():
    counts={}
    for name in NAMES:
        base=ROOT/"datasets"/name
        dd=json.loads((base/"input/data_dictionary.json").read_text())
        cols={t["table"]:{c["name"]:c for c in t["columns"]} for t in dd["tables"]}
        events=event_names(name,base)
        dpath=base/"docs/schema.drawio"
        tree=ET.parse(dpath)
        root=tree.getroot()
        allcells={c.get("id"):c for c in root.findall(".//mxCell")}
        changes=0
        for table,tcols in cols.items():
            # Order by physical SQL PRAGMA, not the Data Dictionary order.
            import sqlite3
            db=sqlite3.connect("file:"+str(base/"input/database.sqlite")+"?mode=ro",uri=True)
            order=[row[1] for row in db.execute('PRAGMA table_info("'+table+'")')]
            db.close()
            for idx,c in enumerate(order):
                meta=tcols.get(c)
                if meta is None or not temporal(c,meta):continue
                cell=allcells.get(table+"_name_"+str(idx)) or allcells.get(table+"_name"+str(idx))
                if cell is None:continue
                event=c in events.get(table,set()) or bool(meta.get("event_activity"))
                col="#FFF0B3" if event else "#D9F0FF"
                style=cell.get("style","")
                style=re.sub(r"(?:fontStyle|fontColor|fillColor)=[^;]*;?","",style)
                cell.set("style",style+f"fontStyle=1;fontColor={'#805000' if event else '#155E85'};fillColor={col};")
                changes+=1
        assert changes>2,(name,changes)
        # XML labels/edge coordinates remain intact.
        tree.write(dpath,encoding="utf-8",xml_declaration=True)
        # Separate SVG colored highlights are inserted before text, keeping links functional.
        svgpath=base/"review/database/schema.svg"
        svg=svgpath.read_text()
        if "Yellow: Gold event-time source" in svg:
            # Already rendered; repeated workflow runs must not stack background rectangles.
            counts[name]=changes
            continue
        for table,tcols in cols.items():
            pat=r'(<a\b[^>]*href="tables/'+re.escape(table)+r'\.md"[^>]*>)(.*?)(</a>)'
            def update(match):
                inner=match.group(2)
                for column,meta in tcols.items():
                    if not temporal(column,meta):continue
                    event=column in events.get(table,set()) or bool(meta.get("event_activity"))
                    bg="#FFF0B3" if event else "#D9F0FF"
                    fg="#805000" if event else "#155E85"
                    rex=r'(<text x="([0-9.]+)" y="([0-9.]+)"[^>]*)(>)(\s*'+re.escape(column)+r'\s*)(</text>)'
                    def color(m):
                        x=float(m.group(2));y=float(m.group(3))
                        rect=f'<rect x="{x-3:g}" y="{y-15:g}" width="283" height="19" rx="3" fill="{bg}"/>'
                        opener=m.group(1).replace('<text ','<text font-weight="700" ',1)
                        opener=re.sub(r'fill="[^"]+"',f'fill="{fg}"',opener)
                        return rect+opener+m.group(4)+m.group(5)+m.group(6)
                    inner=re.sub(rex,color,inner)
                return match.group(1)+inner+match.group(3)
            svg=re.sub(pat,update,svg,flags=re.S)
        svg=svg.replace("</svg>",'<text x="20" y="24" font-family="sans-serif" font-size="12" fill="#805000">Yellow: Gold event-time source (where established); Blue: other temporal column</text>\n</svg>')
        svgpath.write_text(svg)
        counts[name]=changes
    print(json.dumps(counts,indent=2))
if __name__=="__main__":main()
