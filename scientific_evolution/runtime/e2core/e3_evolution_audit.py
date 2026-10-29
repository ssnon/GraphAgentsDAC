"""Read-only, evidence-linked cross-researcher evolution audit.

A lineage witness proves only recorded reuse and parent-child deltas. It does NOT
certify novelty, actual causality, correctness, or a Level-II scientific result.
"""
from __future__ import annotations
import argparse, json, pathlib
from .core import EvolutionJournal


def audit(root):
    j=EvolutionJournal(root);s=j.verify();events=j._events()
    seq_lookup={}; intent_lookup={};source_lookup={}
    for e in events:
        if e['kind']=='ASSET_PUBLISHED':seq_lookup[e['payload']['id']]=e['seq']
        if e['kind']=='EVOLUTION_APPLIED':intent_lookup[e['payload']['id']]=e['seq']
        if e['kind']=='SOURCE_REGISTERED':source_lookup[e['payload']['id']]=e['seq']
    steps=[];reviewed=set();changed_by_worker=[]
    for evo in s.evolution:
        wid=evo['work_id'];w=s.work[wid]
        input_assets=evo['asset_ids'];new_assets=[s.assets[a] for a in w['published']]
        inherited_parent_work_ids=sorted({s.assets[a].get('work_id') or s.assets[a].get('origin','HISTORICAL') for a in input_assets})
        new_child_assets=[]
        for a in new_assets:
            exact_parents=[p for p in a.get('parent_ids',[]) if p in input_assets]
            if exact_parents:
                new_child_assets.append({'id':a['id'],'kind':a['kind'],'parent_ids':exact_parents,
                    'delta_from_parents':a.get('delta_from_parents',''),
                    'claim':a['claim'],'scope':a['scope'],'predictions':a.get('predictions',[]),
                    'limitations':a.get('limitations',[]),'source_ids':a.get('source_ids',[]),
                    'origin_event_seq':seq_lookup.get(a['id']),
                    'authored_claim_certification':a.get('certification','UNVERIFIED')})
        parents_precede_assignment=all(seq_lookup.get(a,0) < intent_lookup.get(evo['id'],0) for a in input_assets if a in seq_lookup)
        published_after_assignment=all(seq_lookup.get(a['id'],0)>intent_lookup.get(evo['id'],0) for a in new_assets)
        parent_source_kinds={src:s.sources[src]['kind'] for a in input_assets for src in s.assets[a].get('source_ids',[]) if src in s.sources}
        model_calls=[c for c in s.model_calls.values() if c.get('work_id')==wid]
        real_saved=sum(c.get('billing_mode')=='EXTERNAL' and c['state']=='SAVED' for c in model_calls)
        mock_saved=sum(c.get('billing_mode')=='MOCK' and c['state']=='SAVED' for c in model_calls)
        rec={'operation_id':evo['id'],'operation':evo['operation'],'origin_work_id':wid,
             'origin_mode':w['mode'],'origin_status':w['status'],'input_asset_ids':input_assets,
             'input_asset_origin_work_ids':inherited_parent_work_ids,
             'input_source_kinds':parent_source_kinds,
             'evolution_assignment_event_seq':intent_lookup.get(evo['id']),
             'published_asset_ids':list(w['published']),
             'derived_asset_witnesses':new_child_assets,
             'parent_published_before_assignment':parents_precede_assignment,
             'child_published_after_assignment':published_after_assignment,
             'model_calls_saved_external':real_saved,'model_calls_saved_mock':mock_saved,
             'cross_researcher_research_attempt':bool(input_assets) and any(s.assets[p].get('work_id')!=wid for p in input_assets),
             'cross_researcher_material_delta_claimed':bool(new_child_assets),
             'scientific_materiality_independently_verified':False}
        steps.append(rec)
        if rec['cross_researcher_material_delta_claimed']:changed_by_worker.append(wid)
    assessments=[]
    for d in s.controller_decisions:
        cid=d['id']
        reviews=[r for r in s.program_reviews if r['reviewer_id']==cid]
        obj=[a for a in s.objective_assessments if a['reviewer_id']==cid]
        assessments.append({'controller_id':cid,'objective':obj[-1] if obj else None,
            'program_review':reviews[-1] if reviews else None})
    return {'status':'READ_ONLY_SCIENTIFIC_EVOLUTION_TRACE','root':str(j.root),
            'total_events':len(events),'total_works':len(s.work),'total_assets':len(s.assets),
            'total_evolution_actions':len(s.evolution),
            'cross_researcher_derived_work_count':len(set(changed_by_worker)),
            'cross_researcher_derived_asset_count':sum(len(a['derived_asset_witnesses']) for a in steps if a['cross_researcher_research_attempt']),
            'scientific_level_ii_certified':False,
            'interpretation':'Provenance and model-authored delta are not independent scientific validation; content and novelty must be assessed externally.',
            'evolution_actions':steps,'controller_assessments':assessments}


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out');ns=p.parse_args()
    res=audit(ns.root)
    b=json.dumps(res,indent=2,ensure_ascii=False)
    if ns.out:
        pathlib.Path(ns.out).write_text(b+'\n',encoding='utf-8')
        print(json.dumps({'status':res['status'],'root':res['root'],'out':ns.out,
            'cross_researcher_derived_work_count':res['cross_researcher_derived_work_count'],
            'scientific_level_ii_certified':False},ensure_ascii=False))
    else:print(b)
if __name__=='__main__':main()
