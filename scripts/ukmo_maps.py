"""Fixed PNG and vector SVG maps from official Met Office NetCDF fields."""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np

REGIONS = {"france": (-6., 10.5, 41., 52.), "europe": (-25., 45., 30., 72.)}
MAP_STEPS = (24, 48, 72, 96, 120, 168)
PRODUCTS = {
    "temperature": {"label": "Température sous abri à 1,5 m", "unit": "°C",
                    "variable": "temperature_at_screen_level", "field": "air_temperature",
                    "levels": np.arange(-30,43,3), "cmap": "turbo"},
    "precipitation": {"label": "Précipitations cumulées depuis le run", "unit": "mm",
                      "levels": np.array([.1,1,2,5,10,15,20,30,40,50,70,100,150,200]), "cmap":"turbo"},
    "vent": {"label": "Vent à 10 m", "unit": "km/h", "variable": "wind_speed_at_10m", "field": "wind_speed",
             "levels": np.arange(0,121,5), "cmap":"viridis"},
    "rafales": {"label": "Rafales maximales sur la période", "unit": "km/h", "field": "wind_speed_of_gust",
                "levels": np.arange(0,181,5), "cmap":"turbo"},
    "nuages": {"label": "Couverture nuageuse totale", "unit": "%", "variable": "cloud_amount_of_total_cloud", "field": "cloud_area_fraction",
               "levels": np.arange(0,110,10), "cmap":"Blues"},
}

def field_values(dataset, product):
    spec = PRODUCTS[product]
    field = dataset[spec["field"]].squeeze()
    values = np.asarray(field.transpose("latitude", "longitude").values, dtype=float)
    units = str(field.attrs.get("units", "")).strip()
    if not np.isfinite(values).all(): raise ValueError("Champ UKMO incomplet")
    if product == "temperature":
        if units != "K": raise ValueError("Unité de température UKMO inattendue")
        if float(dataset["height"]) != 1.5: raise ValueError("Hauteur de température UKMO inattendue")
        return values - 273.15
    if product in ("vent", "rafales"):
        if units not in ("m s-1", "m s**-1"): raise ValueError("Unité de vent UKMO inattendue")
        if float(dataset["height"]) != 10: raise ValueError("Hauteur du vent UKMO inattendue")
        return values * 3.6
    if units != "1" or values.min() < 0 or values.max() > 1.001: raise ValueError("Fraction nuageuse UKMO invalide")
    return np.clip(values * 100, 0, 100)

def _draw_boundaries(ax, config_dir: Path):
    import shapefile
    for name, width in (("ne_50m_coastline", .55), ("ne_50m_admin_0_boundary_lines_land", .4)):
        reader = shapefile.Reader(str(config_dir / "natural-earth" / name))
        for shape in reader.shapes():
            west, east = ax.get_xlim(); south, north = ax.get_ylim()
            if shape.bbox[2] < west or shape.bbox[0] > east or shape.bbox[3] < south or shape.bbox[1] > north:
                continue
            points = np.asarray(shape.points)
            if not len(points):
                continue
            parts = list(shape.parts) + [len(points)]
            for start, end in zip(parts, parts[1:]):
                ax.plot(points[start:end, 0], points[start:end, 1], color="#4d5558", linewidth=width, zorder=3)


