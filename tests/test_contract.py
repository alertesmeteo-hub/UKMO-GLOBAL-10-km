import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update_ukmo_global as m
import numpy as np
class ContractTests(unittest.TestCase):
 def test_national_catalogue_including_corsica(self):
  lat=np.arange(-90,90,.09375);lon=np.arange(-180,180,.140625)
  communes,grid,points,departments=m.catalogue(ROOT/'config/communes-france.json',lat,lon)
  self.assertEqual(len(communes),34746)
  self.assertEqual(set(departments),m.DEPS)
  self.assertEqual(len(departments),96)
  self.assertEqual(sum(map(len,departments.values())),34746)
  for code,dep in [('75056','75'),('59350','59'),('67482','67'),('2A004','2A'),('2B033','2B')]:
   commune=next(c for c in departments[dep] if c[0]==code)
   self.assertTrue(0<=commune[6]<len(points))
   point=points[commune[6]]
   self.assertLessEqual(abs(point[1]-commune[4]),.09375/2+.00001)
   self.assertLessEqual(abs(point[2]-commune[5]),.140625/2+.00001)
 def test_steps(self):
  self.assertEqual(m.STEPS[:3],[1,2,3]);self.assertEqual(m.STEPS[-1],168);self.assertEqual(len(m.STEPS),88)
 def test_periods(self):
  self.assertEqual(m.period(54),1);self.assertEqual(m.period(57),3);self.assertEqual(m.period(150),6)
 def test_schema(self):
  ref=json.loads((ROOT/'tests/reference-schema.json').read_text());self.assertEqual(len(ref['values']),33);self.assertEqual(ref['values'][2],'precipitation_mm');self.assertEqual(ref['values'][12],'precipitation_total_mm')
if __name__=='__main__':unittest.main()
