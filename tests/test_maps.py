import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import numpy as np
import xarray as xr
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import ukmo_maps as maps
import update_ukmo_global as pipeline

class MapTests(unittest.TestCase):
    def dataset(self, product, value, units, height=None):
        field=maps.PRODUCTS[product]['field']
        ds=xr.Dataset({field:(('latitude','longitude'),np.full((2,3),value),{'units':units})},coords={'latitude':[45.,46.],'longitude':[1.,2.,3.]})
        if height is not None: ds['height']=height
        return ds

    def test_units_and_heights(self):
        np.testing.assert_allclose(maps.field_values(self.dataset('temperature',283.15,'K',1.5),'temperature'),10)
        np.testing.assert_allclose(maps.field_values(self.dataset('vent',10,'m s-1',10),'vent'),36)
        np.testing.assert_allclose(maps.field_values(self.dataset('rafales',20,'m s-1',10),'rafales'),72)
        np.testing.assert_allclose(maps.field_values(self.dataset('nuages',.5,'1'),'nuages'),50)
        with self.assertRaises(ValueError): maps.field_values(self.dataset('temperature',283,'K',2),'temperature')
        with self.assertRaises(ValueError): maps.field_values(self.dataset('nuages',1.5,'1'),'nuages')
        with self.assertRaises(ValueError): maps.field_values(self.dataset('vent',np.nan,'m s-1',10),'vent')

    def test_rain_accumulates_every_native_period_without_sampling(self):
        lon=np.arange(-26,47,.5);lat=np.arange(29,74,.5)
        with tempfile.TemporaryDirectory() as tmp:
            writer=maps.MapWriter(lat,lon,datetime(2026,9,25,12,tzinfo=timezone.utc),tmp,ROOT/'config')
            maxima=[]
            def capture(product,region,values,step,start):
                maxima.append((step,float(values.max())))
            with patch.object(writer,'write',side_effect=capture):
                for step in pipeline.STEPS:
                    field=np.ones((len(lat),len(lon)))*pipeline.period(step)*2
                    writer.add_rain(field,step)
            self.assertEqual(len(maxima),12)
            self.assertTrue(all(value==step*2 for step,value in maxima))
            for grid in writer.regions.values(): np.testing.assert_allclose(grid['total'],336)

    def test_validity_and_period_checked(self):
        run=datetime(2026,9,25,12,tzinfo=timezone.utc)
        ds=xr.Dataset({'forecast_reference_time':int(run.timestamp()),'forecast_period':24*3600,'time':int(run.timestamp())+24*3600,'forecast_period_bnds':('bnds',[21*3600,24*3600])})
        ds.forecast_reference_time.attrs['units']='seconds since 1970-01-01 00:00:00'
        ds.forecast_period.attrs['units']='seconds'
        pipeline.validate_time(ds,run,24,3)
        with self.assertRaises(ValueError):pipeline.validate_time(ds,run,24,1)
        with self.assertRaises(ValueError):pipeline.validate_time(ds,run,48,3)

    def test_rain_missing_values_fail_closed(self):
        ds=xr.Dataset({'precipitation':(('latitude','longitude'),[[.001,.002],[.003,.004]],{'units':'m'})},coords={'latitude':[45,46],'longitude':[1,2]})
        np.testing.assert_allclose(pipeline.rainfall(ds),[[1,2],[3,4]])
        ds['precipitation'].values[0,0]=np.nan
        with self.assertRaises(ValueError):pipeline.rainfall(ds)

    def test_vector_export_and_wind_scale(self):
        for product in ('vent','rafales'):np.testing.assert_array_equal(np.diff(maps.PRODUCTS[product]['levels']),5)
        with tempfile.TemporaryDirectory() as tmp:
            lon=np.linspace(-26,46,45);lat=np.linspace(29,73,40)
            field=np.ones((len(lat),len(lon)))*12
            target=Path(tmp)/'map.png'
            box=maps._render(lon,lat,field,'temperature','europe','2026092512',24,target,ROOT/'config')
            svg=target.with_suffix('.svg').read_text(encoding='utf-8')
            self.assertNotIn('<image',svg)
            self.assertIn('<path',svg)
            self.assertIn('Powered by Met Office',svg)
            self.assertTrue(all(0<v<1 for v in box))
            self.assertTrue(target.exists())

if __name__=='__main__':unittest.main()
