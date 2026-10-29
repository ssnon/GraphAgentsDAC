"""Generate inspectable synthetic LIVE-wired Controller/Worker evolution (ZERO paid calls)."""
import argparse, json, os
from pathlib import Path
from .core import EvolutionJournal
from .engine import Engine
from .provider import DurableModel
from .e3_evolution_audit import audit

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out');ns=ap.parse_args()
    # Clearly labelled mock fixture; not imported by real scientific provider.
    from tests.test_e3_evolution import LiveLineageMockProvider
    j=EvolutionJournal(ns.root);j.init('SYNTHETIC MODEL ONLY. NO REAL WORLD SCIENCE.','SYNTHETIC_E3_MOCK')
    j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
    # MOCK still uses both opt-in guards at the model boundary. Set only within
    # this process, restore afterwards. It uses injected offline scripted replies.
    old=os.getenv('FAKG_RESEARCH_ALLOW_PAID')
    os.environ['FAKG_RESEARCH_ALLOW_PAID']='YES'
    try:
        provider=LiveLineageMockProvider()
        gateway=DurableModel(j,provider=provider,approved=True,max_new_calls=30,mode='MOCK')
        e=Engine(j,gateway,serial_fair=True)
        result=e.run(max_iterations=25,max_parallel=1)
    finally:
        if old is None:os.environ.pop('FAKG_RESEARCH_ALLOW_PAID',None)
        else:os.environ['FAKG_RESEARCH_ALLOW_PAID']=old
    a=audit(ns.root)
    if ns.out:Path(ns.out).write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'run_status':result['status'],'root':ns.root,'model_mock_calls':gateway.new_calls,
        'paid_external_calls':0,'controller_decisions':len(j.verify().controller_decisions),
        'cross_researcher_derived_assets':a['cross_researcher_derived_asset_count'],
        'audit':ns.out,'science_discovery_verified':False},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
