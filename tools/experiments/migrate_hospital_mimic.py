#!/usr/bin/env python3
"""Deterministic HospitalFlow MIMIC-inspired structural migration and Gold rebuild.

The records are wholly synthetic. No MIMIC-IV patient-level records are imported.
Run on the previously committed HospitalFlow snapshot; do not re-run on migrated DB.
All source and answer files are validated before publishing changes.
"""
from __future__ import annotations
import csv, io, json, re, sqlite3, hashlib, shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"datasets/hospitalflow"
P=BASE/"private"
E=BASE/"evaluation"
REVIEW=BASE/"review"
ISO="%Y-%m-%dT%H:%M:%SZ"

def load_json(p):return json.loads(p.read_text())
def save_json(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+"\n")
def load_jl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def save_jl(p,items):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text("".join(json.dumps(v,ensure_ascii=False)+"\n" for v in items))
def stamp(s):return datetime.strptime(s,ISO) if s else None
def iso(t):return t.strftime(ISO) if t else None
def q(x):return '"'+x.replace('"','""')+'"'
def table_count(db,name):return db.execute("SELECT COUNT(*) FROM "+q(name)).fetchone()[0]

# Authoritative SQL snippets for the evaluation Gold compiler.
OLD_PROFILE="SELECT 'PAT:'||subject_id||':profile' event_id,'P:'||subject_id object_id,'Patient Profile Verified' activity,profile_verified_at timestamp FROM patient_profile WHERE profile_verified_at IS NOT NULL AND (1=1)"
OLD_AUTH="SELECT 'ADM:'||hadm_id||':auth' event_id,'A:'||hadm_id object_id,'Discharge Authorized' activity,discharge_authorized_at timestamp FROM admissions WHERE discharge_authorized_at IS NOT NULL AND (1=1)"
NEW_EDOUT="SELECT 'ADM:'||hadm_id||':edout' event_id,'A:'||hadm_id object_id,'Emergency Department Departed' activity,edouttime timestamp FROM admissions WHERE edouttime IS NOT NULL AND (1=1)"
NEW_TRANSFER="SELECT 'TR:'||transfer_id event_id,'A:'||hadm_id object_id,'Care Unit Transferred' activity,intime timestamp FROM transfers WHERE hadm_id IS NOT NULL AND eventtype='transfer' AND intime IS NOT NULL"
EXISTING_OUT="SELECT 'ADM:'||hadm_id||':out' event_id,'A:'||hadm_id object_id,'Hospital Discharged' activity,dischtime timestamp FROM admissions WHERE dischtime IS NOT NULL AND (1=1)"

