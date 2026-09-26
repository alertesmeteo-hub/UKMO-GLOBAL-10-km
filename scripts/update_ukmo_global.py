#!/usr/bin/env python3
"""Met Office Global Deterministic 10 km rainfall -> departmental JSON v3."""
from __future__ import annotations
import argparse,json,math,tempfile,time
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np
import requests
import xarray as xr

BASE="https://met-office-atmospheric-model-data.s3.eu-west-2.amazonaws.com"
DEPS={f"{n:02d}" for n in range(1,96) if n!=20} | {"2A","2B"}
STEPS=list(range(1,55))+list(range(57,145,3))+list(range(150,169,6))
VERSION="2.2.0"
SESSION=requests.Session();SESSION.headers["User-Agent"]="AlertesMeteo-UKMO-Global/1.0"

def period(step):return 1 if step<=54 else 3 if step<=144 else 6
def run_iso(run):return run.strftime("%Y-%m-%dT%H:%M:%SZ")
def key(run,step):
 valid=run+timedelta(hours=step);p=period(step)
 return f"global-deterministic-10km/{run:%Y%m%dT%H%MZ}/{valid:%Y%m%dT%H%MZ}-PT{step:04d}H00M-precipitation_accumulation-PT{p:02d}H.nc"
def url(run,step):return f"{BASE}/{key(run,step)}"
def request(method,target,**kwargs):
 for attempt in range(4):
  try:
   response=SESSION.request(method,target,timeout=120,**kwargs)
   if response.status_code==404:return None
   response.raise_for_status();return response
  except requests.RequestException:
   if attempt==3:raise
   time.sleep(2**attempt)

def select_run():
 now=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0);candidates=[]
 for days in range(4):
  date=now-timedelta(days=days)
  for hour in (12,0):candidates.append(date.replace(hour=hour))
 for run in sorted(set(candidates),reverse=True):
  if run<=now and request("HEAD",url(run,168)) is not None:return run
 raise RuntimeError("Aucun run UKMO complet jusqu’à +168 h n’est disponible.")

def download_dataset(run,step,temp,variable=None):
 name=variable or f"precipitation_accumulation-PT{period(step):02d}H"
 target=Path(temp)/f"{name}-{step:03d}.nc"
 valid=run+timedelta(hours=step)
 source=f"{BASE}/global-deterministic-10km/{run:%Y%m%dT%H%MZ}/{valid:%Y%m%dT%H%MZ}-PT{step:04d}H00M-{name}.nc"
 response=request("GET",source,stream=True)
 if response is None:raise RuntimeError(f"Échéance UKMO +{step} h absente")
 with target.open("wb") as handle:
  for chunk in response.iter_content(1024*1024):
   if chunk:handle.write(chunk)
 dataset=xr.open_dataset(target,engine="h5netcdf",decode_times=False)
 try: validate_time(dataset,run,step,period(step) if variable is None or name.startswith('wind_gust_at_10m_max') else None)
 except Exception:
  dataset.close();raise
 return dataset,target

def validate_time(dataset,run,step,span=None):
 if str(dataset['forecast_reference_time'].attrs.get('units',''))!='seconds since 1970-01-01 00:00:00':raise ValueError('Origine temporelle UKMO inattendue')
 if int(dataset['forecast_reference_time'])!=int(run.timestamp()) or int(dataset['forecast_period'])!=step*3600:raise ValueError('Run ou échéance UKMO incohérent')
 if str(dataset['forecast_period'].attrs.get('units',''))!='seconds':raise ValueError('Unité temporelle UKMO inattendue')
 if int(dataset['time'])!=int((run+timedelta(hours=step)).timestamp()):raise ValueError('Date de validité UKMO incohérente')
 if span is not None and not np.array_equal(dataset['forecast_period_bnds'].values,[(step-span)*3600,step*3600]):raise ValueError('Période UKMO incohérente')
def coordinate_names(dataset):
 lat=next(name for name in dataset.coords if "latitude" in name.lower())
 lon=next(name for name in dataset.coords if "longitude" in name.lower())
 return lat,lon
def coordinates(dataset):
 lat_name,lon_name=coordinate_names(dataset)
 return np.asarray(dataset[lat_name].values),np.asarray(dataset[lon_name].values)
