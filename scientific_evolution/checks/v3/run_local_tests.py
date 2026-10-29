#!/usr/bin/env python3
from pathlib import Path
import sys,unittest
here=Path(__file__).parent
sys.path.insert(0,str(here))
sys.path.insert(0,str(here.parent))
import bootstrap
suite=unittest.defaultTestLoader.discover(str(here),pattern='test_v3_continuation.py')
res=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not res.wasSuccessful())
