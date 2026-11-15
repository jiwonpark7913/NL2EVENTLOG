#!/usr/bin/env python3
"""Normalize target-method terminology in presentation and reviewer artifacts.

Never modify database bytes, input dictionaries, evaluation inputs, or private Gold.
Legacy source annotations remain reference labels, not inferred semantic ET truth.
"""
from __future__ import annotations
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('hospitalflow', 'plateflow', 'universityflow', 'warehouseflow')
CASE_NOTE = (
    'Physical storage is described as Tables and Keys. A table may identify or reference several '
    'Entity Types through different keys; a single Entity can appear in several tables. '
    'The displayed type labels are legacy author annotations, not validated semantic ET truth. '
    'Type classification, Entity identity resolution, and event attribution are separate decisions.'
)
TARGET_NOTE = (
    'This is an author-annotated source projection of legacy reference labels and activity sources. '
    'It is not a model-inferred EEG or a complete set of Event definitions with validated rules.'
)

def write_if_changed(path, text):
    if path.exists() and path.read_text() == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return True


def replacements(text):
    """Presentation wording only. Do not apply to stored SQL/JSON Gold or model inputs."""
    pairs = [
        ('Entity Representations (ERs, middle)', 'Tables (middle)'),
        ('Entity Representation (ER)', 'Table'),
        ('Entity Representations', 'Tables'),
        ('Entity Representation', 'Table'),
        ('Physical ERs', 'Tables'),
        ('EEG / ET / ER', 'EEG / ET / Table'),
        ('cross-ER', 'cross-table'),
        ('source ER', 'source table'),
        ('namespace-aware', 'identification-rule-aware'),
        ('pre-namespace Gold', 'legacy Gold'),
        ('Identity Namespaces', 'Entity identities'),
        ('Identity Namespace', 'Entity identification context'),
        ('identity namespaces', 'Entity identities'),
        ('identity namespace', 'Entity identification context'),
        ('namespace model', 'Entity identification model'),
        ('namespace contract', 'identification contract'),
        ('Gold Object Types', 'Legacy type labels'),
        ('Gold object types', 'legacy type labels'),
        ('Gold Object Type', 'Legacy type label'),
        ('Gold OTs', 'legacy type groups'),
        ('OT membership', 'legacy type annotation'),
        ('Evidence Graph', 'Event Extraction Graph'),
        ('DB Understanding Evidence Graph', 'Event Extraction Graph'),
        ('event candidates', 'Event definitions'),
        ('event candidate', 'Event definition'),
        ('Event candidates', 'Event definitions'),
        ('Event candidate', 'Event definition'),
        ('Gold Activity Sources (right)', 'Reference activity-source summary (right)'),
        ('Activity Source Bindings (right)', 'Reference activity-source summary (right)'),
    ]
    for old, new in pairs:
        text = text.replace(old, new)
    text = re.sub(r'\bERs\b', 'tables', text)
    text = re.sub(r'\bER\b(?!\s+diagram)', 'table', text)
    return text


def update_readme(path, dataset, level):
    text = path.read_text()
    # Replace complete obsolete claims before replacing their individual words.
    text = re.sub(r'\*\*Entity-model status:\*\*[^\n]*',
        '**Entity-model status:** ' + CASE_NOTE, text)
    text = re.sub(r'Each physical (?:ER|table) has exactly one currently annotated Entity Type candidate\.[^\n]*',
        CASE_NOTE, text)
    text = re.sub(r'A physical table is one \*\*Entity Representation \(ER\)\*\*\.[^\n]*',
        CASE_NOTE, text)
    text = text.replace('FK paths alone do not establish lifecycle membership.',
        'FK reachability alone does not validate occurrence attribution.')
    text = text.replace('Case Attribution or Lifecycle Membership.', 'validated event–entity attribution.')
    text = replacements(text)
    # Link wording changes never change target filenames or existing question text.
    if level == 'dataset':
        marker = '## Entity terminology'
        section = (marker + '\n\n' + CASE_NOTE + '\n\n'
            '[Canonical terminology and stage contracts](../../docs/system/EEG_ENTITY_MODEL.md). '
            'Step 2 uses explicit activities or implicit recorded history with optional process focus; '
            'legacy reference logs retain their original scopes.\n')
        if marker not in text:
            text = text.rstrip() + '\n\n' + section
    return write_if_changed(path, text)


def edit_svg(path):
    text = replacements(path.read_text())
    text = text.replace('Each physical table is an table.', 'Physical nodes are tables.')
    text = text.replace('Every table is an table;', 'Physical nodes are tables;')
    return write_if_changed(path, text)


