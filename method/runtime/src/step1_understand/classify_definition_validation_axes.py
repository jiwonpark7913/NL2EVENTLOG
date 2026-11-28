"""Independent physical rule, event semantics, attribution and case population proof axes."""

from __future__ import annotations
import sqlite3
import re
from src.common.database_io import quote_identifier as qi
from src.common.database_io import connect_readonly
VERSION='eeg-validation-axes-v1'


def attach_validation_axes(graph,key_profiles,db_path=None):
    """PURPOSE: Keep source-rule execution distinct from meaning and target-specific case proof.
    INPUT: Final native EEG, exact key profiles and optional read-only DB path.
    OUTPUT: Independent per-candidate axes and target-indexed attribution/population receipts.
    A successful source projection probe does not assert event meaning, attribution or complete cases.
    """
    times={t['ts_id']:t for t in graph['timestamps']}
    keys={(k['table'],tuple(k['columns'])):k for k in key_profiles}
    objects={o['table']:o for o in graph['objects']}
    concepts={c['id']:c for c in graph.get('concepts',[])}
    connection=connect_readonly(db_path) if db_path else None
    probes={}
    for time in times.values():
        evidence=[e for e in time.get('role_evidence',[]) if e.get('source') in {'dictionary_description','dictionary_event_activity'}]
        text=' '.join(re.split(r'\bnot\b',str(e.get('detail','')),flags=re.I)[0] for e in evidence)
        phases=[phase for phase,pattern in [('start',r'\b(?:start|starting|begin|beginning) (?:occurrence )?time\b'),
            ('completion',r'\b(?:completion|completed|finish|finishing|end|ending) (?:occurrence )?time\b')] if re.search(pattern,text,re.I)]
        time['occurrence_phase']={'status':'supported' if len(phases)==1 else 'ambiguous' if phases else 'unknown',
            'phase':phases[0] if len(phases)==1 else None,'evidence':evidence if phases else []}
    try:
        for event in graph['bindings']:
            table=event['table'];alpha=event['alpha'];time=times.get(event.get('ts_id'),{})
            row_key=list(objects.get(table,{}).get('pk',[]))
            columns=list(dict.fromkeys([*row_key,*time.get('columns',[]),*([alpha['column']] if alpha.get('kind')=='value' else [])]))
            signature=(table,tuple(columns),alpha.get('column') if alpha.get('kind')=='value' else None)
            if signature not in probes:
                probe={'status':'not_run','basis':'no_live_projection_probe'}
                if connection is not None and columns:
                    sql='SELECT '+','.join('source_row.'+qi(c) for c in columns)+' FROM '+qi(table)+' AS source_row'
                    parameters=[]
                    if alpha.get('kind')=='value':sql+=' WHERE source_row.'+qi(alpha['column'])+'=?';parameters=[alpha['value']]
                    sql+=' LIMIT 0'
                    try:
                        connection.execute(sql,parameters).fetchall()
                        probe={'status':'pass','basis':'executed_readonly_source_projection','sql':sql,
                               'scope':'source columns and predicate only; independent of meaning and case selection'}
                    except sqlite3.Error as error:
                        probe={'status':'fail','basis':'source_projection_error','error_type':type(error).__name__}
                probes[signature]=probe
            physical=dict(probes[signature]);key_valid=keys.get((table,tuple(row_key)),{}).get('unique') is True
            format_known=bool(time.get('detected_format') or time.get('source')=='composite')
            physical['occurrence_key_validated']=key_valid;physical['time_format_known']=format_known
            if physical['status']=='pass' and not (key_valid and format_known):physical['status']='unknown'
            checks=event.get('extraction_checks',{})
            semantic_states=[checks.get(k,'unresolved') for k in ('activity','occurrence','time')]
            semantics={'status':'pass' if all(s=='supported' for s in semantic_states) else
                       'fail' if any(s in {'conflicting','rejected','invalid'} for s in semantic_states) else 'unknown',
                       'checks':{k:checks.get(k,'unresolved') for k in ('activity','occurrence','time')}}
            attribution={};populations={}
            for target_id,concept in concepts.items():
                paths=[p for p in graph.get('attribution_paths',[]) if p.get('event_definition_id')==event['id'] and p.get('to')==target_id]
                valid=[p for p in paths if p.get('validation_status')=='valid' and
                       p.get('case_map',{}).get('validation',{}).get('passed') is True and
                       p.get('entity_identity_validation',{}).get('status')=='pass']
                coverage=next((p['entity_identity_validation']['event_coverage'] for p in paths
                               if p.get('entity_identity_validation',{}).get('event_coverage')),None)
                path_states={}
                for p in paths:path_states[p.get('validation_status')]=path_states.get(p.get('validation_status'),0)+1
                confirmed_empty=[p for p in paths if p.get('validation_status')=='rule_confirmed_no_occurrences']
                attribution[target_id]={'status':'pass' if valid else
                    'rule_confirmed_no_occurrences' if confirmed_empty else 'fail' if paths and all(
                    p.get('validation_status')=='invalid' for p in paths) else 'unknown',
                    'rule_confirmed_path_ids':[p['id'] for p in confirmed_empty],
                    'path_ids':[p['id'] for p in valid], 'path_status_counts':path_states,
                    'event_coverage':coverage,
                    'scope':'unique occurrence-to-Entity mapping; no meaning/population claim'}
                population=concept.get('population',{})
                populations[target_id]={'status':'pass' if population.get('status')=='valid' and
                    population.get('identity_complete') is True else 'unknown','population_id':population.get('id')}
            event['validation_axes']={'version':VERSION,'rule_executable':physical,
                'event_semantics_supported':semantics,'attribution_validated':attribution,
                'case_population_validated':populations}
            event['candidate_kind']='event_extraction_rule'
        graph['validation_axes_version']=VERSION
        graph['validation_axes_policy']='independent_source_rule_event_meaning_target_attribution_and_case_population'
    finally:
        if connection is not None:connection.close()
