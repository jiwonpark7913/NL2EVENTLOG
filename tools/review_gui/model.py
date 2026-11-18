"""Pure helpers for the read-only EEG reviewer."""
from __future__ import annotations
import hashlib, json, re, sqlite3
from pathlib import Path
from typing import Any

TEMPORAL_TYPES={"TIMESTAMP","TIMESTAMPTZ","DATETIME","DATETIME2","DATE","TIME"}

def read_json(path:Path):
    """PURPOSE: Read optional JSON. INPUT: Path. OUTPUT: Object or None; raises for non-object JSON."""
    if not path.is_file(): return None
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(f"Expected JSON object: {path}")
    return value

def sha256_file(path:Path)->str:
    """PURPOSE: Fingerprint a file incrementally. INPUT: Path. OUTPUT: SHA-256 hex digest."""
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""): digest.update(block)
    return digest.hexdigest()

def graph_hash(graph:dict)->str:
    """PURPOSE: Bind reviews to graph content. INPUT: Graph. OUTPUT: Canonical SHA-256 digest."""
    return hashlib.sha256(json.dumps(graph,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def table_catalog(dictionary:dict)->list[dict]:
    """PURPOSE: Normalize tables object/array layouts. INPUT: Public DD. OUTPUT: Table records; no mutation."""
    raw=dictionary.get("tables",[])
    return [{"table":name,**(meta or {})} for name,meta in raw.items()] if isinstance(raw,dict) else [dict(x) for x in raw if isinstance(x,dict)]

def column_metadata(columns:list[dict])->list[dict]:
    """PURPOSE: Normalize column display fields. INPUT: DD columns. OUTPUT: Records preserving unknown source types."""
    return [{"name":c.get("name") or c.get("column"),"source_type":c.get("source_type") or c.get("data_type") or c.get("type") or "unknown","storage_type":c.get("storage_type") or c.get("sql_type") or "unknown","definition":c.get("definition") or c.get("description") or "","sample_values":c.get("sample_values",[])} for c in columns]

def base_sql_type(value:Any)->str|None:
    """PURPOSE: Parse SQL declarations. INPUT: Type with modifiers/brackets or None. OUTPUT: Uppercase base type or None."""
    if value is None or not str(value).strip(): return None
    text=str(value).strip().upper(); text=re.sub(r'^[\[\"`]([^\]\"`]+)[\]\"`]',r'\1',text); match=re.match(r'[A-Z][A-Z0-9_ ]*',text)
    return match.group(0).strip().split()[0] if match else None

def temporal_candidates(table:dict)->list[dict]:
    """PURPOSE: Screen temporal columns without assigning meaning. INPUT: Table DD. OUTPUT: Structural candidates."""
    return [c for c in column_metadata(table.get("columns",[])) if {base_sql_type(c["source_type"]),base_sql_type(c["storage_type"])}&TEMPORAL_TYPES]

def readonly_preview(database:Path,table:str,*,limit:int=10,offset:int=0)->list[dict]:
    """PURPOSE: Page source rows without writes. INPUT: DB, exact table, bounds. OUTPUT: Row mappings; rejects invalid input."""
    if not 1<=limit<=200 or offset<0: raise ValueError("Preview limit must be 1..200 and offset non-negative")
    con=sqlite3.connect(f"file:{database.resolve()}?mode=ro&immutable=1",uri=True)
    try:
        names={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if table not in names: raise ValueError(f"Unknown table: {table}")
        quoted='"'+table.replace('"','""')+'"'; cur=con.execute(f"SELECT * FROM {quoted} LIMIT ? OFFSET ?",(limit,offset)); fields=[x[0] for x in cur.description]
        return [dict(zip(fields,row)) for row in cur.fetchall()]
    finally: con.close()

def _node(identifier,kind,label,payload,status="unknown"):
    """PURPOSE: Create a lossless reviewer node. INPUT: Identity/type/label/native evidence/status. OUTPUT: Node."""
    return {"id":identifier,"type":kind,"label":label,"status":status,"evidence":payload}

def adapt_native_graph(native:dict)->dict:
    """PURPOSE: Adapt genuine native Step 1 output. INPUT: Native graph. OUTPUT: Multi-type graph plus untouched native graph."""
    nodes=[]; edges=[]; ids=set()
    for item in native.get("physical_schema") or native.get("tables",[]):
        name=item.get("name") or item.get("table"); identifier=f"table:{name}"; nodes.append(_node(identifier,"table",name,item,item.get("status","observed"))); ids.add(identifier)
    for item in native.get("entity_types") or native.get("concepts",[]):
        identifier=str(item.get("id")); nodes.append(_node(identifier,"entity_type",item.get("display_name") or item.get("name") or identifier,item,item.get("semantic_status") or item.get("validation_status","unknown"))); ids.add(identifier)
        for table in item.get("member_tables",[]): edges.append({"id":f"membership:{table}:{identifier}","source":f"table:{table}","target":identifier,"type":"candidate_entity_membership","status":item.get("semantic_status","unknown"),"evidence":item})
    for item in native.get("identification_rules",native.get("identification_targets",[])):
        identifier=str(item.get("id") or item.get("rule_id")); target=item.get("entity_type_id") or item.get("concept_id"); table=item.get("table") or item.get("source_table"); nodes.append(_node(identifier,"identification_rule",item.get("description") or identifier,item,item.get("validation_status","unknown"))); ids.add(identifier)
        if table: edges.append({"id":f"id-source:{identifier}","source":f"table:{table}","target":identifier,"type":"identification_source","status":item.get("validation_status","unknown"),"evidence":item})
        if target: edges.append({"id":f"id-target:{identifier}","source":identifier,"target":str(target),"type":"identifies","status":item.get("validation_status","unknown"),"evidence":item})
    for item in native.get("bindings",[]):
        identifier=str(item.get("id")); label=item.get("activity_label") or item.get("alpha",{}).get("name") or identifier; table=item.get("table") or item.get("source_table"); status=item.get("extraction_status") or item.get("interpretation_status") or item.get("validation_status","unknown"); nodes.append(_node(identifier,"event_definition",label,item,status)); ids.add(identifier)
        if table: edges.append({"id":f"event-source:{identifier}","source":f"table:{table}","target":identifier,"type":"event_source","status":status,"evidence":item})
    for i,item in enumerate(native.get("references",native.get("relations",[]))):
        source=item.get("child_table") or item.get("left_table"); target=item.get("parent_table") or item.get("right_table")
        if source and target: edges.append({"id":str(item.get("id") or f"reference:{i}"),"source":f"table:{source}","target":f"table:{target}","type":"physical_reference","status":item.get("validation_status") or item.get("candidate_status","observed"),"evidence":item})
    for i,item in enumerate(native.get("attribution_paths",[])+native.get("binding_object_associations",[])):
        identifier=str(item.get("id") or f"attribution:{i}"); binding=item.get("binding_id") or item.get("event_definition_id"); target=item.get("entity_type_id") or item.get("concept_id") or item.get("target_concept_id"); status=item.get("validation_status","unknown"); nodes.append(_node(identifier,"attribution_rule",identifier,item,status)); ids.add(identifier)
        if binding: edges.append({"id":f"attr-event:{identifier}","source":str(binding),"target":identifier,"type":"attribution_source","status":status,"evidence":item})
        if target: edges.append({"id":f"attr-target:{identifier}","source":identifier,"target":str(target),"type":"attributes_to","status":status,"evidence":item})
    graph={"schema_version":"nl2eventlog-review-eeg-v1","source":"actual_step1_runtime","dataset":native.get("dataset"),"nodes":nodes,"edges":[e for e in edges if e["source"] in ids and e["target"] in ids],"unresolved":native.get("unresolved_temporal_units",[]),"native_graph":native}
    error=validate_graph(graph)
    if error: raise ValueError(error)
    return graph

def validate_graph(graph:Any)->str|None:
    """PURPOSE: Validate graph identities and edges. INPUT: Decoded JSON. OUTPUT: Error or None."""
    if not isinstance(graph,dict): return "EEG JSON must be an object."
    nodes,edges=graph.get("nodes"),graph.get("edges")
    if not isinstance(nodes,list) or not isinstance(edges,list): return "EEG requires nodes[] and edges[]."
    identifiers=[n.get("id") for n in nodes if isinstance(n,dict)]
    if len(identifiers)!=len(nodes) or any(not isinstance(x,str) or not x for x in identifiers): return "Every EEG node must have a nonempty string id."
    if len(set(identifiers))!=len(identifiers): return "Duplicated EEG node ids."
    node_ids=set(identifiers); edge_ids=set()
    for edge in edges:
        if not isinstance(edge,dict) or edge.get("source") not in node_ids or edge.get("target") not in node_ids: return "Every EEG edge must connect existing node IDs."
        if not edge.get("id") or edge["id"] in edge_ids: return "Every EEG edge must have a unique id."
        edge_ids.add(edge["id"])
    return None

def reviewer_patch(graph:dict,dataset:str,reviewer:str,decisions:list[dict],reviewed_at:str)->dict:
    """PURPOSE: Create separate review patch. INPUT: Graph, identity, decisions, ISO time. OUTPUT: Versioned hash-bound patch."""
    return {"schema_version":"nl2eventlog-review-patch-v1","dataset":dataset,"graph_sha256":graph_hash(graph),"reviewer":reviewer,"reviewed_at":reviewed_at,"decisions":decisions}
