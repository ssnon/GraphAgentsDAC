"""Only local test stubs for tools absent from the user's source-only ZIP.
No production tool or source is replaced when importing V4 in user's WSL.
"""
import importlib.util,sys,types,os
from pathlib import Path
source=os.environ.get('V4_LOCAL_SOURCE_ROOT')
if source:sys.path.insert(0,source)
# The local test ZIP includes 6 source files but not optional E2 native tools.
for name,objects in {
  'e2core.verified_science':{'verify_calculation':lambda *_:None,'ScienceInputError':ValueError},
  'e2core.science_sandbox':{'run_science_python':lambda *_a,**_k:None},
  'e2core.literature':{'crossref_lookup':lambda *_:None},
  'e2core.research_literature':{'research_literature':lambda *_:None},
  'e2core.research_context':{'research_capability_state':lambda *_a,**_k:{},
    'research_worker_context':lambda *_a,**_k:{}},
}.items():
 try: found=importlib.util.find_spec(name)
 except ModuleNotFoundError:found=None
 if found is None:
  m=types.ModuleType(name)
  for k,v in objects.items():setattr(m,k,v)
  sys.modules[name]=m
if importlib.util.find_spec('science_frontier_campaign') is None:
 m=types.ModuleType('science_frontier_campaign');m.OPPORTUNITY_PROMPT='Test opportunity JSON'
 m.validate_opp=lambda obj,aug:obj
 sys.modules[m.__name__]=m