def _render(lon, lat, values, product, region, run, step, output, config_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    spec = PRODUCTS[product]
    west, east, south, north = REGIONS[region]
    fig, ax = plt.subplots(figsize=(12, 8.2), dpi=150)
    cmap = plt.get_cmap(spec["cmap"]).copy()
    if product == "precipitation":
        cmap = ListedColormap(['#dcecf9', '#b6daf3', '#80b9ec', '#438bdf', '#16bfc7',
                               '#35cb75', '#8bdc32', '#e9ee28', '#ffcd27', '#ff8b22',
                               '#f4432c', '#c92368', '#ad19bf']).with_extremes(under='#f4f8fc', over='#751499')
    norm = BoundaryNorm(spec["levels"], cmap.N)
    ix = np.flatnonzero((lon >= west - 1) & (lon <= east + 1))
    iy = np.flatnonzero((lat >= south - 1) & (lat <= north + 1))
    # Isobands interpolate display geometry, never the values served to the probe.
    mesh = ax.contourf(lon[ix], lat[iy], values[np.ix_(iy, ix)], levels=spec["levels"],
                       cmap=cmap, norm=norm, extend="both", antialiased=False)
    ax.set(xlim=(west, east), ylim=(south, north))
    _draw_boundaries(ax, config_dir)
    ax.set(xlim=(west, east), ylim=(south, north), xlabel="", ylabel="")
    # Un degré de longitude se resserre avec la latitude. Ce rapport évite
    # l'Europe écrasée et la France artificiellement étirée.
    ax.set_aspect(1.0 / np.cos(np.deg2rad((south + north) / 2.0)))
    ax.set_xticks([]); ax.set_yticks([])
    run_dt = datetime.strptime(run, "%Y%m%d%H").replace(tzinfo=timezone.utc)
    ax.set_title(f"UKMO Global 10 km — {spec['label']} ({spec['unit']})\nRun {run_dt:%d/%m/%Y %H} UTC · H+{step}", fontsize=12, fontweight="bold")
    bar = fig.colorbar(mesh, ax=ax, orientation="vertical", pad=.015, fraction=.035)
    bar.set_label(spec["unit"], fontweight="bold")
    ax.set_anchor('C')
    fig.text(.5, .06, "www.alertes-meteo.com", ha="center", va="bottom",
            fontsize=8, color="#f04444", fontweight="bold",
            bbox={"facecolor": "#111", "alpha": .94, "edgecolor": "none", "pad": 4})
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.text(.5, .022, 'Powered by Met Office data · CC BY-SA', ha='center', fontsize=7, color='#48545a')
    fig.canvas.draw()
    position = ax.get_position()
    plot_box = [round(position.x0, 6), round(1.0 - position.y1, 6),
                round(position.width, 6), round(position.height, 6)]
    fig.savefig(output, facecolor="white")
    if bar.solids is not None: bar.solids.set_rasterized(False)
    fig.savefig(output.with_suffix(".svg"), facecolor="white")
    plt.close(fig)
    return plot_box



class MapWriter:
    def __init__(self, lat, lon, run, output, config):
        self.lat, self.lon = np.asarray(lat), np.asarray(lon)
        self.run, self.output, self.config = run, Path(output), Path(config)
        self.entries = {key: [] for key in PRODUCTS}
        self.regions = {}
        normalized = (self.lon + 180) % 360 - 180
        for region, (w,e,s,n) in REGIONS.items():
            ix = np.flatnonzero((normalized >= w-1) & (normalized <= e+1))
            ix = ix[np.argsort(normalized[ix])]
            iy = np.flatnonzero((self.lat >= s-1) & (self.lat <= n+1))
            iy = iy[np.argsort(self.lat[iy])]
            if len(ix)<2 or len(iy)<2: raise ValueError("Domaine UKMO absent")
            self.regions[region] = {"ix":ix, "iy":iy, "lons":normalized[ix], "lats":self.lat[iy],
                                    "total":np.zeros((len(iy),len(ix)))}

    def add_rain(self, values, step):
        for region, grid in self.regions.items():
            grid["total"] += values[np.ix_(grid["iy"], grid["ix"])]
            if step in MAP_STEPS: self.write("precipitation", region, grid["total"], step, 0)

    def add_field(self, values, product, step, start):
        for region, grid in self.regions.items():
            self.write(product, region, values[np.ix_(grid["iy"], grid["ix"])], step, start)

    def write(self, product, region, values, step, start):
        grid = self.regions[region]
        relative = f"maps/{region}/{product}-{step:03d}h.png"
        probe = relative.replace(".png", "-values.json")
        box = _render(grid["lons"], grid["lats"], values, product, region,
                      self.run.strftime("%Y%m%d%H"), step, self.output/relative, self.config)
        data = {"bounds": list(REGIONS[region]), "lons":np.round(grid["lons"],5).tolist(),
                "lats":np.round(grid["lats"],5).tolist(), "values":np.round(values,1).tolist()}
        (self.output/probe).write_text(json.dumps(data, separators=(",",":"), allow_nan=False), encoding="utf-8")
        iso = lambda h: (self.run+timedelta(hours=h)).isoformat()
        self.entries[product].append({"region":region, "lead_hour":step, "image":relative,
                                      "vector":relative.replace(".png",".svg"), "values":probe, "plot_box":box,
                                      "start_time":iso(start), "end_time":iso(step), "period_hours":step-start})

    def finish(self):
        for key, entries in self.entries.items():
            if len(entries) != len(MAP_STEPS)*len(REGIONS): raise ValueError(f"Cartes incomplètes : {key}")
        manifest = {"model":"UKMO-GLOBAL", "pipeline_version":"2.1.0", "resolution_km":10,
                    "run":self.run.strftime("%Y%m%d%H"), "steps":list(MAP_STEPS),
                    "products":{k:{"label":v["label"],"unit":v["unit"],"maps":self.entries[k]} for k,v in PRODUCTS.items()}}
        (self.output/"maps"/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        return manifest
