"""Refuse partial UKMO publications."""
import json
import sys
from pathlib import Path

def validate(root):
    root = Path(root)
    index = json.loads((root/'index.json').read_text(encoding='utf-8'))
    manifest = json.loads((root/'maps/manifest.json').read_text(encoding='utf-8'))
    assert index['model']['pipeline_version'] == manifest['pipeline_version'] == '2.1.0'
    assert manifest['model'] == 'UKMO-GLOBAL'
    assert manifest['steps'] == [24,48,72,96,120,168]
    assert set(manifest['products']) == {'temperature','precipitation','vent','rafales','nuages'}
    for product in manifest['products'].values():
        assert {(m['region'],m['lead_hour']) for m in product['maps']} == {(r,h) for r in ('france','europe') for h in manifest['steps']}
        for item in product['maps']:
            for key in ('image','vector','values'): assert (root/item[key]).stat().st_size > 100
            assert '<image' not in (root/item['vector']).read_text(encoding='utf-8')
    for extension in ('png','svg'): assert len(list((root/'maps').glob('*/*.'+extension))) == 60
    assert len(list((root/'maps').glob('*/*-values.json'))) == 60
    assert len(index['departments']) == 96
    assert index['coverage']['communes'] >= 34000
    commune_count = 0
    for dep in index['departments'].values():
        payload = json.loads((root/dep['file']).read_text(encoding='utf-8'))
        commune_count += len(payload['communes'])
        assert all(0 <= c[6] < len(payload['points']) for c in payload['communes'])
        assert len(payload['forecast']) == 169
        assert all(len(rows) == len(payload['points']) and all(len(row)==33 for row in rows) for _,rows in payload['forecast'])
    assert commune_count == index['coverage']['communes']
    print('Publication UKMO complète : 60 cartes PNG/SVG, 60 grilles et 96 départements.')

if __name__ == '__main__': validate(sys.argv[1])
