import json, urllib.request
from pathlib import Path

def load_registry(categories, max_chars=14000):
    state={'loaded':False,'registry_version':None,'categories':[],'sources':[],'errors':[]}
    chunks=[]
    try:
        local=json.loads(Path('CEREBRON_REGISTRY.json').read_text(encoding='utf-8'))
        manifest_url=local['registry']
        with urllib.request.urlopen(manifest_url,timeout=15) as r:
            manifest=json.loads(r.read().decode('utf-8'))
        state['registry_version']=manifest.get('version')
        base=manifest_url.rsplit('/registry/manifest.json',1)[0]+'/'
        paths=manifest.get('paths',{})
        for cat in categories:
            rel=paths.get(cat)
            if not rel: continue
            url=base+rel
            try:
                with urllib.request.urlopen(url,timeout=15) as r:
                    text=r.read().decode('utf-8')
                remaining=max_chars-sum(len(x) for x in chunks)
                if remaining<=0: break
                text=text[:remaining]
                chunks.append(f'\n### {cat}\n{text}')
                state['categories'].append(cat); state['sources'].append(url)
            except Exception as e:
                state['errors'].append({'category':cat,'error':repr(e)})
        state['loaded']=bool(chunks)
    except Exception as e:
        state['errors'].append({'stage':'manifest','error':repr(e)})
    return '\n'.join(chunks), state
