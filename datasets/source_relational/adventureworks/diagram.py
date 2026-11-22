#!/usr/bin/env python3
"""Human-only semantic layout; does not annotate model inputs or assert ET identity.
SVG, editable draw.io and the scrollable viewer share exactly the same geometry.
PNG export uses CairoSVG (pip install cairosvg).
"""
from pathlib import Path
import argparse
import html
import json
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parent
TIME = {'datetime', 'date', 'time', 'datetime2', 'smalldatetime'}
BLUE, YELLOW = '#d9f1ff', '#fff2b3'
# Vertical business lanes; columns 0..2 have a non-maintenance temporal column.
# Columns 3..5 contain no temporal column other than ModifiedDate.
LANES = [
 ('01  SALES | offer / cart → order → order line', [
 ['SpecialOffer', 'ShoppingCartItem'], ['SalesOrderHeader'], ['CurrencyRate'],
 ['Customer', 'Store', 'SalesPerson', 'CreditCard'],
 ['SalesOrderDetail', 'SpecialOfferProduct', 'SalesOrderHeaderSalesReason', 'PersonCreditCard'],
 ['SalesReason', 'Currency', 'CountryRegionCurrency', 'SalesTaxRate', 'SalesTerritory']]),
 ('02  PROCUREMENT | supplier terms → purchase order → purchase line', [
 ['ProductVendor'], ['PurchaseOrderHeader'], ['PurchaseOrderDetail'], ['Vendor'], [], ['ShipMethod']]),
 ('03  MANUFACTURING | bill of materials → work order → operation / transaction', [
 ['BillOfMaterials'], ['WorkOrder'], ['WorkOrderRouting', 'TransactionHistory', 'TransactionHistoryArchive'],
 ['ProductInventory'], [], ['Location', 'ScrapReason', 'UnitMeasure']]),
 ('04  PRODUCT | product lifecycle → effective prices / costs → review', [
 ['Product'], ['ProductCostHistory', 'ProductListPriceHistory'], ['ProductReview'],
 ['ProductModel', 'ProductSubcategory', 'ProductCategory', 'ProductDescription'],
 ['ProductDocument', 'ProductModelIllustration', 'ProductModelProductDescriptionCulture', 'ProductProductPhoto'],
 ['Document', 'Illustration', 'ProductPhoto', 'Culture']]),
 ('05  PEOPLE & ORGANIZATION | employee → assignment / rate / territory history', [
 ['Employee', 'Shift'], ['EmployeeDepartmentHistory', 'EmployeePayHistory'], ['SalesPersonQuotaHistory', 'SalesTerritoryHistory'],
 ['BusinessEntity', 'Person', 'JobCandidate', 'Department'],
 ['BusinessEntityAddress', 'BusinessEntityContact', 'EmailAddress', 'PersonPhone', 'Password'],
 ['ContactType', 'PhoneNumberType']]),
 ('06  SHARED GEOGRAPHY | address → province → country', [[], [], [], ['Address'], ['StateProvince'], ['CountryRegion', 'AddressType']]),
 ('07  SYSTEM METADATA | technical times; separate from business processes', [['AWBuildVersion'], ['DatabaseLog'], ['ErrorLog'], [], [], []]),
]
COLS = ['Temporal: anchor / lifecycle', 'Temporal: order / effective period', 'Temporal: detail / occurrence',
        'Reference: entity / snapshot', 'Reference: detail / association', 'Reference: classification / support']
# Display grain is a reading aid, not an ET gold label. PKs remain the identity evidence.
GRAIN = {
 'SalesOrderHeader':'one sales order', 'SalesOrderDetail':'one line within a sales order',
 'PurchaseOrderHeader':'one purchase order', 'PurchaseOrderDetail':'one line within a purchase order',
 'WorkOrder':'one manufacturing work order', 'WorkOrderRouting':'one operation for a work order / product',
 'TransactionHistory':'one inventory transaction', 'TransactionHistoryArchive':'one archived inventory transaction',
 'Product':'one product', 'ProductInventory':'one product at one location',
 'ProductCostHistory':'one product cost effective period', 'ProductListPriceHistory':'one product price effective period',
 'ProductVendor':'one product / vendor supply relationship', 'BillOfMaterials':'one component-use record / effective period',
 'Employee':'one employee', 'EmployeeDepartmentHistory':'one employee department / shift assignment period',
 'EmployeePayHistory':'one employee pay-rate change', 'SalesTerritoryHistory':'one salesperson territory assignment period',
 'SalesPersonQuotaHistory':'one salesperson quota period', 'Shift':'one shift definition (time of day)',
 'SpecialOffer':'one offer effective period', 'CurrencyRate':'one dated currency-pair rate',
 'ShoppingCartItem':'one shopping-cart item', 'ProductReview':'one product review',
 'AWBuildVersion':'one database build metadata record', 'DatabaseLog':'one DDL log record (empty snapshot)',
 'ErrorLog':'one technical error record (empty snapshot)',
}
W, GAP, RH, HH = 420, 64, 23, 80

