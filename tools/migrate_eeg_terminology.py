#!/usr/bin/env python3
"""Align public dataset documentation with the target EEG/ET/ER methodology.

Never changes SQLite, SQL, Gold CSV, model-visible dictionaries or question texts.
Existing Gold grouping is explicitly legacy until semantics and namespaces are reviewed.
"""
from __future__ import annotations
import json
import re
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAMES=("hospitalflow","plateflow","universityflow","warehouseflow")
DISPLAY={"hospitalflow":"HospitalFlow","plateflow":"PlateFlow","universityflow":"UniversityFlow","warehouseflow":"WarehouseFlow"}
TARGET_NOTE=("The diagram is an **author-annotated EEG source projection**, not a model-inferred EEG or "
             "a validated namespace-aware Entity Type Gold. The ET candidates reflect legacy identity labels.")
CASE_NOTE=("A physical table is one **Entity Representation (ER)**. Its displayed **Entity Type (ET) candidate** "
           "comes from legacy Gold annotations. ET semantic grouping and cross-ER instance identity "
           "resolution must be validated independently. FK reachability alone does not establish "
           "Case Attribution or Lifecycle Membership.")

def write_if_changed(p,text):
    old=p.read_text() if p.exists() else None
    if old!=text:
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(text)
        return True
    return False

def replacements(text):
    changes=[
      ("Gold Object Types → Physical Tables → Activities","Entity Types → Entity Representations → Activities"),
      ("Gold Object Types","Legacy Entity Type candidates"),
      ("Gold object types","legacy Entity Type candidates"),
      ("Gold Object Type","Entity Type candidate"),
      ("Gold object type","entity type candidate"),
      ("Gold OTs","legacy ET candidates"),
      ("Gold OT","legacy ET candidate"),
      ("OT membership","ET candidate membership"),
      ("OT group","ET candidate group"),
      ("Object Types (left)","Entity Types (left)"),
      ("Object Types","Entity Types"),
      ("Object Type","Entity Type"),
      ("Gold Evidence Graph","Gold EEG Source Projection"),
      ("Gold Evidence Structure","Gold EEG Source Projection"),
      ("Evidence Graph","Event Extraction Graph"),
      ("Physical Tables (middle)","Entity Representations (middle)"),
      ("Physical Tables","Entity Representations"),
    ]
    for before,after in changes:text=text.replace(before,after)
    return text

def update_readme(path,n,level):
    s=path.read_text()
    s=replacements(s)
    # Replace assumptions that source-table membership itself proves ET semantics/identity.
    s=re.sub(r"Each physical table belongs to exactly one[^.]*\.",CASE_NOTE,s)
    s=re.sub(r"One identity OT per physical table[^.]*\.",CASE_NOTE,s)
    s=re.sub(r"\*\*This is an author-annotated Gold source projection, not an inferred Event Extraction Graph or a full provenance graph\.\*\*",TARGET_NOTE,s)
    s=re.sub(r"\*\*This is an author-annotated Gold source projection, not an inferred Evidence Graph or a full provenance graph\.\*\*",TARGET_NOTE,s)
    s=s.replace("The diagram distinguishes core business object concepts from supporting entities and activity-record types.",
                "The diagram distinguishes core entity concepts from supporting representations and occurrence records.")
    s=s.replace("An event can be associated with several business objects through foreign keys without its source table belonging to multiple OTs.",
                "An event may be attributed to several Entity Instances without implying that its source ER belongs to multiple ETs.")
    s=s.replace("The core set is a conceptual layer for interpreting process scope, not a rule that forces unrelated PK domains to merge.",
                "The core set is a conceptual shortlist, not evidence for merging separate Entity Instances or Identity Namespaces.")
    s=s.replace("Object types identify business entities or independent occurrence records. The conceptual shortlist of core nouns is not a physical schema transformation.",
                "Entity Types capture business semantics; Entity Representations preserve physical tables. ET classification is separate from instance identity resolution.")
    s=re.sub(r"Gold identity types: \*\*(\d+)\*\*",r"Legacy ET candidate groups: **\1**",s)
    s=s.replace("Gold SQL and record-level evidence are available in the linked inspection materials.",
                "Gold SQL and record-level evidence are available in the linked inspection materials; their internal consistency does not validate the target namespace model.")
    if level=="dataset":
        note="\n## Entity-model interpretation\n\n"+CASE_NOTE+" See the [EEG / ET / ER methodology](../../docs/system/EEG_ENTITY_MODEL.md) for the target semantics.\n"
        if "## Entity-model interpretation" not in s:s=s.rstrip()+"\n"+note
    elif level=="database":
        note="\n\n**Entity-model status:** "+CASE_NOTE+" [Terminology and namespace contract](../../../../docs/system/EEG_ENTITY_MODEL.md).\n"
        if "**Entity-model status:**" not in s:
            marker="## Relational Schema"
            if marker in s:s=s.replace(marker,note+"\n"+marker,1)
            else:s=s.rstrip()+note
    return write_if_changed(path,s)

