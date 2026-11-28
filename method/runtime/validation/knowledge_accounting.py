"""Measure independent source-supported requirements through the five v2 stages."""

from src.step1_understand.candidate_ledger import candidate_key


def knowledge_counts(required, ledger, whole_graph, request_graph, pi):
    """PURPOSE: Separate discovery, decision, projection, retrieval, and selection losses.
    INPUT: Independent physical facts with expected Case, ledger, runtime views and checked PI.
    OUTPUT: Conditional stage counts and first-loss diagnoses for each lost fact.
    """
    stages = ('discovered', 'decided', 'projected', 'retrieved', 'selected')
    counts = dict.fromkeys(stages, 0)
    losses = []
    records = {row['id']: row for row in ledger['candidates']}
    executable = {e['id'] for e in whole_graph['event_definitions'] if e.get('extraction_status') == 'executable'}
    visible = {e['id'] for e in request_graph['event_definitions']}
    chosen = set(pi['selected_event_definition_ids'])

    def path_ids(view, case, ids):
        """PURPOSE: Verify that a candidate kept the required Case projection.
        INPUT: Runtime view, target ET and allowed EDs. OUTPUT: Observed path IDs."""
        return {p['id'] for p in view.get('attribution_paths', [])
                if p['to'] == case and p['event_definition_id'] in ids
                and p['validation_status'] == 'valid' and p['case_map']['validation']['passed']}

    for fact in required:
        candidate = candidate_key(fact['kind'], fact['source'])
        row = records.get(candidate, {})
        admitted = set(row.get('projected_ids', [])) & executable
        retrieved_paths = path_ids(request_graph, fact['case'], admitted & visible)
        selected_paths = {p for e in admitted & chosen for p in pi.get('verified_attribution_paths', {}).get(e, [])}
        checks = (bool(row), row.get('decision') == 'approved', bool(path_ids(whole_graph, fact['case'], admitted)),
                  bool(retrieved_paths), bool(retrieved_paths & selected_paths))
        for stage, present in zip(stages, checks):
            if not present:
                losses.append({'candidate_id': candidate, 'first_loss': stage})
                break
            counts[stage] += 1
    return {'required': len(required), 'stage_counts': counts, 'first_losses': losses}