def rainfall(dataset):
 names=[name for name in dataset.data_vars if "precip" in name.lower()] or list(dataset.data_vars)
 lat_name,lon_name=coordinate_names(dataset);field=dataset[names[0]].squeeze()
 if lat_name not in field.dims or lon_name not in field.dims:raise RuntimeError(f"Dimensions pluie UKMO inattendues : {field.dims}")
 values=np.asarray(field.transpose(lat_name,lon_name).values,dtype=float)
 units=str(field.attrs.get("units","")).strip().lower()
 factor=1000.0 if units in {"m","metre","metres","meter","meters"} else 1.0
 if factor==1000.0:values*=factor
 elif units not in {"mm","kg m-2","kg m**-2","kg/m2"}:raise RuntimeError(f"Unité de précipitations UKMO inconnue : {units!r}")
 if not np.isfinite(values).all():raise ValueError('Précipitations UKMO incomplètes : publication refusée')
 # NetCDF quantization can retain a one-quantum negative residual near zero.
 # Only tolerate the precision declared by this field, never arbitrary negatives.
 digits=field.attrs.get('least_significant_digit')
 tolerance=1e-6
 if digits is not None and 0<=int(digits)<=15:
  tolerance=max(tolerance,factor*2.0**(-math.ceil(int(digits)*math.log2(10))))
 minimum=float(np.min(values))
 if minimum < -tolerance*(1+1e-6):raise ValueError(f'Précipitations UKMO négatives : {minimum} mm, tolérance {tolerance} mm')
 if minimum<0:print(f'Résidu de quantification UKMO ramené à zéro : {minimum:.9f} mm (tolérance {tolerance:.9f} mm).',flush=True)
 return np.maximum(values,0.0)

def catalogue(path,lat,lon):
 communes=json.loads(Path(path).read_text(encoding="utf-8-sig"))["communes"]
 communes=[c for c in communes if str(c[2]).upper() in DEPS]
 if len(communes)<34000 or {str(c[2]).upper() for c in communes}!=DEPS:raise ValueError("Catalogue national UKMO incomplet")
 if lat.ndim!=1 or lon.ndim!=1:raise RuntimeError("Grille UKMO non régulière inattendue")
 mapping=[]
 for commune in communes:
  iy=int(np.abs(lat-float(commune[5])).argmin());ix=int(np.abs(((lon-float(commune[6])+180)%360)-180).argmin());mapping.append((commune,iy,ix))
 unique=sorted({(iy,ix) for _,iy,ix in mapping});point_id={cell:i for i,cell in enumerate(unique)};by_dep=defaultdict(list)
 for commune,iy,ix in mapping:by_dep[str(commune[2]).upper()].append([str(commune[0]),str(commune[1]),list(commune[3]),int(commune[4]),float(commune[5]),float(commune[6]),point_id[iy,ix]])
 points=[[iy*len(lon)+ix,round(float(lat[iy]),5),round(float(lon[ix]),5),0] for iy,ix in unique]
 return communes,unique,points,by_dep