def migrate_db():
    dbpath=BASE/"input/database.sqlite"
    db=sqlite3.connect(dbpath)
    db.row_factory=sqlite3.Row
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "patient_profile" in tables and "transfers" not in tables,"Migration already applied / unexpected input"
    profiles={r["subject_id"]:dict(r) for r in db.execute("SELECT * FROM patient_profile")}
    admissions=[dict(r) for r in db.execute("SELECT * FROM admissions ORDER BY hadm_id")]
    assert len(admissions)==15 and table_count(db,"patients")==12
    assert db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
    db.execute("PRAGMA foreign_keys=OFF")
    db.execute("""CREATE TABLE patients_mimic(
        subject_id INTEGER PRIMARY KEY NOT NULL,
        gender TEXT NOT NULL CHECK(gender IN ('F','M')),
        anchor_age INTEGER NOT NULL CHECK(anchor_age BETWEEN 0 AND 91),
        anchor_year INTEGER NOT NULL,
        anchor_year_group TEXT NOT NULL,
        dod TEXT
    )""")
    patients=[dict(r) for r in db.execute("SELECT * FROM patients ORDER BY subject_id")]
    first_admit={r["subject_id"]:r["admittime"] for r in admissions}
    death_patients=set()
    for i,p in enumerate(patients):
        adt=first_admit.get(p["subject_id"],"2026-01-01T00:00:00Z")
        year=int(adt[:4]);age=22+(i*7)%62
        group=["2011 - 2013","2014 - 2016","2017 - 2019"][i%3]
        # Do not fabricate a death just to fill an optional patient field.
        db.execute("INSERT INTO patients_mimic VALUES(?,?,?,?,?,NULL)",
                   (p["subject_id"],p["gender"],age,year,group))
    db.execute("""CREATE TABLE admissions_mimic(
        hadm_id INTEGER PRIMARY KEY NOT NULL,
        subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
        admittime TEXT NOT NULL,
        dischtime TEXT,
        deathtime TEXT,
        admission_type TEXT NOT NULL,
        admit_provider_id TEXT,
        admission_location TEXT,
        discharge_location TEXT,
        insurance TEXT,
        language TEXT,
        marital_status TEXT,
        race TEXT,
        edregtime TEXT,
        edouttime TEXT,
        hospital_expire_flag INTEGER NOT NULL DEFAULT 0 CHECK(hospital_expire_flag IN (0,1)),
        CHECK(dischtime IS NULL OR admittime<=dischtime),
        CHECK(edouttime IS NULL OR edregtime IS NOT NULL),
        CHECK(edouttime IS NULL OR edregtime<=edouttime)
    )""")
    for i,a in enumerate(admissions):
        edt=stamp(a["edregtime"]);admit=stamp(a["admittime"])
        edout=None
        if edt:
            delta=admit-edt
            edout=edt+delta*0.8 if delta.total_seconds()>=0 else admit
        # All records remain synthetic and no death information is invented.
        db.execute("""INSERT INTO admissions_mimic
          (hadm_id,subject_id,admittime,dischtime,deathtime,admission_type,admit_provider_id,
           admission_location,discharge_location,insurance,language,marital_status,race,
           edregtime,edouttime,hospital_expire_flag)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (a["hadm_id"],a["subject_id"],a["admittime"],a["dischtime"],None,
           ["EW EMER.","DIRECT EMER.","URGENT","ELECTIVE"][i%4],
           f"PV{(i%5)+1:04d}",["EMERGENCY ROOM","PHYSICIAN REFERRAL","CLINIC REFERRAL"][i%3],
           "HOME" if a["dischtime"] else None,["Medicare","Medicaid","Other"][i%3],
           ["ENGLISH","SPANISH"][i%2],["SINGLE","MARRIED","UNKNOWN"][i%3],
           ["WHITE","BLACK/AFRICAN AMERICAN","ASIAN","OTHER"][i%4],
           a["edregtime"],iso(edout),0))
    db.execute("""CREATE TABLE transfers(
        subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
        hadm_id INTEGER REFERENCES admissions(hadm_id),
        transfer_id INTEGER PRIMARY KEY NOT NULL,
        eventtype TEXT CHECK(eventtype IN ('ed','admit','transfer','discharge')),
        careunit TEXT,
        intime TEXT,
        outtime TEXT,
        CHECK(outtime IS NULL OR intime IS NULL OR intime<=outtime)
    )""")
    transfer_rows=[]
    tid=80000000
    for i,a in enumerate(admissions):
        admitted=stamp(a["admittime"]);end=stamp(a["dischtime"])
        if end is not None and end<=admitted:raise AssertionError("Nonpositive admission length")
        if end: move=admitted+(end-admitted)*0.45
        else: move=admitted+timedelta(hours=6+i%5)
        # Every 3rd stay has no transfer event. Other stays have one valid move.
        do_move=(i%3!=2) and (end is None or (end-admitted).total_seconds()>4*3600)
        tid+=1
        transfer_rows.append((a["subject_id"],a["hadm_id"],tid,"admit","Medical Ward",iso(admitted),iso(move if do_move else end)))
        if do_move:
            tid+=1
            transfer_rows.append((a["subject_id"],a["hadm_id"],tid,"transfer",
                                  ["Surgical Ward","Step-Down Unit","Medical ICU"][i%3],iso(move),iso(end)))
        if end:
            tid+=1
            transfer_rows.append((a["subject_id"],a["hadm_id"],tid,"discharge",None,iso(end),None))
    db.executemany("INSERT INTO transfers VALUES(?,?,?,?,?,?,?)",transfer_rows)
    # Replacing parents requires disabling FKs until both original tables are gone.
    db.execute("DROP TABLE patient_profile")
    db.execute("DROP TABLE patients")
    db.execute("ALTER TABLE patients_mimic RENAME TO patients")
    db.execute("DROP TABLE admissions")
    db.execute("ALTER TABLE admissions_mimic RENAME TO admissions")
    # SQLite can retarget child FKs on parent rename in version-dependent ways.
    # Ensure the original user-facing SQL schema has no temporary table references.
    fk_violations=list(db.execute("PRAGMA foreign_key_check"))
    if fk_violations:raise AssertionError("Broken FKs: "+str(fk_violations[:12]))
    if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise AssertionError("SQLite integrity failed")
    # Check that child FKs do not point to the replaced temporary names.
    refs=[(t[0],r[2]) for t in db.execute("SELECT name FROM sqlite_master WHERE type='table'") for r in db.execute("PRAGMA foreign_key_list("+q(t[0])+")")]
    assert not any("mimic" in dest for _,dest in refs),refs
    db.commit()
    db.execute("PRAGMA foreign_keys=ON")
    assert not list(db.execute("PRAGMA foreign_key_check"))
    assert table_count(db,"transfers")==len(transfer_rows)
    return db,transfer_rows

def migrate_dd(db):
    dd=load_json(BASE/"input/data_dictionary.json")
    profile=next(t for t in dd["tables"] if t["table"]=="patient_profile")
    dd["tables"]=[t for t in dd["tables"] if t["table"]!="patient_profile"]
    def column(table,name,definition,datatype,eventtime=False,nullable=True):
        return dict(metadata_id="hospitalflow."+table+"."+name,name=name,readable_name=name.replace("_"," ").title(),
          definition=definition,type=datatype,representation_class="Date-time" if eventtime else ("Integer" if datatype=="INTEGER" else "Text"),
          format="RFC 3339 UTC text, YYYY-MM-DDTHH:MM:SSZ" if eventtime else datatype,
          timezone="UTC" if eventtime else None,nullable=nullable,required=not nullable,
          source_references=["Synthetic HospitalFlow; MIMIC-IV hosp schema names (not MIMIC patient records)"],
          code_meanings={},foreign_keys=[])
    for t in dd["tables"]:
        if t["table"]=="patients":
            t["definition"]="MIMIC-IV-compatible patient demographics and anchor metadata (synthetic)."
            t["columns"]+= [
              column("patients","anchor_age","Age in synthetic anchor_year; not an event.", "INTEGER",nullable=False),
              column("patients","anchor_year","Synthetic de-identified reference year.", "INTEGER",nullable=False),
              column("patients","anchor_year_group","Approximate original-year group (synthetic).", "TEXT",nullable=False),
              column("patients","dod","Date of death if known; not an assumed process event.","TEXT")]
        if t["table"]=="admissions":
            t["columns"]=[c for c in t["columns"] if c["name"]!="discharge_authorized_at"]
            t["columns"] += [
             column("admissions","deathtime","Actual death timestamp if observed during this admission; NULL in current synthetic cohort.","TEXT",True),
             column("admissions","edouttime","Time the patient departed the emergency department, as in MIMIC-IV.","TEXT",True),
             column("admissions","admission_type","Type of admission; administrative attribute, not event.","TEXT",nullable=False),
             column("admissions","admit_provider_id","Admission provider reference.","TEXT"),
             column("admissions","admission_location","Location from which admission occurred.","TEXT"),
             column("admissions","discharge_location","Discharge destination.","TEXT"),
             column("admissions","insurance","Recorded payor category.","TEXT"),
             column("admissions","language","Admission-level language preference, not a patient master attribute.","TEXT"),
             column("admissions","marital_status","Marital status at admission.","TEXT"),
             column("admissions","race","Recorded demographic classification at admission.","TEXT"),
             column("admissions","hospital_expire_flag","Whether death occurred during admission (all zero in synthetic sample).","INTEGER",nullable=False)]
            t["definition"]="Synthetic hospital stay using original MIMIC-IV admissions time-column names."
    transfers=dict(table="transfers",metadata_id="hospitalflow.transfers",readable_name="Hospital Transfers",
      definition="One patient physical-location interval per record, following the MIMIC-IV transfers table shape.",
      row_grain="One admission, ward transfer, or discharge location interval.",
      primary_key=["transfer_id"],
      foreign_keys=[dict(columns=["subject_id"],referenced_table="patients",referenced_columns=["subject_id"]),
                    dict(columns=["hadm_id"],referenced_table="admissions",referenced_columns=["hadm_id"])],
      logical_relationships=[],columns=[
        column("transfers","subject_id","Patient whose physical-location history this record describes.","INTEGER",nullable=False),
        column("transfers","hadm_id","Hospital admission associated with this location interval.","INTEGER"),
        column("transfers","transfer_id","Unique location record identifier.","INTEGER",nullable=False),
        column("transfers","eventtype","ed, admit, transfer or discharge interval type. Only transfer is a distinct transfer activity.","TEXT"),
        column("transfers","careunit","Care unit occupied during this location interval.","TEXT"),
        column("transfers","intime","Actual entry time into the recorded care unit.","TEXT",True),
        column("transfers","outtime","Actual departure time from the recorded care unit.","TEXT",True)])
    dd["tables"].append(transfers)
    defs={r["name"]:r["sql"] for r in db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'")}
    for t in dd["tables"]:
        t["sql_definition"]=defs[t["table"]]
        info={r["name"]:r for r in db.execute("PRAGMA table_info("+q(t["table"])+")")}
        assert {c["name"] for c in t["columns"]}==set(info),(t["table"],set(info)-{c["name"] for c in t["columns"]})
        for col in t["columns"]:
            x=info[col["name"]];col["primary_key_position"]=x["pk"];col["nullable"]=not (x["notnull"] or x["pk"]);col["required"]=not col["nullable"]
    dd["business_rules"]=[x for x in dd.get("business_rules",[]) if "patient_profile" not in x.lower() and "discharge_authorized" not in x.lower()]
    dd["business_rules"].extend([
      "MIMIC-IV-inspired structure with wholly synthetic patients and movements; no original patient record is used.",
      "Patient demographics live only in patients, with admission-specific attributes in admissions.",
      "An interval in transfers is not automatically a separate event for every time column: eventtype=transfer at intime records the care-unit transfer; admit and discharge intervals duplicate admission milestones.",
      "An ED departure event uses admissions.edouttime; admission approval is not inferred. Null deathtime/dod are not events."
    ])
    save_json(BASE/"input/data_dictionary.json",dd)
    return dd

def migrate_gold(db):
    gold=load_jl(P/"gold.jsonl")
    changes={"Discharge Authorized":"Emergency Department Departed","Patient Profile Verified":"Care Unit Transferred"}
    # Keep activity labels semantically distinct; only the two superseded types are repurposed.
    def rewrite_sql(old):
        assert OLD_PROFILE in old and OLD_AUTH in old,"Unexpected legacy SQL compilation"
        sql=old.replace(" UNION ALL "+OLD_PROFILE,"").replace(" UNION ALL "+OLD_AUTH,"")
        assert "patient_profile" not in sql and "discharge_authorized_at" not in sql
        assert EXISTING_OUT in sql
        sql=sql.replace(EXISTING_OUT,EXISTING_OUT+" UNION ALL "+NEW_EDOUT+" UNION ALL "+NEW_TRANSFER)
        # Only the WHERE activity selector remains in the old vocabulary.
        sql=sql.replace("'Discharge Authorized'","'Emergency Department Departed'")
        sql=sql.replace("'Patient Profile Verified'","'Care Unit Transferred'")
        if "'Care Unit Transferred'" not in sql:raise AssertionError("New transfer binding missing")
        return sql
    for g in gold:
        if g.get("answerability")!="answerable":continue
        gid=g["question_id"]
        es=g["es"]
        sql=rewrite_sql(es["compiled_sql"])
        if gid in ("HF01","HF01P","HF02","HF02P"):
            sql=sql.replace("'Emergency Department Departed','Discharge Summary Signed'",
                            "'Care Unit Transferred','Emergency Department Departed','Discharge Summary Signed'")
        # Already changed the label in the original profile selector for HF01.
        es["compiled_sql"]=sql
        es["version"]="hospital-mimic-transfers-2"
        es["activities"]=list(dict.fromkeys(changes.get(a,a) for a in es.get("activities",[])))
        sources=[source for source in es.get("activity_sources",[]) if source["activity"] not in changes]
        existing={s["activity"] for s in sources}
        for activity,table,col,source_sql in [
          ("Emergency Department Departed","admissions","edouttime",NEW_EDOUT),
          ("Care Unit Transferred","transfers","intime",NEW_TRANSFER)]:
            if activity in es["activities"] and activity not in existing:
                sources.append({"table":table,"activity":activity,"timestamp_column":col,
                                "encoding":"Row encoding" if table=="transfers" else "Column encoding",
                                "event_sql":source_sql})
        es["activity_sources"]=sources
        for field in ("requested_activities",):
            if field in g and isinstance(g[field],list):
                g[field]=list(dict.fromkeys(changes.get(a,a) for a in g[field]))
        if "process_view" in g and isinstance(g["process_view"],dict):
            pv=g["process_view"]
            if "activities" in pv:pv["activities"]=list(dict.fromkeys(changes.get(a,a) for a in pv["activities"]))
        actual=list(db.execute(sql))
        assert len(actual)==len({(r[0],r[1]) for r in actual}),"Duplicate event_id/case in "+gid
        assert all(len(r)==4 for r in actual)
        rows=[tuple("" if v is None else str(v) for v in r) for r in actual]
        # Preserve SQL's deterministic order.
        path=P/"gold_logs"/(gid+".csv")
        with path.open("w",newline="") as f:
            out=csv.writer(f);out.writerow(["event_id","case_id","activity","timestamp"]);out.writerows(rows)
        (P/"gold_sql"/(gid+".sql")).write_text(sql.rstrip()+"\n")
        g["event_count"]=len(rows)
        g["case_count"]=len({r[1] for r in rows})
        g["requested_activity_count"]=len(es["activities"])
        g["extractable_activity_count"]=len(es["activities"])
    save_jl(P/"gold.jsonl",gold)
    for name in ["questions.jsonl","model_questions.jsonl"]:
        f=E/name
        if not f.exists():continue
        qs=load_jl(f)
        for x in qs:
            id=x.get("question_id") or x.get("id")
            question=x.get("text") or x.get("question") or ""
            if id in ("H06","H06P"):
                question=question.replace("Discharge Authorized","Emergency Department Departed")
                question=question.replace("authorization to leave","departure from the emergency department")
            if id in ("H09","H09P"):
                question=("For each patient, extract Care Unit Transferred events."
                          if id=="H09" else "Show when each patient moved to a different hospital care unit.")
            if id in ("HF01","HF01P","HF02","HF02P"):pass
            for k in ("question","text"):
                if k in x:x[k]=question
            if "requested_activities" in x:
                x["requested_activities"]=[changes.get(a,a) for a in x["requested_activities"]]
        save_jl(f,qs)
    # Informal review descriptions are rewritten separately below.
    return gold

def gold_validate(db,gold):
    total=0
    for g in gold:
        if g.get("answerability")!="answerable":continue
        id=g["question_id"]
        csvfile=P/"gold_logs"/(id+".csv")
        with csvfile.open(newline="") as f:
            reader=csv.reader(f);header=next(reader);expected=list(reader)
        assert header==["event_id","case_id","activity","timestamp"]
        sql=(P/"gold_sql"/(id+".sql")).read_text()
        rows=[[str(v) if v is not None else "" for v in r] for r in db.execute(sql)]
        assert rows==expected,(id,"Gold SQL mismatch",len(rows),len(expected))
        assert len(rows)==g["event_count"]
        total+=1
    return total