def candidate_manifest(base, dataset):
    source = json.loads((base / 'review/gold_dfg/gold_source_manifest.json').read_text())
    con = sqlite3.connect('file:' + str(base / 'input/database.sqlite') + '?mode=ro', uri=True)
    tables = []
    groups = {}
    quote = lambda x: '"' + x.replace('"', '""') + '"'
    for table, annotation in source['tables'].items():
        cols = list(con.execute('PRAGMA table_info(' + quote(table) + ')'))
        pk = [c[1] for c in sorted(cols, key=lambda c: c[5]) if c[5]]
        references = {}
        for fk in con.execute('PRAGMA foreign_key_list(' + quote(table) + ')'):
            references.setdefault(fk[0], []).append(fk)
        foreign_keys = []
        for rows in references.values():
            rows.sort(key=lambda r: r[1])
            foreign_keys.append(dict(columns=[r[3] for r in rows], referenced_table=rows[0][2],
                referenced_columns=[r[4] for r in rows], role='structural_reference',
                semantic_attribution_validation='not_established_by_fk_alone'))
        tables.append(dict(table=table, primary_key=pk, foreign_keys=foreign_keys,
            legacy_type_label=annotation['ot'], semantic_et_validation='pending',
            identification_rule_validation='pending',
            legacy_source_activity_labels=annotation['activities'],
            legacy_source_time_columns=annotation['timestamps']))
        groups.setdefault(annotation['ot'], []).append(table)
    con.close()
    doc = dict(schema_version=2, dataset=dataset,
        status='candidate_only_not_validated_ET_gold',
        purpose='Reviewer-only Table/Key inventory and legacy labels, not runtime EEG or model input',
        identity_rule='identify(table, row, key_columns) resolves an Entity under a validated interpretation',
        default_directional_case_attribution='FK_to_referenced_PK_or_unique_only_when_validated',
        default_reverse_fk_traversal=False,
        table_key_interpretations=tables, legacy_type_groups=groups,
        target_method_contract=dict(
            et_classification='business_meaning_and_instance_granularity_before_instance_identity',
            definitions='Event definitions, not individual Event occurrences',
            parsing='one_call_by_default_then_original_request_based_final_review',
            explicit_selection='requested_activities',
            implicit_no_focus='all_supported_attributable_definitions',
            implicit_with_focus='definition_selection_using_request_and_EEG_evidence',
            process_focus_filters='Event_definitions_not_case_population',
            independent_lifecycle_gate=False),
        note='Activity labels are source summaries, not complete Event definitions. No semantic ET reannotation or extraction execution is performed by this renderer.')
    return write_if_changed(base / 'review/gold_dfg/entity_model_candidates.json',
                            json.dumps(doc, indent=2, ensure_ascii=False) + '\n')


def review_inventory(path):
    text = replacements(path.read_text())
    text = re.sub(r'\*\*Author annotations \(legacy ET candidates\)\.\*\*[^\n]*',
                  '**Legacy author annotations.** ' + CASE_NOTE, text)
    text = re.sub(r'\[.*?candidates\]\(entity_model_candidates.json\)[^\n]*',
                  '[Table/key review inventory](entity_model_candidates.json) — reviewer-only, not validated ET truth.', text)
    if 'entity_model_candidates.json' not in text:
        text += '\n[Table/key review inventory](entity_model_candidates.json) — reviewer-only, not model input.\n'
    return write_if_changed(path, text)


def root_readme():
    path = ROOT / 'README.md'
    text = path.read_text()
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith('Research implementation and four evaluation datasets'):
            lines[index] = ('Four evaluation datasets and author review tools for natural-language-to-event-log extraction. '
                'The target method uses Tables and Keys, Entity Types (ETs), Entity identification rules, '
                'and Event definitions in a request-independent Event Extraction Graph (EEG).')
    text = replacements('\n'.join(lines))
    # Normalize duplicated methodology links introduced by the earlier migration.
    link = '- [Canonical EEG terminology and stage contracts](docs/system/EEG_ENTITY_MODEL.md)'
    text = re.sub(r'^- \[.*?\]\(docs/system/EEG_ENTITY_MODEL.md\)\n?', '', text, flags=re.M)
    text = text.replace('## Repository map\n', '## Repository map\n\n' + link + '\n', 1)
    text = re.sub(r'\*\*Evaluation migration status:\*\*[^\n]*',
        '**Evaluation migration status:** stored reference labels and Gold logs retain their original semantics. '
        'SQL/CSV consistency is checked separately from semantic ET correctness and target-method validation. '
        'The current pipeline contracts are documented as target behavior, not new measured results.', text)
    return write_if_changed(path, re.sub(r'\n{3,}', '\n\n', text).rstrip() + '\n')


def main():
    counts = {}
    for name in NAMES:
        base = ROOT / 'datasets' / name
        changed = 0
        changed += update_readme(base / 'README.md', name, 'dataset')
        changed += update_readme(base / 'review/database/README.md', name, 'database')
        changed += update_readme(base / 'review/gold_dfg/README.md', name, 'gold')
        changed += review_inventory(base / 'review/gold_dfg/event_graph.md')
        changed += edit_svg(base / 'review/database/gold_evidence_graph.svg')
        changed += candidate_manifest(base, name)
        for sub in ['docs/object_type_verification.md', 'docs/object_activity_design.md',
                    'docs/schema_overview.md', 'docs/realism_review.md']:
            path = base / sub
            if path.exists():
                text = path.read_text()
                text = re.sub(r'A physical table is one \*\*Entity Representation \(ER\)\*\*\.[^\n]*', CASE_NOTE, text)
                changed += write_if_changed(path, replacements(text))
        counts[name] = changed
    counts['root_readme'] = root_readme()
    path = ROOT / 'docs/system/DESIGN_METHODOLOGY.md'
    text = path.read_text()
    text = re.sub(r'^> The active target terminology[^\n]*\n*', '', text)
    note = ('> Canonical method terms and stage contracts: [EEG terminology](EEG_ENTITY_MODEL.md). '
            'Construction notes below describe legacy dataset assumptions, not a new runtime-method evaluation.\n\n')
    if not text.startswith(note):
        text = note + replacements(text)
    counts['design_methodology'] = write_if_changed(path, text)
    print(json.dumps(counts, indent=2))

if __name__ == '__main__':
    main()