def temporal(c): return c['source_type'] in TIME

def grain(t):
    label = GRAIN.get(t['table'], 'PK grain: ' + ', '.join(t['primary_key']))
    return label if len(label) <= 66 else label[:63] + '…'

def geometry(tables):
    names = [n for _, cols in LANES for col in cols for n in col]
    assert len(names) == len(set(names)) == len(tables) and set(names) == set(tables)
    boxes, bands, y = {}, [], 210
    for title, cols in LANES:
        top = y
        for ci, col in enumerate(cols):
            cy = top + 58
            for name in col:
                t = tables[name]
                assert any(temporal(c) and c['name'] != 'ModifiedDate' for c in t['columns']) == (ci < 3), name
                h = HH + RH * len(t['columns'])
                boxes[name] = (36 + ci * (W + GAP), cy, W, h)
                cy += h + 38
        y = max((b[1]+b[3] for n,b in boxes.items() if n in [n for col in cols for n in col]), default=top) + 46
        bands.append((title, top, y-top-14))
    return boxes, bands, 36+6*(W+GAP), y+24

def generate(tables=None):
    if tables is None: tables = {t['table']:t for t in json.loads((BASE/'input/data_dictionary.json').read_text())['tables']}
    boxes,bands,width,height = geometry(tables)
    root=ET.Element('mxfile',host='app.diagrams.net')
    diagrams=[('Business overview', list(tables))]+[(schema,[n for n,t in tables.items() if t['source_schema']==schema]) for schema in sorted({t['source_schema'] for t in tables.values()})]
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<defs><marker id="fk" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 1L7 4L0 7" fill="none" stroke="#64748b"/></marker></defs>',
         '<rect width="100%" height="100%" fill="white"/>']
    def text(x,y,s,size=14,fill='#334155',bold=False):
        return f'<text x="{x}" y="{y}" font-family="DejaVu Sans,sans-serif" font-size="{size}" fill="{fill}" font-weight="{700 if bold else 400}">{html.escape(s)}</text>'
    notes=[('AdventureWorks | Business flow & physical schema',27),
           ('71 tables / 90 declared FKs. Lanes group business context, not Entity Type equivalence. Orders, lines and operations retain distinct grains.',14),
           ('SKY BLUE = non-ModifiedDate date/time (actual, planned, effective or descriptive). YELLOW = ModifiedDate maintenance time.',14),
           ('Left: non-maintenance temporal columns. Right: ModifiedDate-only / no temporal columns. Arrows: child FK → referenced key; not process sequence.',14)]
    for i,(s,size) in enumerate(notes): svg.append(text(36,40+i*30,s,size,bold=i==0))
    for ci,title in enumerate(COLS): svg.append(text(36+ci*(W+GAP),184,title,14,bold=True))
    for title,y,h in bands:
        svg.append(f'<rect x="16" y="{y}" width="{width-32}" height="{h}" rx="10" fill="#f8fafc" stroke="#cbd5e1"/>')
        svg.append(text(36,y+31,title,18,bold=True))
    # Route through vertical gutters and the lane's top corridor; cards mask unrelated crossings.
    routes=[]
    for name,t in tables.items():
        x,y,w,h=boxes[name]
        for fi,f in enumerate(t['foreign_keys']):
            tx,ty,tw,th=boxes[f['referenced_table']]
            si=next(i for i,c in enumerate(t['columns']) if c['name']==f['columns'][0])
            ti=next(i for i,c in enumerate(tables[f['referenced_table']]['columns']) if c['name']==f['referenced_columns'][0])
            sy=y+HH+RH*si+RH/2; ey=ty+HH+RH*ti+RH/2
            corridor=min(y,ty)-18-(fi%4)*4
            pts=[(x+w,sy),(x+w+16+fi%4*6,sy),(x+w+16+fi%4*6,corridor),(tx-18-fi%4*6,corridor),(tx-18-fi%4*6,ey),(tx,ey)]
            routes.append((name,f,pts))
            desc=name+'.'+','.join(f['columns'])+' → '+f['referenced_table']+'.'+','.join(f['referenced_columns'])
            svg.append(f'<path class="fk" data-source="{name}" data-target="{f["referenced_table"]}" d="M'+ ' L'.join(f'{a},{b}' for a,b in pts)+f'" fill="none" stroke="#94a3b8" stroke-width="1.2" opacity="0.55" marker-end="url(#fk)"><title>{html.escape(desc)}</title></path>')
    for name,t in tables.items():
        x,y,w,h=boxes[name]
        svg.append(f'<g class="table" id="{name}" tabindex="0" role="button" aria-label="{name}"><title>{html.escape(t["definition"] or name)}</title><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white" stroke="#64748b"/>')
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{HH}" fill="#e2e8f0"/>')
        svg += [text(x+10,y+19,t['source_schema'],11),text(x+10,y+41,name,16,bold=True),text(x+10,y+65,grain(t),10)]
        for i,c in enumerate(t['columns']):
            ry=y+HH+i*RH
            color=YELLOW if c['name']=='ModifiedDate' else BLUE if temporal(c) else '#ffffff'
            svg.append(f'<rect x="{x+1}" y="{ry}" width="{w-2}" height="{RH}" fill="{color}"/>')
            key=('PK ' if c['primary_key_position'] else '')+('FK' if c['foreign_keys'] else '')
            svg += [text(x+10,ry+16,c['name'],12),text(x+285,ry+16,key,10),text(x+340,ry+16,c['source_type'],10)]
        svg.append('</g>')
    svg.append('</svg>')
    svg='\n'.join(svg)
    for label,present in diagrams:
        d=ET.SubElement(root,'diagram',id=label.replace(' ','_'),name=label)
        model=ET.SubElement(d,'mxGraphModel',page='0',grid='1',pageWidth=str(width),pageHeight=str(height))
        r=ET.SubElement(model,'root'); ET.SubElement(r,'mxCell',id='0'); ET.SubElement(r,'mxCell',id='1',parent='0')
        def cell(cid,value,x,y,w,h,style,parent='1'):
            c=ET.SubElement(r,'mxCell',id=cid,value=value,style=style,vertex='1',parent=parent)
            ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
        for i,(s,size) in enumerate(notes):cell('note'+str(i),html.escape(s),36,16+i*30,width-70,30,f'text;html=1;align=left;fontSize={size};')
        for ci,title in enumerate(COLS):cell('level'+str(ci),title,36+ci*(W+GAP),160,W,32,'text;align=left;fontStyle=1;fontSize=14;')
        for i,(title,y,h) in enumerate(bands):
            cell('lane'+str(i),title,16,y,width-32,h,'swimlane;startSize=44;horizontal=1;fillColor=#f8fafc;swimlaneFillColor=#f8fafc;strokeColor=#cbd5e1;align=left;spacingLeft=20;fontStyle=1;fontSize=18;')
        for name in present:
            t=tables[name];x,y,w,h=boxes[name]
            head=html.escape(t['source_schema'])+'<br><b>'+name+'</b><br><font style="font-size:10px">'+html.escape(grain(t))+'</font>'
            cell(name,head,x,y,w,h,'swimlane;html=1;startSize=80;horizontal=1;align=left;spacingLeft=10;fillColor=#e2e8f0;swimlaneFillColor=#ffffff;strokeColor=#64748b;fontSize=14;')
            for i,c in enumerate(t['columns']):
                color=YELLOW if c['name']=='ModifiedDate' else BLUE if temporal(c) else '#ffffff'
                key=(' [PK]' if c['primary_key_position'] else '')+(' [FK]' if c['foreign_keys'] else '')
                value=html.escape(c['name']+key+' : '+c['source_type'])
                cell(name+'.'+c['name'],value,0,HH+i*RH,W,RH,f'html=1;align=left;spacingLeft=10;fillColor={color};strokeColor=none;fontSize=12;',name)
        for name,f,pts in routes:
            if name not in present or f['referenced_table'] not in present:continue
            c=ET.SubElement(r,'mxCell',id=f['name'],value=', '.join(f['columns'])+' → '+', '.join(f['referenced_columns']),source=name+'.'+f['columns'][0],target=f['referenced_table']+'.'+f['referenced_columns'][0],edge='1',parent='1',style='edgeStyle=orthogonalEdgeStyle;html=1;endArrow=ERone;startArrow=ERmany;fontSize=9;strokeColor=#94a3b8;exitX=1;exitY=0.5;entryX=0;entryY=0.5;')
            geo=ET.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'});arr=ET.SubElement(geo,'Array',attrib={'as':'points'})
            for a,b in pts[1:-1]:ET.SubElement(arr,'mxPoint',x=str(a),y=str(b))
    ET.indent(root);ET.ElementTree(root).write(BASE/'docs/schema.drawio',encoding='utf-8',xml_declaration=True)
    (BASE/'docs/schema.svg').write_text(svg)
    (BASE/'review/database/schema.svg').write_text(svg)
    viewer='''<!doctype html><html lang="en"><meta charset="utf-8"><title>AdventureWorks schema explorer</title>
<style>body{margin:0;font:14px system-ui;color:#1e293b}header{padding:14px;background:#eef2f6;position:sticky;top:0;z-index:2}button,input,select{padding:7px;margin:3px}#viewport{overflow:auto;height:calc(100vh - 135px);border:1px solid #94a3b8}#canvas{width:max-content;transform-origin:top left}.table{cursor:pointer}.table:hover>rect:first-of-type{stroke:#0284c7;stroke-width:3}.dim{opacity:.12}.selected>rect:first-of-type{stroke:#0284c7;stroke-width:4}#viewport svg{display:block}#bar{height:19px;overflow-x:scroll;position:sticky;bottom:0;background:#eef2f6}</style>
<header><b>AdventureWorks · 71 tables · 90 declared FKs</b> <input id="search" placeholder="Find table" list="tables"><datalist id="tables">OPTIONS</datalist><button id="find">Find</button><button id="reset">Reset focus</button><label>Zoom <select id="zoom"><option>.5</option><option>.75</option><option selected>1</option><option>1.25</option><option>1.5</option></select></label><label><input type="checkbox" id="links" checked>FK edges</label><a href="schema.png">PNG</a> · <a href="schema.drawio">draw.io</a><p style="margin:5px">Scroll horizontally using the bottom scrollbar or Shift + wheel. Click a table to highlight its direct FK neighbors. Blue = date/time except ModifiedDate; yellow = ModifiedDate. Business lanes do not assert same ET or instance identity.</p></header>
<div id="viewport"><div id="canvas">SVG</div></div><div id="bar"><div id="track" style="height:1px"></div></div>
<script>
const vp=document.querySelector('#viewport'),canvas=document.querySelector('#canvas'),bar=document.querySelector('#bar'),svg=canvas.querySelector('svg');
const edges=[...svg.querySelectorAll('.fk')],tables=[...svg.querySelectorAll('.table')];
function focusTable(id){const t=document.getElementById(id);if(!t||!t.classList.contains('table'))return;let related=new Set([id]);edges.forEach(e=>{let hit=e.dataset.source===id||e.dataset.target===id;e.classList.toggle('dim',!hit);if(hit){related.add(e.dataset.source);related.add(e.dataset.target)}});tables.forEach(t=>{t.classList.toggle('dim',!related.has(t.id));t.classList.toggle('selected',t.id===id)});t.scrollIntoView({block:'center',inline:'center'});}
tables.forEach(t=>{t.onclick=()=>focusTable(t.id);t.onkeydown=e=>{if(e.key==='Enter')focusTable(t.id)}});
document.querySelector('#find').onclick=()=>{const q=document.querySelector('#search').value.toLowerCase();const t=tables.find(t=>t.id.toLowerCase()===q)||tables.find(t=>t.id.toLowerCase().includes(q));if(t)focusTable(t.id)};
document.querySelector('#search').onkeydown=e=>{if(e.key==='Enter')document.querySelector('#find').click()};
document.querySelector('#reset').onclick=()=>svg.querySelectorAll('.dim,.selected').forEach(e=>e.classList.remove('dim','selected'));
document.querySelector('#links').onchange=e=>edges.forEach(p=>p.style.display=e.target.checked?'':'none');
document.querySelector('#zoom').onchange=e=>{const z=Number(e.target.value);svg.setAttribute('width',WIDTH*z);svg.setAttribute('height',HEIGHT*z);document.querySelector('#track').style.width=svg.getAttribute('width')+'px'};
document.querySelector('#track').style.width='WIDTHpx';bar.onscroll=()=>{vp.scrollLeft=bar.scrollLeft};vp.onscroll=()=>{bar.scrollLeft=vp.scrollLeft};
</script></html>'''
    viewer=viewer.replace('OPTIONS',''.join(f'<option value="{n}">' for n in sorted(tables))).replace('SVG',svg).replace('WIDTH',str(width)).replace('HEIGHT',str(height))
    (BASE/'docs/schema.html').write_text(viewer)
    print(f'Diagrams: {len(tables)} tables, {len(routes)} FKs, {width} x {height}')

def png():
    import cairosvg
    cairosvg.svg2png(url=str(BASE/'docs/schema.svg'), write_to=str(BASE/'docs/schema.png'))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--png',action='store_true');args=parser.parse_args()
    generate()
    if args.png:png()
