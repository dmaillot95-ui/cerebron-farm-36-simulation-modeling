import json, os, pathlib, subprocess, hashlib, time

ROLE=os.getenv('ROLE','UNKNOWN_ROLE')
MODEL=os.getenv('MODEL','huggingface-projects/llama-3.2-3B-Instruct')
FOCUS=os.getenv('FOCUS','simulation modeling')
MISSION=pathlib.Path('MISSION.md').read_text(encoding='utf-8')
PREFERRED=['/generate','/chat','/predict','/respond','/infer','/run']

def run(cmd,timeout=240):
    return subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)

def payload_for(spec,prompt):
    payload={}; prompt_set=False
    for p in spec.get('parameters',[]):
        name=p.get('name',''); lname=name.lower(); required=bool(p.get('required',False)); default=p.get('default'); typ=(p.get('type') or {}).get('type')
        if lname in {'message','prompt','text','query','input','instruction','user_message'}:
            payload[name]=prompt; prompt_set=True
        elif lname in {'chat_history','history','messages'}: payload[name]=[]
        elif lname in {'max_new_tokens','max_tokens','maximum_new_tokens'}: payload[name]=700
        elif lname=='temperature': payload[name]=0.2
        elif lname=='top_p': payload[name]=0.9
        elif lname=='top_k': payload[name]=40
        elif lname in {'system','system_prompt'}: payload[name]='REALITY > COHERENCE. CLAIM <= EVIDENCE. MODEL != REALITY. SIMULATION != TEST.'
        elif required and default is None:
            if typ=='string' and not prompt_set: payload[name]=prompt; prompt_set=True
            else: return None
    return payload if prompt_set else None

def extract(raw):
    raw=raw.strip()
    try:
        obj=json.loads(raw)
        if isinstance(obj,dict):
            for k in ('Response','response','text','output','message'):
                if isinstance(obj.get(k),str) and obj[k].strip(): return obj[k].strip()
    except Exception: pass
    return raw

def invoke(space,prompt):
    info=run(['hf-gradio','info',space],120)
    if info.returncode!=0: return False,None,{'error':info.stderr.strip() or info.stdout.strip()}
    try: api=json.loads(info.stdout)
    except Exception as e: return False,None,{'error':f'info-json:{e!r}'}
    endpoints=list(api.items()); endpoints.sort(key=lambda kv:(PREFERRED.index(kv[0]) if kv[0] in PREFERRED else 99,kv[0]))
    errors=[]
    for endpoint,spec in endpoints:
        payload=payload_for(spec,prompt)
        if payload is None: continue
        pred=run(['hf-gradio','predict',space,endpoint,json.dumps(payload,ensure_ascii=False)],240)
        if pred.returncode==0 and pred.stdout.strip():
            text=extract(pred.stdout)
            if text:
                return True,text,{'endpoint':endpoint,'sha256':hashlib.sha256(text.encode()).hexdigest()}
        errors.append({'endpoint':endpoint,'error':(pred.stderr or pred.stdout)[-1200:]})
    return False,None,{'errors':errors}

prompt=f'''You are {ROLE} in CEREBRON Ω Farm 36 Simulation & Modeling.\nFocus: {FOCUS}.\n\n{MISSION}\n\nReturn a concise auditable report with assumptions, equations/rules, units, parameters, boundary/initial conditions, numerical method, verification checks, calibration-vs-validation separation, sensitivity, uncertainty, extrapolation limits, failure modes, falsification path, and claim ledger.'''

ok,text,meta=invoke(MODEL,prompt)
out={'farm':36,'role':ROLE,'model':MODEL,'focus':FOCUS,'provider':'huggingface-space-zerogpu','inference_success':ok,'status':'UNREVIEWED_EXTERNAL_AGENT_OUTPUT' if ok else 'EXTERNAL_INFERENCE_FAILED','output':text,'meta':meta,'timestamp':int(time.time())}
pathlib.Path('results').mkdir(exist_ok=True)
pathlib.Path(f'results/{ROLE}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'role':ROLE,'status':out['status'],'inference_success':ok,'meta':meta},ensure_ascii=False))
