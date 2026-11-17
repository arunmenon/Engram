import os,shlex
from pathlib import Path
from google.cloud import spanner
from google.oauth2.credentials import Credentials
for line in Path('/private/tmp/engram-spanner-token-env').read_text().splitlines():
 if not any(line.startswith(p) for k in ['GOOGLE_CLOUD_PROJECT','SPANNER_INSTANCE_ID','SPANNER_DATABASE_ID','GOOGLE_OAUTH_ACCESS_TOKEN'] for p in [k+'=','export '+k+'=']):continue
 k,_,v=shlex.split(line)[-1].partition('=');os.environ[k]=v
original=spanner.Client
credentials=Credentials(token=os.environ['GOOGLE_OAUTH_ACCESS_TOKEN'])
def authenticated_client(*args,**kwargs):
 kwargs['credentials']=credentials;return original(*args,**kwargs)
spanner.Client=authenticated_client
import uvicorn
uvicorn.run('context_graph.api.app:create_app',factory=True,host='127.0.0.1',port=int(os.environ['ENGRAM_COMPAT_API_PORT']),log_level='warning')