def edit_svg(path):
    s=path.read_text()
    original=s
    subs=[
       ("Gold Evidence Structure","EEG Source Projection"),
       ("Gold OT membership is unique per physical table.","Every table is an ER; labels are provisional legacy ET candidates."),
       ("Gold OT","Legacy ET candidate"),
       ("Object Types (left)","Entity Types (left)"),
       ("Physical Tables (middle)","Entity Representations (middle)"),
       ("Core business object","Core business entity"),
       ("Supporting/record object","Supporting/record ER"),
       ("Gold Activity Sources (right)","Activity Source Bindings (right)"),
       ("No cross-OT mergers are inferred from foreign keys.","FK associations do not establish shared Entity Instance identity."),
       ('aria-label="Gold OT left, physical tables middle and source activities right"',
        'aria-label="Entity Type candidates left, physical Entity Representations middle and source activities right"'),
    ]
    for old,new in subs:s=s.replace(old,new)
    if s==original:
        # Some diagrams already use the final labels; do not force extra modification.
        return False
    return write_if_changed(path,s)

def candidate_manifest(base,n):
    original=json.loads((base/"review/gold_dfg/gold_source_manifest.json").read_text())
    db=sqlite3.connect(f"file:{base/'input/database.sqlite'}?mode=ro",uri=True)
    es=[]
    for t,d in original["tables"].items():
        pk=[r[1] for r in db.execute('PRAGMA table_info("'+t.replace('"','""')+'")') if r[5]]
        assert pk,(n,t,"no primary key")
        ns=f"{n}:{t}"
        status="unreviewed"
        if n=="hospitalflow" and t in ("admissions","admission_detail"):
            ns="hospitalflow:admission:hadm_id"
            status="shared_primary_key_fk_supported"
        es.append({"er":t,"candidate_entity_type":d["ot"],"primary_key":pk,
            "identity_namespace":ns,"namespace_evidence_status":status,
            "semantic_et_validation":"pending",
            "source_activity_labels":d["activities"],"source_time_columns":d["timestamps"]})
    db.close()
    grouped={}
    for row in es:
        grouped.setdefault(row["candidate_entity_type"],[]).append(row["er"])
    doc={
       "dataset":n,
       "model":"Target EEG schema; provisional migration of pre-namespace Gold annotation",
       "status":"candidate_only_not_validated_ET_gold",
       "one_entity_representation_per_physical_table":True,
       "identity":"Entity ID = (Entity Type, Identity Namespace, Canonical Key)",
       "default_directional_case_attribution":"FK_to_referenced_PK_or_unique_only_when_validated",
       "default_reverse_fk_traversal":False,
       "identity_mapping_policy":"Shared/Mapped/Independent/Unknown require separate verified evidence",
       "case_population_policy":"distinct union of validated ET instance mappings; not computed in this review",
       "lifecycle_membership_policy":"separate evidence required; never inferred from FK alone",
       "entity_representations":es,"candidate_entity_types":grouped,
       "explanation":"This metadata is for reviewer comparison; do not pass it to models or treat it as reviewed semantic ET Gold."
    }
    return write_if_changed(base/"review/gold_dfg/entity_model_candidates.json",json.dumps(doc,indent=2,ensure_ascii=False)+"\n")

