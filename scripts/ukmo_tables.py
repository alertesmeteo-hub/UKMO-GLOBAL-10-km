"""Hourly table conversion. Keep interval gust maxima distinct from instants."""
import numpy as np

EXTRA_FIELDS = {
    'humidity': {'variable':'relative_humidity_at_screen_level','field':'relative_humidity','unit':'1','factor':100},
    'pressure': {'variable':'pressure_at_mean_sea_level','field':'air_pressure_at_sea_level','unit':'Pa','factor':.01},
    'direction': {'variable':'wind_direction_at_10m','field':'wind_from_direction','unit':'degrees','factor':1},
}
TABLE_COLUMNS = {'temperature':0,'humidity':1,'nuages':3,'vent':4,'direction':5,'rafales':6,'pressure':7}

def extra_values(dataset, key):
    spec=EXTRA_FIELDS[key];field=dataset[spec['field']].squeeze()
    if field.attrs.get('units')!=spec['unit']:raise ValueError(f'Unité UKMO inattendue : {key}')
    values=np.asarray(field.transpose('latitude','longitude').values,dtype=float)*spec['factor']
    if not np.isfinite(values).all():raise ValueError(f'Champ UKMO incomplet : {key}')
    if key=='humidity':
        # Small oversaturation can occur in model relative humidity.
        if values.min()<0 or values.max()>110:raise ValueError('Humidité UKMO invalide')
        return np.clip(values,0,100)
    if key=='direction':
        if values.min()<0 or values.max()>360:raise ValueError('Direction UKMO invalide')
        return values%360
    if values.min()<800 or values.max()>1100:raise ValueError('Pression mer UKMO invalide')
    return values

def to_hourly(native, steps):
    """Interpolate scalars/circular directions; never interpolate gust maxima."""
    instants=[0]+list(steps);output={}
    for key,samples in native.items():
        first=next(iter(samples.values()))
        result=np.full((169,len(first)),np.nan)
        if key=='rafales':
            previous=0
            for step in steps:
                result[previous+1:step+1]=samples[step]
                previous=step
        else:
            for start,end in zip(instants,instants[1:]):
                a=np.arange(end-start+1)[:,None]/(end-start)
                lo,hi=samples[start],samples[end]
                if key=='direction':
                    delta=(hi-lo+180)%360-180
                    result[start:end+1]=(lo+a*delta)%360
                else:result[start:end+1]=(1-a)*lo+a*hi
        output[key]=result
    return output

def condition_codes(rain, cloud):
    # Indicative summary, not a direct Met Office weather/precipitation-phase code.
    return np.select([rain>=2,rain>=.1,cloud>=80,cloud>=40,cloud>=15],[6,5,4,3,2],default=1)

def make_row(fields, hour, gid, rain, total, condition):
    row=[None]*33
    for key,column in TABLE_COLUMNS.items():
        number=float(fields[key][hour,gid])
        if np.isfinite(number):row[column]=round(number,1)
    row[2]=round(float(rain),2);row[9]=int(condition);row[12]=round(float(total),1)
    return row
