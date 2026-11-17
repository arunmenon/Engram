import os,shlex,subprocess,time,socket,json,uuid,hashlib
from pathlib import Path
import httpx
ROOT=Path('/Users/arunmenon/projects/Engram');run='20261006-cloud-api-readonly-'+uuid.uuid4().hex[:8];record=ROOT/'docs/review/spanner-compatibility/runs'/run
parsed={}
for line in Path('/private/tmp/engram-spanner-token-env').read_text().splitlines():
 if any(line.startswith(p) for k in ['GOOGLE_CLOUD_PROJECT','SPANNER_INSTANCE_ID','SPANNER_DATABASE_ID','GOOGLE_OAUTH_ACCESS_TOKEN'] for p in [k+'=','export '+k+'=']):
  k,_,v=shlex.split(line)[-1].partition('=');parsed[k]=v
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
auth=uuid.uuid4().hex;env=os.environ.copy()
for k in ['SPANNER_EMULATOR_HOST','CG_SPANNER_EMULATOR_HOST']:env.pop(k,None)
env.update(PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',LITELLM_LOCAL_MODEL_COST_MAP='true',GRPC_VERBOSITY='ERROR',CG_AUTH_API_KEY=auth,CG_AUTH_ADMIN_KEY=auth,ENGRAM_COMPAT_API_PORT=str(port),CG_SPANNER_PROJECT=parsed['GOOGLE_CLOUD_PROJECT'],CG_SPANNER_INSTANCE=parsed['SPANNER_INSTANCE_ID'],CG_SPANNER_DATABASE=parsed['SPANNER_DATABASE_ID'],CG_SPANNER_CREATE_IF_MISSING='false',CG_SPANNER_ALLOW_CREATE_ON_INSTANCE='false',CG_ONTOLOGY_PACKS='pdlc',CG_INTENT_USE_LLM='false')
for k in ['EVENT_LOG','SUBSCRIPTION','GRAPH','KEYWORD_INDEX','VECTOR_INDEX']:env['CG_STORAGE_'+k]='spanner'
manifest={'kind':'real_api_readonly_smoke','commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'backend':'real_spanner','target':{k:parsed[k] for k in ['GOOGLE_CLOUD_PROJECT','SPANNER_INSTANCE_ID','SPANNER_DATABASE_ID']},'auth':'test-only explicit token SDK bootstrap; temporary localhost API/admin key','entry_point':'uvicorn context_graph.api.app:create_app factory; normal app lifespan and routes','all_storage_ports':'spanner','read_only':True,'max_seconds':90,'resource_changes':[],'model_mode':'no provider invoked; empty-session queries only','harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scenario_ids':['BOOT-01','OPS-01','MEM-01','MEM-02','MEM-03','ONT-01'],'scope':'read-only subset; not full scenario acceptance'}
p=Path('/private/tmp/engram-api-read-manifest.json');p.write_text(json.dumps(manifest));subprocess.run(['python3','scripts/track_spanner_compatibility.py','start','--run-id',run,'--manifest',str(p)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
logpath=Path('/private/tmp')/(run+'.log');results=[];process=None
try:
 with logpath.open('w') as log:
  process=subprocess.Popen(['/private/tmp/engram-ontology-review-venv/bin/python','/private/tmp/engram-cloud-api-bootstrap.py'],cwd=ROOT,env=env,stdout=log,stderr=log)
  with httpx.Client(base_url=f'http://127.0.0.1:{port}',headers={'Authorization':'Bearer '+auth},timeout=15) as client:
   for attempt in range(60):
    if process.poll() is not None:raise RuntimeError('API startup exited')
    try:
     response=client.get('/v1/health')
     if response.status_code==200:break
    except httpx.ConnectError:pass
    time.sleep(.2)
   else:raise RuntimeError('API startup deadline')
   sid='compat-empty-'+uuid.uuid4().hex
   tests=[('health','GET','/v1/health',None),('ontology','GET','/v1/ontology',None),('stats','GET','/v1/admin/stats',None),('empty_context','GET','/v1/context/'+sid,None),('missing_lineage','GET','/v1/nodes/'+uuid.uuid4().hex+'/lineage',None),('empty_subgraph','POST','/v1/query/subgraph',{'query':sid,'session_id':sid,'agent_id':'compat-readonly','max_nodes':10})]
   for name,method,url,body in tests:
    try:
     start=time.monotonic();r=client.request(method,url,json=body) if body is not None else client.request(method,url);data=r.json()
     item={'name':name,'http_status':r.status_code,'ms':round((time.monotonic()-start)*1000,1),'passed':r.status_code==200}
     if name=='health':item.update(event_log=data.get('event_log'),graph=data.get('graph'));item['passed']=item['passed'] and data.get('event_log',{}).get('backend')=='spanner' and data.get('graph',{}).get('backend')=='spanner'
     if name in ['empty_context','missing_lineage','empty_subgraph']:item['node_count']=len(data.get('nodes',{}));item['passed']=item['passed'] and item['node_count']==0
     if name=='stats':item['event_log_backend']=data.get('event_log',{}).get('backend');item['passed']=item['passed'] and item['event_log_backend']=='spanner'
     results.append(item)
    except Exception as exc:results.append({'name':name,'passed':False,'error_type':type(exc).__name__})
except Exception as exc:results.append({'name':'startup','passed':False,'error_type':type(exc).__name__})
finally:
 if process and process.poll() is None:
  process.terminate()
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:process.kill();process.wait()
 if logpath.exists():
  sanitized=logpath.read_text(errors='replace').replace(parsed['GOOGLE_OAUTH_ACCESS_TOKEN'],'[REDACTED_TOKEN]').replace(auth,'[REDACTED_API_KEY]')
  (record/'api.log').write_text(sanitized)
 (record/'observations.json').write_text(json.dumps({'checks':results,'cloud_resource_changes':[],'cleanup':'owned API process stopped','acceptance':'partial smoke only; no ingestion/workers/model providers'},indent=2)+'\n')
 p=Path('/private/tmp/engram-api-read-results.json');p.write_text(json.dumps({'scenarios':[],'summary':f'{sum(r["passed"] for r in results)} of {len(results)} read-only API subchecks passed; full scenario acceptance pending','cleanup':'owned API process stopped; no cloud resources changed','evidence':str((record/'observations.json').relative_to(ROOT))}))
 subprocess.run(['python3','scripts/track_spanner_compatibility.py','finish','--run-id',run,'--results',str(p)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
 print(json.dumps({'run_id':run,'checks':results,'cloud_resource_changes':0}))
