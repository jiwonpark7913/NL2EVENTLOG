"""Query-independent business descriptions for Step 2."""

from src.common.prompt_loader import load_prompt
import hashlib
import json
import re
from src.common.llm_usage import experiment_settings
VERSION = "business-activity-v2"
STORAGE_EXPRESSION = re.compile(r'\b(?:select|column|table|foreign key|primary key|identified by)\b|\b\w+\.\w+\b|\b\w+_\w+\b', re.I)
from src.common.llm_usage import chat_settings


def entry(item, event=False):
    """PURPOSE: Project public semantic fields. INPUT: ET or event. OUTPUT: ID/name/meaning."""
    sem = item.get('activity_semantics') or {}
    fields = ((item.get('meaning_card') or {}).get('activity_meaning'), sem.get('meaning'),
              sem.get('description'), (item.get('semantic_signature') or {}).get('description')) if event else (
              item.get('instance_granularity'), item.get('business_meaning'), item.get('business_definition'))
    return {'id': item['id'], 'name': (item.get('activity_label') or item.get('activity') if event
                                        else item.get('name') or item.get('label')) or '',
            'meaning': next((' '.join(sentence.split()) for x in fields if isinstance(x, str)
                             for sentence in re.split(r'(?<=\.)\s+', x)
                             if sentence.strip() and not STORAGE_EXPRESSION.search(sentence)), '')}


def summary_inventory(graph):
    """PURPOSE: Describe each ET and all attributable activities. INPUT: EEG. OUTPUT: Paragraph and counts."""
    indexed = {e['id']:e for e in graph.get('dbu_rewrite', {}).get('entity_types', [])}
    indexed.update({e['id']:e for e in graph.get('entity_types', graph.get('table_key_records', []))})
    types = list(indexed.values())
    events = {e['id']: e for e in graph.get('event_definitions', [])}
    linked = {e['id']: set() for e in types}
    from src.step2_retrieve_and_interpret.interpret_and_verify_process import attribution_evidence

    # Index once, then use exactly the same forward-path and direct-identity
    # checks as selection. Embedded paths belong to their enclosing definition.
    paths_by_event = {}
    for path in graph.get('attribution_paths', []):
        paths_by_event.setdefault(path.get('event_definition_id'), []).append(path)
    from src.common.event_definition_policy import binding_policy
    for eid, event in events.items():
        if not binding_policy(event,versioned=bool(graph.get('activity_semantics_version')))['history_supported']:
            continue
        local_graph = dict(graph, attribution_paths=paths_by_event.get(eid, []))
        for et in types:
            scopes = [None, *[p['case_role'] for p in paths_by_event.get(eid, [])
                              if p.get('to') == et['id'] and p.get('case_role')]]
            for scope in scopes:
                evidence = attribution_evidence(local_graph, event, et, diagnose=False, case_scope=scope)
                if evidence['status'] == 'pass' and evidence.get('verified_for_history'):
                    linked[et['id']].add(eid)
                    break
    et_map = {'ET'+str(i):et['id'] for i,et in enumerate(sorted(types,key=lambda e:e['id']),1)}
    groups = {}
    for eid in sorted(set().union(*linked.values())):
        event = events[eid]
        groups.setdefault(event.get('canonical_activity_id') or entry(event,True)['name'].casefold(),[]).append(eid)
    activities = {'A'+str(i):ids for i,ids in enumerate(groups.values(),1)}
    members = {et:{a:sorted(linked[target].intersection(ids)) for a,ids in activities.items()
                   if linked[target].intersection(ids)} for et,target in et_map.items()}
    items = {}
    for et,target in et_map.items():
        obj = indexed[target]
        items[et] = {'name':entry(obj)['name'],'evidence':[obj[k] for k in
            ('instance_granularity','business_meaning','business_definition') if obj.get(k)]}
    for a,ids in activities.items():
        evidence = []
        for eid in ids:
            e = events[eid]
            evidence.append(entry(e,True)['meaning'])
            evidence.extend(x.get('text') for x in (e.get('activity_semantics') or {}).get('evidence',[]) if isinstance(x,dict))
        items[a] = {'name':entry(events[ids[0]],True)['name'],'evidence':list(dict.fromkeys(x for x in evidence if x))}
    return et_map,members,items