def review_inventory(path):
    s=path.read_text()
    s=replacements(s)
    s=s.replace("**Author annotations.** One identity OT per physical table; event-to-object attribution is a separate relation.",
                "**Legacy author annotations.** Every physical table is an ER. Candidate ET grouping is not yet validated for Identity Namespaces or lifecycle membership.")
    s=s.replace("One identity OT per physical table; event-to-object attribution is a separate relation.",
                "One ER per physical table; event-to-entity attribution is a separate relation.")
    s=s.replace("The model is not given this file.","This is a reviewer-only candidate grouping and is not provided to the model.")
    if "entity_model_candidates.json" not in s:
        s+="\n[Entity Representation and namespace candidates](entity_model_candidates.json) — review-only; **not validated semantic ET Gold**.\n"
    return write_if_changed(path,s)

def editorial_docs(base,n):
    changed=0
    docs=[
      "docs/object_type_verification.md",
      "docs/object_activity_design.md",
      "docs/schema_overview.md",
      "docs/realism_review.md",
      "design/plan.md",
    ]
    for sub in docs:
        p=base/sub
        if not p.exists():continue
        s=p.read_text()
        before=s
        s=replacements(s)
        s=s.replace("A physical table belongs to exactly one OT. Do not conflate FK associations with equal business-object identity.",
                    CASE_NOTE)
        s=s.replace("**Decision:** Keep 11 OTs. Merge only admissions with admission_detail.",
                    "**Legacy annotation:** 11 identity groups; only admissions and admission_detail share a supported primary-key identity. Semantic ET group review may regroup different entity populations without merging instances.")
        s=s.replace("Clinical grouping in the diagram is presentation only, not an ontology merge.",
                    "Domain grouping is visual only, not evidence of semantic ET equality or shared instance identity.")
        if before!=s:changed+=write_if_changed(p,s)
    return changed

def root_readme():
    p=ROOT/"README.md"
    s=p.read_text()
    s=s.replace("Research implementation and four evaluation datasets for natural-language-to-event-log extraction.",
       "Research implementation and four evaluation datasets for natural-language-to-event-log extraction. The target method uses **Entity Types (ETs)**, physical-table **Entity Representations (ERs)**, **Identity Namespaces**, and a request-independent **Event Extraction Graph (EEG)**.")
    s=s.replace("- [System design](docs/system/)",
       "- [EEG / ET / ER target methodology](docs/system/EEG_ENTITY_MODEL.md)\n- [System design](docs/system/)")
    s=re.sub(r"PlateFlow and WarehouseFlow refer to the former.*?\n\n","",s,flags=re.S)
    note="\n**Evaluation migration status:** the stored Gold SQL/CSV, legacy identity groups, and case semantics predate the namespace-aware ET redesign. Gold SQL/CSV consistency is verified separately; semantic ET reannotation and FK→PK-only attribution recall remain open validation tasks.\n"
    if "**Evaluation migration status:**" not in s:s=s.rstrip()+"\n"+note
    return write_if_changed(p,s)

def main():
    counts={}
    for n in NAMES:
        base=ROOT/"datasets"/n
        nchanges=0
        nchanges+=update_readme(base/"README.md",n,"dataset")
        nchanges+=update_readme(base/"review/database/README.md",n,"database")
        nchanges+=review_inventory(base/"review/gold_dfg/event_graph.md")
        nchanges+=edit_svg(base/"review/database/gold_evidence_graph.svg")
        nchanges+=candidate_manifest(base,n)
        nchanges+=editorial_docs(base,n)
        counts[n]=nchanges
    counts["root_readme"]=root_readme()
    p=ROOT/"docs/system/DESIGN_METHODOLOGY.md"
    s=p.read_text()
    disclaimer="> The active target terminology and mapping contracts are in [EEG / ET / ER methodology](EEG_ENTITY_MODEL.md). Dataset construction notes below may retain legacy assumptions; they do not establish validated semantic ET groupings or namespace-aware case attribution.\n\n"
    if not s.startswith(disclaimer):write_if_changed(p,disclaimer+s)
    # Assert the scope boundary: the migration's output is review/documentation only.
    for n in NAMES:
        p=ROOT/"datasets"/n/"review/gold_dfg/entity_model_candidates.json"
        doc=json.loads(p.read_text())
        assert doc["status"]=="candidate_only_not_validated_ET_gold"
        assert len(doc["entity_representations"])==len(doc["candidate_entity_types"]) or len(doc["entity_representations"])>len(doc["candidate_entity_types"])
        assert not doc["default_reverse_fk_traversal"]
    print(json.dumps(counts,indent=2))

if __name__=="__main__":main()
