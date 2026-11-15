"""Regression checks for terminology, identifier evidence, and review-only output."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('terminology', ROOT/'tools/migrate_eeg_terminology.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TerminologyTests(unittest.TestCase):
    def test_replacement_is_idempotent_and_preserves_external_erd(self):
        old = ('Entity Representations (ERs, middle); source ER; Event candidate; '
               'Identity Namespace; Full-size ER diagram; ERD')
        new = m.replacements(old)
        self.assertEqual(new, m.replacements(new))
        self.assertNotIn('Entity Representation', new)
        self.assertIn('Event definition', new)
        self.assertIn('Full-size ER diagram', new)
        self.assertIn('ERD', new)

    def test_root_readme_does_not_duplicate_intro_or_method_link(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'README.md').write_text(
                '# NL2EventLog\n\nResearch implementation and four evaluation datasets for natural-language-to-event-log extraction.\n\n'
                '## Repository map\n\n- [EEG / ET / ER target methodology](docs/system/EEG_ENTITY_MODEL.md)\n'
                '- [EEG / ET / ER target methodology](docs/system/EEG_ENTITY_MODEL.md)\n')
            before = m.ROOT
            try:
                m.ROOT = root
                self.assertTrue(m.root_readme())
                content = (root/'README.md').read_text()
                self.assertFalse(m.root_readme())
                self.assertEqual(content.count('](docs/system/EEG_ENTITY_MODEL.md)'), 1)
                self.assertNotIn('Entity Representation', content)
            finally:
                m.ROOT = before

    def test_manifest_preserves_composite_references_without_inventing_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base/'input').mkdir()
            (base/'review/gold_dfg').mkdir(parents=True)
            db = base/'input/database.sqlite'
            con = sqlite3.connect(db)
            con.executescript('CREATE TABLE parent(a TEXT,b TEXT,PRIMARY KEY(a,b));'
                             'CREATE TABLE child(id INTEGER PRIMARY KEY,a TEXT,b TEXT,'
                             'FOREIGN KEY(a,b) REFERENCES parent(a,b));')
            con.close()
            raw = db.read_bytes()
            source = {'tables': {t: {'ot': t.title(), 'activities': [], 'timestamps': []}
                                 for t in ['parent', 'child']}}
            (base/'review/gold_dfg/gold_source_manifest.json').write_text(json.dumps(source))
            self.assertTrue(m.candidate_manifest(base, 'fixture'))
            self.assertFalse(m.candidate_manifest(base, 'fixture'))
            self.assertEqual(raw, db.read_bytes())
            d = json.loads((base/'review/gold_dfg/entity_model_candidates.json').read_text())
            self.assertEqual(d['schema_version'], 2)
            self.assertNotIn('identity_namespace', json.dumps(d))
            self.assertNotIn('entity_representations', d)
            child = next(x for x in d['table_key_interpretations'] if x['table']=='child')
            fk, = child['foreign_keys']
            self.assertEqual(fk['columns'], ['a','b'])
            self.assertEqual(fk['referenced_columns'], ['a','b'])
            self.assertEqual(child['semantic_et_validation'], 'pending')
            self.assertFalse(d['target_method_contract']['independent_lifecycle_gate'])


if __name__ == '__main__':
    unittest.main()
