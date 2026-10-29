"""Deterministic provider mock of FRESH -> cross-branch FUSE/CHALLENGE -> TOOL -> HOLD.

This demonstrates execution/provenance only. It does not verify scientific novelty.
"""
from __future__ import annotations
import argparse, json, pathlib, os
from unittest.mock import patch
from .long_campaign import prepare_isolated_fresh
from .core import EvolutionJournal
from .provider import DurableModel
from .engine import Engine
from .e3r1_portfolio_audit import audit


def work(wid,op,aid=(),q=None):
    return {'id':'EV_'+wid,'operation':op,'asset_ids':list(aid),
            'reason':'Deterministic toy research, no empirical inference',
            'work':{'id':wid,'mode':'FRESH' if op=='FRESH' else 'INFORMED','problem_id':'P0',
            'question':q or 'Synthetic problem '+wid,'research_rationale':'Scripted test without scientific claims','source_ids':[]}}

def asset(aid,kind,parents=()):
    return {'id':aid,'kind':kind,'problem_id':'P0','claim':'Synthetic '+aid,
            'assumptions':'No empirical meaning','scope':'toy only','predictions':['Synthetic discriminating measurement'],
            'limitations':['Not real physics'],'source_ids':[],'parent_ids':list(parents),
            'delta_from_parents':'New toy sign prediction after parent comparison' if parents else ''}

def assess(hold=False):
    return {'objective_status':'UNRESOLVED','research_status':'PAUSED_LOW_INFORMATION' if hold else 'CONTINUING',
            'objective_coverage':'NO_OBJECTIVE_RESULT','resolved_scope':'No real result',
            'supporting_asset_ids':[],'remaining_questions':['Real problem untested'],
            'untried_approaches_considered':['No real scientific experiment'],
            'reason':'Mock test only; no scientific result'}

def port(ids,action,reason):
    return {'work_ids':list(ids),'action':action,'assessment':'WAIT_NEW_EVIDENCE' if action=='DEFER' else 'OTHER',
            'rationale':reason,'evidence_asset_ids':[]}

class ScriptedProvider:
    def __call__(self,wire,timeout=180):
        u=json.loads(json.loads(wire)['messages'][1]['content'])
        if 'pinned_input' in u:
            wid=u['pinned_input']['work']['id']; prior=u['own_prior_steps']
            if wid=='W_A':a=asset('A_H','HYPOTHESIS')
            elif wid=='W_B':a=asset('A_N','NULL_MODEL')
            elif wid=='W_C':a=asset('A_C','COUNTEREXAMPLE',['A_H'])
            elif wid=='W_F':
                if not any(x['kind']=='TOOL_RESULT' for x in prior):
                    obj={'scientific_text':'Request a genuine computed toy value',
                         'next_action':'CONTINUE','assets':[],'new_problems':[],
                         'tool_request':{'kind':'verified_calculation','arguments':{'expressions':{'sum':'x+y'},'scenarios':[{'x':2,'y':3}]}}}
                    return json.dumps({'choices':[{'message':{'content':json.dumps(obj)}}]}).encode()
                a=asset('A_F','PREDICTION',['A_H','A_N'])
            else:raise AssertionError('Unexpected scheduled mock work '+wid)
            obj={'scientific_text':'A scripted toy scientific sentence','next_action':'RETURN',
                 'assets':[a],'new_problems':[],'tool_request':None}
        else:
            aids={x['id'] for x in u['assets']}
            if not aids:
                actions=[work('W_A','FRESH'),work('W_B','FRESH'),work('W_UNUSED','FRESH')];ports=[];hold=False
            elif 'A_H' in aids and 'A_N' in aids and 'A_C' not in aids:
                actions=[work('W_F','FUSE',['A_H','A_N']),work('W_C','CHALLENGE',['A_H'])]
                ports=[port(['W_UNUSED'],'DEFER','Factual mock duplicate, no information gain')];hold=False
            elif 'A_F' in aids:
                actions=[];ports=[port(['W_UNUSED'],'KEEP','Preserve unexecuted idea for later independent study')];hold=True
            else:actions=[];ports=[];hold=False
            obj={'rationale':'Science-neutral deterministic portfolio decision',
                 'new_problems':[],'reviews':[],'actions':actions,
                 'portfolio_decisions':ports,
                 'disposition':'HOLD_WITH_RATIONALE' if hold else 'ONGOING',
                 'unresolved_opportunities':['Independent science still needed'],
                 'objective_assessment':assess(hold)}
        return json.dumps({'choices':[{'message':{'content':json.dumps(obj)}}]}).encode()

def run(root):
    root=pathlib.Path(root)
    problem=root.parent/'e3r1_mock_problem.txt'
    problem.write_text('Synthetic SERS-like toy problem. This is not a scientific research result.\n')
    prepare_isolated_fresh(root,problem)
    j=EvolutionJournal(root)
    gw=DurableModel(j,provider=ScriptedProvider(),approved=True,max_new_calls=25,mode='MOCK')
    engine=Engine(j,gw)
    with patch.dict(os.environ,{"FAKG_RESEARCH_ALLOW_PAID":"YES"}):
        result=engine.run(max_iterations=15,max_parallel=2)
    s=j.verify()
    assert result['status']=='SCIENTIFIC_DISPOSITION_PROPOSED', result
    assert s.work['W_UNUSED']['status']=='DEFERRED'
    assert s.work['W_F']['status']=='DONE' and s.work['W_C']['status']=='DONE'
    assert s.assets['A_F']['parent_ids']==['A_H','A_N']
    assert len(s.tool_results)==1
    assert s.objective_assessments[-1]['research_status']=='PAUSED_LOW_INFORMATION'
    assert not any(c.get('billing_mode')=='EXTERNAL' for c in s.model_calls.values())
    return {'status':'E3R1_MOCK_SUCCESS_NOT_SCIENTIFIC_DISCOVERY','root':str(root),
            'works':len(s.work),'assets':len(s.assets),'controller_decisions':len(s.controller_decisions),
            'tool_results':len(s.tool_results),'journal_events':len(j._events()),
            'program_hold':s.program_reviews[-1]['scientific_status'],
            'portfolio_decisions':audit(root)['portfolio_assessment_events']}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out');a=ap.parse_args()
    result=run(a.root)
    if a.out:pathlib.Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
