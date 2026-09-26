import sys
import unittest
from pathlib import Path
import numpy as np
import xarray as xr
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from update_ukmo_global import STEPS
from ukmo_tables import to_hourly,extra_values,condition_codes,make_row,TABLE_COLUMNS

class TableTests(unittest.TestCase):
    def test_scalars_and_interval_gusts(self):
        native={key:{h:np.array([float(h)]) for h in [0]+STEPS} for key in TABLE_COLUMNS}
        native['rafales'].pop(0)
        result=to_hourly(native,STEPS)
        np.testing.assert_allclose(result['temperature'][:,0],np.arange(169))
        np.testing.assert_allclose(result['rafales'][55:58,0],[57,57,57])
        np.testing.assert_allclose(result['rafales'][145:151,0],[150]*6)
        self.assertTrue(np.isnan(result['rafales'][0,0]))
        row=make_row(result,0,0,0,0,1)
        self.assertEqual(len(row),33);self.assertIsNone(row[6]);self.assertEqual(row[9],1)
        row=make_row(result,56,0,.3,12,5)
        self.assertEqual(row[0],56);self.assertEqual(row[6],57);self.assertEqual(row[12],12)

    def test_circular_direction_crosses_north(self):
        samples={h:np.array([350. if h<=54 else 10.]) for h in [0]+STEPS}
        result=to_hourly({'direction':samples},STEPS)['direction']
        self.assertGreater(result[55,0],350)
        self.assertLess(result[56,0],10)

    def test_extra_units(self):
        ds=xr.Dataset({'relative_humidity':(('latitude','longitude'),[[.8]],{'units':'1'})})
        # Preserve two spatial dimensions in actual global data.
        ds=xr.Dataset({'relative_humidity':(('latitude','longitude'),np.full((2,2),.8),{'units':'1'})})
        np.testing.assert_allclose(extra_values(ds,'humidity'),80)
        ds=xr.Dataset({'air_pressure_at_sea_level':(('latitude','longitude'),np.full((2,2),101325),{'units':'Pa'})})
        np.testing.assert_allclose(extra_values(ds,'pressure'),1013.25)
        ds.air_pressure_at_sea_level.attrs['units']='hPa'
        with self.assertRaises(ValueError):extra_values(ds,'pressure')

    def test_conditions_are_indicative_not_unknown(self):
        np.testing.assert_array_equal(condition_codes(np.array([0,0,0,0,.2,3]),np.array([0,20,50,90,10,100])),[1,2,3,4,5,6])

if __name__=='__main__':unittest.main()
