"""Regression checks for public dictionaries keyed by physical table and column names."""

import copy
import unittest

from src.common.data_dictionary import normalize_dictionary


class DictionaryFormatTests(unittest.TestCase):
    """Preserve public descriptions across equivalent input representations."""

    def test_name_keyed_dictionary_retains_citable_evidence(self):
        """PURPOSE: Prevent silent loss of table and column documentation in name-keyed DDs.
        INPUT: Public table map with nested column map and SQL type declarations.
        OUTPUT: Verbatim citable prose and declarations; source mapping remains unchanged.
        """
        raw = {'jobs': {'description': 'One handling job per row.', 'columns': {
            'job_id': {'declaration': 'TEXT PRIMARY KEY', 'description': 'Handling job identifier.'},
            'finished_at': {'declaration': 'TEXT NOT NULL', 'description': 'Actual job completion time.'}}}}
        original = copy.deepcopy(raw)
        result = normalize_dictionary(raw)
        self.assertEqual(raw, original)
        self.assertEqual(result['tables'][0]['table'], 'jobs')
        self.assertEqual(result['tables'][0]['definition'], 'One handling job per row.')
        columns = {item['column']: item for item in result['columns']}
        self.assertEqual(columns['job_id']['type'], 'TEXT PRIMARY KEY')
        self.assertEqual(columns['finished_at']['definition'], 'Actual job completion time.')
        self.assertEqual(result['evidence_text']['C:jobs.finished_at'], 'Actual job completion time.')

    def test_wrapped_mapping_matches_explicit_record_list(self):
        """PURPOSE: Maintain equivalent dictionary meaning for list and wrapped-map inputs.
        INPUT: Two encodings of the same table and column records.
        OUTPUT: Equal normalized tables, columns and semantic evidence.
        """
        table = {'description': 'One order per row.', 'columns': {
            'id': {'type': 'INTEGER', 'description': 'Order identifier.'}}}
        mapping = normalize_dictionary({'tables': {'orders': table}})
        explicit = normalize_dictionary({'tables': [{
            'table': 'orders', 'description': table['description'],
            'columns': [{'name': 'id', **table['columns']['id']}]}]})
        for field in ('tables', 'columns', 'semantic_statements', 'evidence_text'):
            self.assertEqual(mapping[field], explicit[field])

    def test_name_keyed_format_keeps_oracle_fields_filtered(self):
        """PURPOSE: Keep evaluator-only fields excluded before adapting dictionary structure.
        INPUT: Public descriptions with an explicitly forbidden answer field.
        OUTPUT: Ordinary prose survives and answer material is removed and audited.
        """
        raw = {'orders': {'description': 'One order per row.', 'gold_sql': 'SELECT hidden_answer',
                          'columns': {'id': {'description': 'Order identifier.'}}}}
        result = normalize_dictionary(raw)
        self.assertEqual(result['tables'][0]['definition'], 'One order per row.')
        self.assertEqual(result['input_contract_audit']['blocked_count'], 1)
        self.assertNotIn('hidden_answer', str(result['evidence_text']))

    def test_explicit_code_assignments_reach_review_evidence(self):
        """PURPOSE: Preserve code meanings embedded in public description text for event review.
        INPUT: Name-keyed dictionary with literal semicolon-separated code assignments.
        OUTPUT: Per-code domains and citable statements plus unchanged original prose.
        """
        text = 'A = item accepted; L = item loaded.'
        result = normalize_dictionary({'scans': {'description': 'One scan per item action.',
            'columns': {'kind': {'description': text}}}})
        column = result['columns'][0]
        self.assertEqual(column['code_meanings'], {'A': 'item accepted', 'L': 'item loaded'})
        self.assertEqual(set(column['value_domain']), {'A', 'L'})
        self.assertEqual(result['evidence_text']['C:scans.kind'], text)
        self.assertIn({'id': 'C:scans.kind:code:L', 'table': 'scans', 'column': 'kind',
                       'field': 'code_meaning', 'text': 'item loaded'}, result['semantic_statements'])

    def test_prose_and_ambiguous_codes_are_not_invented_domains(self):
        """PURPOSE: Refuse partial or conflicting parses as code-domain evidence.
        INPUT: Ordinary prose and repeated-code assignments. OUTPUT: No fabricated code meanings.
        """
        for text in ('A timestamp at which an item was loaded.', 'A = accepted; other text',
                     'A = accepted; A = approved'):
            with self.subTest(text=text):
                result = normalize_dictionary({'scans': {'columns': {'kind': {'description': text}}}})
                self.assertEqual(result['columns'][0]['code_meanings'], {})
