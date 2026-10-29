"""Scripted live-path mock: real journal + provider bridge + parallel worker + replay."""
from __future__ import annotations
import json
from .core import EvolutionJournal, EvidenceError
from .engine import Engine
from .provider import DurableModel

class ScriptedProvider:
    def __init__(self):self.controller_count=0;self.worker_count={};self.requests=[]
    def __call__(self,wire,timeout=180):
        obj=json.loads(wire);prompt=obj['messages'][0]['content'];inp=json.loads(obj['messages'][1]['content']);self.requests.append(obj)
        if 'evolution controller' in prompt:
            self.controller_count+=1
            if self.controller_count==1:
                actions=[
                   {'id':'E_FA','operation':'FRESH','asset_ids':[],'reason':'Independent toy exploration','work':{'id':'WA','mode':'FRESH','problem_id':'P0','question':'Find toy H','research_rationale':'Independent toy scenario','source_ids':[]}},
                   {'id':'E_FB','operation':'FRESH','asset_ids':[],'reason':'Independent toy null','work':{'id':'WB','mode':'FRESH','problem_id':'P0','question':'Find toy N','research_rationale':'Independent toy scenario','source_ids':[]}}]
                out={'rationale':'Two independent toy inquiries; not real evidence','actions':actions,'new_problems':[], 'reviews':[], 'disposition':'ONGOING','unresolved_opportunities':['Need actual evaluation']}
            elif self.controller_count==2:
                assets={a['id'] for a in inp['assets']}
                if not {'H1','N1'}.issubset(assets):
                    raise AssertionError('Expected both independent mock findings before fusion')
                actions=[
                  {'id':'E_DEV','operation':'DEVELOP','asset_ids':['H1'],'reason':'Narrow toy H','work':{'id':'WC','mode':'INFORMED','problem_id':'P0','question':'Develop H1 condition','research_rationale':'Limit assumptions','source_ids':[]}},
                  {'id':'E_FUSE','operation':'FUSE','asset_ids':['H1','N1'],'reason':'Find discriminating toy prediction','work':{'id':'WD','mode':'INFORMED','problem_id':'P0','question':'Fuse toy mechanisms','research_rationale':'Test against a rival','source_ids':[]}}]
                out={'rationale':'Actual indexed findings led to new toy research','actions':actions,'new_problems':[], 'reviews':[], 'disposition':'ONGOING','unresolved_opportunities':['Need parameter test']}
            else:
                assets={a['id'] for a in inp['assets']}
                assert {'H2','F1'}.issubset(assets)
                out={'rationale':'No new evidence; planned toy studies have narrowed claims','actions':[], 'new_problems':[],
                     'reviews':[{'id':'H1','decision':'RESTRICTED','rationale':'H2 narrows the toy statement'}],
                     'disposition':'HOLD_WITH_RATIONALE','unresolved_opportunities':['Independent test of toy predictions']}
        else:
            wid=inp['pinned_input']['work']['id']
            self.worker_count[wid]=self.worker_count.get(wid,0)+1
            if wid=='WA':asset={'id':'H1','kind':'HYPOTHESIS','problem_id':'P0','claim':'Toy mechanism H may explain toy data','assumptions':'fictional coefficient','scope':'only toy system','predictions':['toy observable'],'limitations':['unverified'],'parent_ids':[],'delta_from_parents':''}
            elif wid=='WB':asset={'id':'N1','kind':'NULL_MODEL','problem_id':'P0','claim':'Toy null N produces same toy mean','assumptions':'fictional noise','scope':'only toy system','predictions':['toy mean'],'limitations':['unverified'],'parent_ids':[],'delta_from_parents':''}
            elif wid=='WC':asset={'id':'H2','kind':'HYPOTHESIS','problem_id':'P0','claim':'Toy H survives only in a narrow regime','assumptions':'fictional small parameter','scope':'small parameter only','predictions':['conditional response'],'limitations':['unverified'],'parent_ids':['H1'],'delta_from_parents':'Restricts H1 to a narrower physical range'}
            else:asset={'id':'F1','kind':'PREDICTION','problem_id':'P0','claim':'Toy H1 and N1 differ under a hypothetical perturbation','assumptions':'fictional stimulus','scope':'toy simulation','predictions':['different response'],'limitations':['unverified'],'parent_ids':['H1','N1'],'delta_from_parents':'Combines competing mechanisms into a discrimination design'}
            out={'scientific_text':'Synthetic toy science, not measured','next_action':'RETURN','assets':[asset],'new_problems':[],'tool_request':None}
        return json.dumps({'choices':[{'message':{'content':json.dumps(out,ensure_ascii=False)}}],'usage':{'total_tokens':42}}).encode()

def run_demo(root):
    j=EvolutionJournal(root);j.init('SYNTHETIC DEMO toy problem, NOT science',origin='E2_SCRIPTED_MOCK')
    p=ScriptedProvider()
    # Provider injected, no network/no real key; isolated approval only for this explicit test.
    import os
    previous=os.environ.get('FAKG_RESEARCH_ALLOW_PAID')
    os.environ['FAKG_RESEARCH_ALLOW_PAID']='YES'
    try:
        model=DurableModel(j,provider=p,approved=True,max_new_calls=12,mode='MOCK')
        engine=Engine(j,model)
        result=engine.run(max_iterations=4,max_parallel=2)
    finally:
        if previous is None:os.environ.pop('FAKG_RESEARCH_ALLOW_PAID',None)
        else:os.environ['FAKG_RESEARCH_ALLOW_PAID']=previous
    r=j.report()
    if not {'H1','N1','H2','F1'}.issubset(r['assets']):
        raise EvidenceError('SCRIPTED_DEMO_INCOMPLETE_ASSETS; inspect operational_pauses and ' +
                            'work states in the existing read-only science report: ' + str(r['root']))
    assert r['assets']['H2']['parent_ids']==['H1'] and r['assets']['F1']['parent_ids']==['H1','N1']
    assert r['program_reviews'][-1]['scientific_status']=='HOLD_WITH_RATIONALE'
    return {'status':'E2_SCRIPTED_MULTI_WAVE_COMPLETE_NOT_SCIENTIFIC_DISCOVERY','events':r['events'],
      'assets':list(r['assets']),'workers':list(r['work']),'controller_decisions':len(r['controller_decisions']),
      'provider_calls_mock_only':len(p.requests),'actual_paid_calls':0,'science_certification':False,
      'root':r['root'],'operational_status':result['status']}
