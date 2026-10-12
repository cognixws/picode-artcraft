#!/usr/bin/env python3
"""Static package/manifest and captured-schema compatibility checks."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
from catalog import APPS

root = Path(__file__).resolve().parents[1]
m = json.loads((root/'picode-extension.json').read_text())
assert set(m['agent']['mcpServers']) == set(APPS)
assert len(m['contributes']['openWith']) <= 16
assert len(m['activation']['files']) <= 8
ports = [s['port'] for s in APPS.values() if s['port']]
assert len(ports) == len(set(ports))
for name, spec in APPS.items():
    assert (root/'skills'/name/'SKILL.md').is_file(), name
    tools = json.loads((root/'server/tools'/(name+'.json')).read_text())['tools']
    names = [t['name'] for t in tools]
    assert len(names) == len(set(names)), name
    assert not spec['probe'] or spec['probe'] in names, (name, spec['probe'])
    if spec.get('openTool'): assert spec['openTool'] in names, name
    for tool in spec['paths']: assert tool in names, (name, tool)
for name in ['wordcraft', 'deckcraft', 'gridcraft']:
    index = (root/'skills'/name/'references/tools.tsv').read_text()
    assert all(len(line.split('\t')) == 3 and line == line.rstrip() for line in index.splitlines()), name
for path in m['agent']['skills']: assert (root/path/'SKILL.md').is_file()
for path in ['apps.js','apps.css','domain.js']: assert (root/'ui'/path).is_file()
print('Catalog, manifest limits, skills and captured schemas: PASS')