def build(catalog_path,output,repository,force=False):
 run=select_run();old=request("GET",f"https://raw.githubusercontent.com/{repository}/data/index.json")
 print(f'Run UKMO sélectionné : {run_iso(run)}',flush=True)
 if old is not None and not force:
  try:
   previous=old.json().get("model",{})
   if previous.get("run_time")==run_iso(run) and previous.get('pipeline_version')==VERSION:print("Run déjà publié.");return
  except ValueError:pass
 output=Path(output);(output/"departements").mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as temp:
  first,path=download_dataset(run,1,temp);lat,lon=coordinates(first);communes,grid,points,by_dep=catalogue(catalog_path,lat,lon)
  from ukmo_maps import MapWriter,MAP_STEPS,PRODUCTS,field_values
  writer=MapWriter(lat,lon,run,output,Path(catalog_path).parent)
  field=rainfall(first);native={1:np.array([field[iy,ix] for iy,ix in grid])};writer.add_rain(field,1);first.close();path.unlink()
  for number,step in enumerate(STEPS[1:],2):
   dataset,path=download_dataset(run,step,temp)
   current_lat,current_lon=coordinates(dataset)
   if not np.array_equal(lat,current_lat) or not np.array_equal(lon,current_lon):raise ValueError('Grille UKMO variable entre échéances')
   field=rainfall(dataset);native[step]=np.array([field[iy,ix] for iy,ix in grid]);writer.add_rain(field,step);dataset.close();path.unlink()
   if number%10==0:print(f"Échéances téléchargées : {number}/{len(STEPS)}",flush=True)
  from ukmo_tables import EXTRA_FIELDS,extra_values,to_hourly,condition_codes,make_row,TABLE_COLUMNS
  table_native={}
  for product,spec in {**PRODUCTS,**EXTRA_FIELDS}.items():
   if product=='precipitation':continue
   table_native[product]={}
   for step in (STEPS if product=='rafales' else [0]+STEPS):
    variable=f'wind_gust_at_10m_max-PT{period(step):02d}H' if product=='rafales' else spec['variable']
    dataset,path=download_dataset(run,step,temp,variable)
    current_lat,current_lon=coordinates(dataset)
    if not np.array_equal(lat,current_lat) or not np.array_equal(lon,current_lon):raise ValueError('Grille UKMO incohérente entre paramètres')
    field=extra_values(dataset,product) if product in EXTRA_FIELDS else field_values(dataset,product)
    table_native[product][step]=np.array([field[iy,ix] for iy,ix in grid])
    if product in PRODUCTS and step in MAP_STEPS:
     writer.add_field(field,product,step,step-period(step) if product=='rafales' else step)
    dataset.close();path.unlink()
   print(f'Champs horaires et cartes {product} produits.',flush=True)
  writer.finish()
  table_fields=to_hourly(table_native,STEPS)
  hourly={0:np.zeros(len(grid))}
  for step in STEPS:
   span=period(step);increment=native[step]/span
   for hour in range(step-span+1,step+1):hourly[hour]=increment
  ref=json.loads((Path(__file__).resolve().parents[1]/"tests/reference-schema.json").read_text());total=np.zeros(len(grid));forecasts={dep:[] for dep in by_dep}
  for hour in range(169):
   increment=hourly[hour];total+=increment;valid=run_iso(run+timedelta(hours=hour))
   conditions=condition_codes(increment,table_fields['nuages'][hour])
   for dep,commune_rows in by_dep.items():
    ids=sorted({row[6] for row in commune_rows});values=[]
    for gid in ids:
     values.append(make_row(table_fields,hour,gid,increment[gid],total[gid],conditions[gid]))
    forecasts[dep].append([valid,values])
  department_index={};generated=run_iso(datetime.now(timezone.utc))
  for dep,commune_rows in by_dep.items():
   ids=sorted({row[6] for row in commune_rows});local={gid:i for i,gid in enumerate(ids)};dep_points=[points[i] for i in ids];dep_rows=[row[:6]+[local[row[6]]] for row in commune_rows]
   payload={"schema_version":3,"status":"ok","generated_at":generated,"department":dep,"columns":ref,"points":dep_points,"communes":dep_rows,"forecast":forecasts[dep]}
   text=json.dumps(payload,ensure_ascii=False,separators=(",",":"));(output/"departements"/f"{dep}.json").write_text(text,encoding="utf-8");department_index[dep]={"file":f"departements/{dep}.json","communes":len(dep_rows),"points":len(dep_points),"bytes":len(text.encode())}
  index={"schema_version":3,"status":"ok","generated_at":generated,"model":{"name":"UKMO Global 10 km","provider":"Met Office","dataset":"Global Deterministic 10 km — AWS Open Data","resolution_km":10,"forecast_hours_requested":168,"run_time":run_iso(run),"pipeline_version":VERSION,"source_url":BASE,"license":"CC BY-SA — Powered by Met Office data"},"coverage":{"label":"France métropolitaine et Corse","communes":len(communes),"departments":len(DEPS)},"diagnostics":{"native_steps_hours":STEPS,"hourly_interpolated_after":54,"unavailable":[name for name in ref["values"] if name not in ("precipitation_mm","precipitation_total_mm")]},"departments":department_index}
  index['maps']={'status':'ready','manifest':'maps/manifest.json','count':60,'coverage':'France et Europe'}
  available={ref['values'][col] for col in TABLE_COLUMNS.values()}|{'precipitation_mm','precipitation_total_mm','condition_code'}
  index['diagnostics']['unavailable']=[name for name in ref['values'] if name not in available]
  index['diagnostics']['gust_period_hours']=[None]+[period(h) for h in range(1,169)]
  index['diagnostics']['note']='Température à 1,5 m. Champs instantanés interpolés après +54 h ; précipitations réparties sur 3 h puis 6 h ; rafales maximales répétées sur leur période native, jamais interpolées. Temps indicatif dérivé des nuages et précipitations, sans diagnostic de phase pluie/neige. Rafales à H+0 indisponibles.'
  (output/"index.json").write_text(json.dumps(index,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
  print(f"UKMO {run_iso(run)} : {len(communes)} communes, {len(grid)} points, 169 échéances.")

if __name__=="__main__":
 parser=argparse.ArgumentParser();parser.add_argument("--catalog",default="config/communes-france.json");parser.add_argument("--output-dir",default="build/national");parser.add_argument("--repository",default="alertesmeteo-hub/UKMO-GLOBAL-10-km");parser.add_argument("--force",action="store_true");args=parser.parse_args()
 build(args.catalog,args.output_dir,args.repository,args.force)
