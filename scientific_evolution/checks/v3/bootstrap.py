"""Local-only stubs for unavailable optional science providers.

The Journal, DurableModel, Engine and source V2 module all import from the
provided ORIGINAL source code; no production code is replaced by this fixture.
"""
import importlib.util
import sys, types
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[2]/'science_v3_source'
# For downloadable ZIP tests this fixture is optional. User's WSL already has
# complete e2core + science_frontier_campaign. Local reproducibility is provided
# by run_local_tests.py outside the portable package.
if SOURCE.is_dir():sys.path.insert(0,str(SOURCE))
if 'e2core.verified_science' not in sys.modules and not (SOURCE/'e2core/verified_science.py').exists():
 for name,values in {
  'e2core.verified_science':{'verify_calculation':lambda *_:None,'ScienceInputError':ValueError},
  'e2core.science_sandbox':{'run_science_python':lambda *_a,**_k:None},
  'e2core.literature':{'crossref_lookup':lambda *_:None},
  'e2core.research_literature':{'research_literature':lambda *_:None},
  'e2core.research_context':{'research_capability_state':lambda *_a,**_k:{},'research_worker_context':lambda *_a,**_k:{}},
 }.items():
  if importlib.util.find_spec(name) is None:
   mod=types.ModuleType(name)
   for k,v in values.items():setattr(mod,k,v)
   sys.modules[name]=mod
if importlib.util.find_spec('science_frontier_campaign') is None:
 m=types.ModuleType('science_frontier_campaign')
 m.OPPORTUNITY_PROMPT='Test stub opportunity only'
 m.validate_opp=lambda obj,augmented:obj
 sys.modules['science_frontier_campaign']=m
