import hashlib,json
from pathlib import Path
from google.cloud import spanner
from google.oauth2.credentials import Credentials
from engram_composition_assessment import token
from engram_experiment_support import fingerprint,read_owner,snapshot,durable_json
root=Path.cwd(); primary=root/'docs/review/spanner-compatibility/runs/tenant-isolation-1014-03'; run=root/'docs/review/spanner-compatibility/runs/tenant-isolation-1014-restart-01'
result=json.loads((primary/'results.json').read_text());restart=json.loads((run/'restart-results.json').read_text())
assert result['state']=='scenarios-passed-awaiting-fenced-restart-verification' and restart['state']=='passed'
assert not result['shutdown_errors'] and not restart['shutdown_errors']
assert all(c['passed'] for c in result['checks']+restart['checks'])
source=json.loads((run/'source-hashes.json').read_text())
assert all(hashlib.sha256((root/k).read_bytes()).hexdigest()==v for k,v in source.items())
client=spanner.Client(project='portiq-mvp',credentials=Credentials(token(impersonate=True)))
main_sources=json.loads((primary/'source-hashes.json').read_text())
assert all(hashlib.sha256((root/k).read_bytes()).hexdigest()==v for k,v in main_sources.items() if k!='scripts/engram_tenant_isolation_demo.py')
assert hashlib.sha256((primary/'runner-original.py').read_bytes()).hexdigest()==main_sources['scripts/engram_tenant_isolation_demo.py']
summary={'audit_passed':True,'main_run':primary.name,'continuation_run':run.name,'source_hashes_matched':len(source),'main_assertions':len(result['checks']),'restart_assertions':len(restart['checks']),'targets':{}}
groups={}
for t in ['a','b']:
 expected=json.loads((run/(t+'-final-retained.json')).read_text())
 db=client.instance('engram-experiment').database(expected['database'].rsplit('/',1)[1]);db.reload()
 owner=read_owner(db);fp=fingerprint(db);observed=snapshot(db)
 assert owner==expected['owner'] and fp==expected['fingerprints'] and observed==expected['snapshot']
 assert list(db.ddl_statements)==json.loads((run/(t+'-schema-before.json')).read_text())
 assert not observed['pending'] and not observed['dead_letters']
 with db.snapshot(multi_use=True) as snap:
  raw={}
  for table in [*fp,'TenantControl']:
   response=snap.execute_sql('SELECT * FROM '+table);rows=[list(row) for row in response]
   raw[table]={'columns':[field.name for field in response.fields],'rows':rows}
  groups[t]={row[0] for row in snap.execute_sql('SELECT group_name FROM ConsumerGroups')}
 exported=json.loads(json.dumps(raw,default=str))
 durable_json(run/(t+'-independent-raw-tables.json'),exported)
 stats=next(r['output'] for r in result['requests'] if r['tenant']==t and r['path']=='/v1/admin/stats' and r['status']==200)
 assert stats['event_log']['length']==(9 if t=='a' else 12)
 verify=json.loads((primary/(t+'-previous-export.verified.json')).read_text())
 assert verify['verified'] and hashlib.sha256((primary/(t+'-previous-export.json')).read_bytes()).hexdigest()==verify['sha256']
 summary['targets'][t]={'database':db.name,'owner':owner,'fingerprints':fp,'snapshot_matches':True,'schema_unchanged':True,'export_verified':True,'admin_stats_own_event_count':stats['event_log']['length']}
assert groups['a']==groups['b'] and len(groups['a'])==5
summary['same_group_names_in_both_databases']=sorted(groups['a'])
summary['mismatched_startup_passed']=json.loads((primary/'mismatched-startup.json').read_text())['passed'];assert summary['mismatched_startup_passed']
summary['old_epoch_startup_refused']=json.loads((primary/'old-epoch-startup-refused.json').read_text())['passed'];assert summary['old_epoch_startup_refused']
durable_json(run/'independent-post-process-audit.json',summary)
print(json.dumps({'accepted':True,'main':summary['main_assertions'],'restart':summary['restart_assertions'],'sources':len(source),'counts':{t:{k:v['count'] for k,v in info['fingerprints'].items()} for t,info in summary['targets'].items()}},indent=2))
client.close()