def eeg_summary(graph,client,model):
    """PURPOSE: Prepare a validated business paragraph during EEG preparation. INPUT: EEG and SDK. OUTPUT: Auditable summary."""
    import tiktoken
    ets,members,items = summary_inventory(graph)
    tables = graph.get('tables',[])
    columns = {c['name'].lower() for t in tables for c in t.get('columns',[]) if isinstance(c,dict) and c.get('name')}
    table_names = {t['name'].lower() for t in tables if t.get('name')}
    collisions, hidden = [], []
    for alias,item in items.items():
        name = item['name'].lower()
        if name in columns or STORAGE_EXPRESSION.search(name):
            hidden.append(alias)
            item['name'] = ''
        elif name in table_names or name+'s' in table_names:
            collisions.append(alias)
    business_words = {word.lower() for item in items.values() for word in re.findall(r'[A-Za-z]+',item['name'])}
    physical_words = (columns|table_names) - business_words
    phrases, problems, usage = {}, [], []
    pending = [a for a in items if items[a]['evidence']]
    for attempt in range(3):
        failed = []
        for offset in range(0,len(pending),25):
            batch = pending[offset:offset+25]
            schema = {'type':'object','properties':{a:{'type':'string'} for a in batch},'required':batch,'additionalProperties':False}
            response = client.chat.completions.create(model=model,**chat_settings(model),response_format={'type':'json_schema',
                'json_schema':{'name':'eeg_business_descriptions','strict':True,'schema':schema}},
                messages=[{'role':'system','content':load_prompt('step1_understand', 'describe_business_entities_and_events')},
                          {'role':'user','content':json.dumps({a:items[a] for a in batch},ensure_ascii=False)}])
            usage.append({'input':response.usage.prompt_tokens,'output':response.usage.completion_tokens})
            try:
                values = json.loads(response.choices[0].message.content or '{}')
            except ValueError:
                values = {}
            for a in batch:
                phrase = values.get(a) if isinstance(values,dict) and not set(values)-set(batch) else None
                words = re.findall(r"\b[\w'-]+\b",phrase or '') if isinstance(phrase,str) else []
                invalid = (not isinstance(phrase,str) or len(words)>(32 if a in ets else 12)
                    or re.search(r'[.!?]\s+\S|\b(?:ET|A)\d+\b',phrase) or STORAGE_EXPRESSION.search(phrase)
                    or any(w.lower() in physical_words for w in words))
                if invalid:
                    problems.append({'attempt':attempt+1,'alias':a,'output':phrase,'reason':
                        'length' if len(words)>(32 if a in ets else 12) else 'physical' if isinstance(phrase,str) and (STORAGE_EXPRESSION.search(phrase) or any(w.lower() in physical_words for w in words)) else 'other'})
                    failed.append(a)
                else:
                    phrases[a] = phrase.strip().rstrip('.')
        pending = failed
        if not pending:
            break
    def label(a):
        """PURPOSE: Render one verified alias. INPUT: Alias. OUTPUT: Business label and optional explanation."""
        return ' '.join(filter(None,[a,items[a]['name'],phrases.get(a)]))
    sentences = [label(et) for et in ets]
    sentences.extend(label(a)+' ('+', '.join(et for et in ets if a in members[et])+')'
                     for a in items if a not in ets)
    paragraph = '. '.join(sentences)+'.'
    content = {k:v for k,v in graph.items() if k not in ('revision_summary','eeg_cache')}
    digest = hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(paragraph=paragraph,et_aliases=ets,members=members,evidence=items,phrases=phrases,
                validation_errors=problems,fallback_aliases=pending,hidden_physical_names=hidden,
                business_table_collisions=collisions,model=model,prompt_version=VERSION,eeg_hash=digest,
                settings=experiment_settings(model),
                cache_key=hashlib.sha256((digest+VERSION+model+json.dumps(experiment_settings(model),sort_keys=True)).encode()).hexdigest(),usage=usage,
                tokens=len(tiktoken.get_encoding('o200k_base').encode(paragraph)))
