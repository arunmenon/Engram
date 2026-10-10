import ast,json,subprocess,pathlib
out=pathlib.Path('docs/review/spanner-compatibility/runs/20261010-memory-producer-rca')
def git(*args):return subprocess.run(['git',*args],text=True,capture_output=True,check=True).stdout
names={'BeliefNode','GoalNode','EpisodeNode','merge_belief_node','merge_goal_node','merge_episode_node','merge_belief_nodes_batch','merge_goal_nodes_batch','merge_episode_nodes_batch','write_belief_node','write_goal_node','write_episode_node'}
refs=git('for-each-ref','--format=%(refname)','refs/heads','refs/remotes/origin').splitlines()
refs += ['d49ded4','797f799','b4a94d9','0507231']
report=[]
for ref in refs:
 if ref.endswith('/HEAD'):continue
 sha=git('rev-parse',ref).strip()
 matches=subprocess.run(['git','grep','-l','-E','BeliefNode|GoalNode|EpisodeNode|merge_(belief|goal|episode)_node|write_(belief|goal|episode)_node',sha,'--','src'],text=True,capture_output=True)
 files=[line.split(':',1)[1] for line in matches.stdout.splitlines() if line.endswith('.py')]
 calls=[];definitions=[];errors=[]
 for f in files:
  try:tree=ast.parse(git('show',sha+':'+f))
  except SyntaxError as e:errors.append({'file':f,'error':str(e)});continue
  for n in ast.walk(tree):
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n.name in names:definitions.append({'file':f,'line':n.lineno,'symbol':n.name})
   if isinstance(n,ast.Call):
    name=n.func.id if isinstance(n.func,ast.Name) else n.func.attr if isinstance(n.func,ast.Attribute) else ''
    if name in names:calls.append({'file':f,'line':n.lineno,'symbol':name})
 report.append(dict(ref=ref,commit=sha,matching_files=files,definitions=definitions,calls=calls,parse_errors=errors))
history=git('log','--all','--format=%H %s','-G',r'BeliefNode\(|GoalNode\(|EpisodeNode\(|merge_(belief|goal|episode)_node\(','--','src/context_graph/worker','src/context_graph/api')
(out/'source-call-audit.json').write_text(json.dumps(dict(scope='Fetched available local/origin refs plus four historical anchors; src Python direct constructor/writer calls. Does not cover external producers, unavailable branches, dynamic dispatch or direct Cypher outside matching files.',refs=report,worker_api_history_matches=history.splitlines()),indent=2)+'\n')
print('Refs inspected:',len(report),'Direct calls:',sum(len(r['calls']) for r in report),'Parse errors:',sum(len(r['parse_errors']) for r in report),'Worker/API historical matches:',len(history.splitlines()))
