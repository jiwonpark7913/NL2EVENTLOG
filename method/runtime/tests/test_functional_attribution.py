"""Role-preserving reverse UNIQUE FK attribution and physical constraint checks."""

from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
import unittest

from src.common.attribution_policy import attribution_adjacency, database_path_issues
from src.step1_understand.validate_event_attribution_paths import enumerate_attribution_paths
from src.step1_understand.entity_representations import validate_entity_attribution


class FunctionalAttributionTests(unittest.TestCase):
    """Exercise real SQLite joins instead of accepting observed overlap as a key constraint."""

    def setUp(self):
        """PURPOSE: Create a public synthetic paired-leg schema with distinct FK roles.
        INPUT: Test lifecycle. OUTPUT: Temporary DB, reference inventory and canonical case population.
        """
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'db.sqlite'
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript("""
                CREATE TABLE legs(id TEXT PRIMARY KEY);
                CREATE TABLE stays(id TEXT PRIMARY KEY, arrival TEXT UNIQUE REFERENCES legs(id),
                                   departure TEXT UNIQUE REFERENCES legs(id));
                CREATE TABLE events(id TEXT PRIMARY KEY, leg TEXT REFERENCES legs(id), kind TEXT, at TEXT);
                INSERT INTO legs VALUES ('A'),('B'),('C'),('D');
                INSERT INTO stays VALUES ('S1','A','B'),('S2','C','D');
                INSERT INTO events VALUES ('E1','A','arrival','2026-01-01'),
                    ('E2','B','departure','2026-01-01'),('E3','C','arrival','2026-01-02'),
                    ('E4','D','departure','2026-01-02');
            """)
        self.references = [
            {'id': 'R:event-leg', 'child_table': 'events', 'parent_table': 'legs',
             'columns': [['leg', 'id']], 'kind': 'declared', 'child_key_unique': False},
            *[{'id': 'R:' + role, 'child_table': 'stays', 'parent_table': 'legs',
               'columns': [[role, 'id']], 'kind': 'declared', 'child_key_unique': True}
              for role in ('arrival', 'departure')],
        ]
        self.objects = [{'id': 'O:' + table, 'table': table, 'pk': ['id']}
                        for table in ('events', 'legs', 'stays')]
        self.concepts = [{'id': 'ET:Stay', 'kind': 'identity', 'members': ['O:stays'],
                          'case_key': {'fields': ['id']}, 'population': {'maps': [
                              {'representation_id': 'O:stays', 'identity_scope_id': 'stay'}]}}]

    def paths(self, kind, *, label=None, dictionary=None):
        """PURPOSE: Generate and execute the real source-to-case paths for one event kind.
        INPUT: Physical kind value, optional supported label and DD. OUTPUT: Measured native paths.
        """
        binding = {'id': 'E:' + kind, 'table': 'events',
                   'alpha': {'kind': 'value', 'column': 'kind', 'value': kind},
                   'occurrence_time_source': {'columns': ['at']}}
        if label:
            binding.update(activity_label=label, activity_semantics={'status': 'supported',
                           'occurrence_status': 'supported'})
        return enumerate_attribution_paths(self.db, [binding], self.objects, self.concepts,
                                           self.references, [], dictionary=dictionary)

    def test_arrival_and_departure_preserve_fk_roles_and_single_case(self):
        """PURPOSE: Attribute events to the right canonical stay through distinct UNIQUE FK roles.
        INPUT: Arrival-only and departure-only event predicates.
        OUTPUT: Each valid path maps two events to two single cases and uses the correct FK ID.
        """
        for kind in ('arrival', 'departure'):
            with self.subTest(kind=kind):
                valid = [p for p in self.paths(kind) if p['validation_status'] == 'valid']
                self.assertEqual(len(valid), 1)
                path = valid[0]
                self.assertEqual(path['edge_ids'], ['R:event-leg', 'R:' + kind])
                self.assertEqual(path['joins'][-1]['direction'], 'parent_to_child')
                self.assertEqual(path['case_map']['validation']['max_cases_per_source'], 1)
                with closing(sqlite3.connect(self.db)) as conn:
                    self.assertEqual(database_path_issues(conn, path['joins']), [])
                    pairs = conn.execute(path['case_map']['map_sql'], path['case_map']['map_parameters']).fetchall()
                self.assertEqual({case for _, case in pairs}, {'["S1"]', '["S2"]'})

    def test_observed_unique_or_partial_index_cannot_authorize_reverse(self):
        """PURPOSE: Reject a fabricated uniqueness claim despite unique values in the current rows.
        INPUT: Nonunique FK with an optional partial UNIQUE index.
        OUTPUT: Physical reverse-path guard rejects both; forward FK remains supported.
        """
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript("CREATE TABLE notes(id TEXT PRIMARY KEY, leg TEXT REFERENCES legs(id));"
                               "INSERT INTO notes VALUES ('N1','A');")
            reference = {'id': 'R:note', 'child_table': 'notes', 'parent_table': 'legs',
                         'columns': [['leg', 'id']], 'kind': 'declared', 'child_key_unique': True}
            adjacency = attribution_adjacency([reference])
            self.assertFalse(database_path_issues(conn, adjacency['notes']))
            self.assertTrue(database_path_issues(conn, adjacency['legs']))
            conn.execute('CREATE UNIQUE INDEX partial_leg ON notes(leg) WHERE leg IS NOT NULL')
            self.assertTrue(database_path_issues(conn, adjacency['legs']))

    def test_conflicting_role_paths_do_not_choose_an_arbitrary_case(self):
        """PURPOSE: Block a source event that reaches two different canonical cases through two roles.
        INPUT: One event on a leg used as one stay's departure and another stay's arrival.
        OUTPUT: Both otherwise-functional paths become ambiguous with no deliverable occurrence.
        """
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE stays SET arrival='B' WHERE id='S2'")
            conn.execute("INSERT INTO events VALUES ('EX','B','ambiguous','2026-01-03')")
        paths = self.paths('ambiguous')
        self.assertEqual(sum(p['validation_status'] == 'valid' for p in paths), 2)
        validate_entity_attribution(self.db, paths, self.concepts)
        self.assertTrue(all(p['validation_status'] == 'ambiguous' for p in paths))
        self.assertTrue(all(p['entity_identity_validation']['event_coverage']['deliverable_source_rows'] == 0
                            for p in paths))

    def test_documented_roles_are_separate_without_activity_name_rules(self):
        """PURPOSE: Keep distinct proved role projections for PI to resolve.
        INPUT: One shared object with two documented reference roles.
        OUTPUT: The role-specific paths reach compatible scopes without choosing a role by event label.
        """
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE stays SET arrival='B' WHERE id='S2'")
        dictionary = {'columns': [
            {'table': 'stays', 'column': 'arrival', 'id': 'C:arrival', 'definition': 'Arrival leg.'},
            {'table': 'stays', 'column': 'departure', 'id': 'C:departure', 'definition': 'Departure leg.'},
        ]}
        paths = self.paths('departure', label='Observed transition', dictionary=dictionary)
        validate_entity_attribution(self.db, paths, self.concepts)
        by_role = {p['role_validation']['reference']['role']: p for p in paths}
        self.assertEqual(set(by_role), {'arrival','departure'})
        self.assertTrue(all(p['validation_status']=='valid' for p in paths))
        self.assertEqual(by_role['departure']['case_map']['validation']['matched_source_rows'],2)
        self.assertEqual(by_role['arrival']['case_map']['validation']['matched_source_rows'],1)

    def test_documented_role_excludes_opposite_only_rows_but_keeps_unknowns(self):
        """PURPOSE: Distinguish wrong-role rows from events with missing membership.
        INPUT: A departure event on an inbound leg, then one on an unclassified leg.
        OUTPUT: First scope is valid and the genuinely unmatched event fails validation.
        """
        dictionary = {'columns': [
            {'table': 'stays', 'column': 'arrival', 'id': 'C:arrival', 'definition': 'Arrival leg.'},
            {'table': 'stays', 'column': 'departure', 'id': 'C:departure', 'definition': 'Departure leg.'},
        ]}
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("INSERT INTO events VALUES ('EX','A','departure','2026-01-03')")
        chosen = next(p for p in self.paths('departure', label='Actual take-off', dictionary=dictionary)
                      if p['role_validation']['reference']['role'] == 'departure')
        observed = chosen['case_map']['validation']
        self.assertEqual(chosen['validation_status'], 'valid')
        self.assertEqual((observed['all_source_rows'],observed['out_of_role_source_rows'],
                          observed['source_rows'],observed['zero_case_source_rows']), (3,1,2,0))
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("INSERT INTO legs VALUES ('Z')")
            conn.execute("INSERT INTO events VALUES ('EY','Z','departure','2026-01-03')")
        chosen = next(p for p in self.paths('departure', label='Actual take-off', dictionary=dictionary)
                      if p['role_validation']['reference']['role'] == 'departure')
        self.assertEqual(chosen['reason_code'], 'role_path_has_unmapped_events')
        self.assertEqual(chosen['case_map']['validation']['zero_case_source_rows'], 1)

    def test_selected_role_filters_canonical_case_population(self):
        """PURPOSE: Keep canonical case keys when selecting an outbound subset.
        INPUT: A logical leg ET and one declared reverse role. OUTPUT: Only departure leg keys are emitted.
        """
        from src.common.entity_population import population_cte
        case = {'table': 'legs', 'columns': ['id'], 'population': {'entity_type_id': 'ET:Leg',
            'maps': [{'id': 'map', 'representation_id': 'O:legs', 'table': 'legs',
                      'key_columns': ['id'], 'identity_scope_id': 'leg'}]}}
        steps = attribution_adjacency(self.references)['legs']
        departure = next(step for step in steps if step['relationship_id'] == 'R:departure')
        with closing(sqlite3.connect(self.db)) as conn:
            query = 'WITH ' + population_cte(case, {'kind':'reference_role','step':departure})
            rows = conn.execute(query + " SELECT json_extract(case_id, '$[2][0][1]') FROM entity_cases").fetchall()
        self.assertEqual({row[0] for row in rows}, {'B','D'})
