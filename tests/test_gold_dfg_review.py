import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('gold_dfg_review',Path(__file__).resolve().parents[1]/'tools/build_gold_dfg_review.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class DFGTests(unittest.TestCase):
 def row(self,cid,eid,act,time):return dict(case_id=cid,event_id=eid,activity=act,timestamp='2026-01-01T'+time+':00Z')
 def test_case_boundaries_and_repeated_events(self):
  rows=[self.row('A','1','Receive','09:00'),self.row('B','4','Ship','10:00'),self.row('A','3','Ship','11:00'),self.row('A','2','Receive','10:00')]
  d=m.extract(rows)
  self.assertEqual(dict(d['nodes']),{'Receive':2,'Ship':2})
  self.assertEqual(dict(d['edges']),{('Receive','Receive'):1,('Receive','Ship'):1})
  self.assertEqual(dict(d['starts']),{'Receive':1,'Ship':1})
  self.assertEqual(dict(d['ends']),{'Ship':2})
 def test_tied_order_is_marked(self):
  d=m.extract([self.row('A','2','Ship','09:00'),self.row('A','1','Receive','09:00'),self.row('A','3','Close','10:00')])
  self.assertEqual(d['tied_timestamp_groups'],1)
  self.assertEqual(dict(d['ambiguous']),{('Receive','Ship'):1,('Ship','Close'):1})
 def test_empty_log(self):
  d=m.extract([]);self.assertEqual(dict(d['edges']),{});self.assertEqual(d['traces'],[])

if __name__=='__main__':unittest.main()
