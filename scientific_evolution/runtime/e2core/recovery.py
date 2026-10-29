"""Opt-in, no-paid, non-mutating archival recovery of the E2-R1 Oct 27 paid run.

This creates NEW evidence events in a fork. It NEVER alters model-authored bytes,
reclassifies a scientific claim as tool-verified, or 'repairs' a Controller decision.
"""
from __future__ import annotations
import copy
import json
import os
import pathlib
import shutil
import tempfile
from .core import EvolutionJournal, EvidenceError, guard, canon, sha
from .provider import strict_envelope, content_from_wire

CASE_CALLS={
    'CTRL_D00001':'480a4f008f423c7e3d3bfbb23912c8c84c3ad55ff43b144f0b3d5c9fe653bba2',
    'WK_W_REPAIR_LAG_CALCULATION_00001':'d9210fe4288eb04592de169e6d7baf4f83b4fdc40827125ed51aa54069f9f61e',
    'WK_W_DISCRIMINANT_MATRIX_00001':'c9b77d1c54c74685ee701452233d4fc3b6b82a2ba84a944b7d2a1abc52c93c96',
    'CTRL_D00002':'11567ff9009a45f8244d6c3b693a1abf4601c6bd8d002c426ab02d4a4f0232eb',
}
WORKS=[
    ('LAG','WK_W_REPAIR_LAG_CALCULATION_00001','VERIFY',['A_SHARED_LAG'],'P1','W_RECOVERED_LAG','EV_RECOVERED_LAG','SRC_RECOVERED_LAG'),
    ('MATRIX','WK_W_DISCRIMINANT_MATRIX_00001','FUSE',['A_SHARED_LAG','A_RESONANCE','A_OCCUPANCY','A_DUTY_NULL'],'P1','W_RECOVERED_MATRIX','EV_RECOVERED_MATRIX','SRC_RECOVERED_MATRIX'),
]

def inspect_case(j):
    s=j.verify()
    guard(len(j._events())==50,'RECOVERY_EXPECTS_50_EVENT_FIRST_RUN')
    guard(len(s.controller_decisions)==1 and s.controller_decisions[0]['id']=='D00001','RECOVERY_CONTROLLER_HISTORY_MISMATCH')
    guard(s.work['W_REPAIR_LAG_CALCULATION']['outcome']=='BLOCKED' and s.work['W_DISCRIMINANT_MATRIX']['outcome']=='BLOCKED','RECOVERY_EXPECTS_BLOCKED_ORIGINAL_WORKS')
    guard(s.work['W_CONTROLLED_PERTURBATION_TABLE']['status']=='QUEUED','RECOVERY_EXPECTS_QUEUED_THIRD_WORK')
    for cid,digest in CASE_CALLS.items():
        guard(cid in s.model_calls and s.model_calls[cid]['state']=='SAVED','RECOVERY_MODEL_CALL_MISSING')
        guard(s.model_calls[cid]['response_blob']==digest,'RECOVERY_SOURCE_RESPONSE_HASH_MISMATCH')
    return s

def _read_response(j,cid):
    s=j.verify();digest=s.model_calls[cid]['response_blob']
    contents=content_from_wire(j.raw(digest))
    obj=strict_envelope(contents)
    guard(isinstance(obj,dict),'SAVED_MODEL_TEXT_NOT_JSON_OBJECT')
    return digest,contents,obj

def _archival_work(j,spec):
    label,cid,op,parents,problem,wid,evid,sid=spec
    digest,text,obj=_read_response(j,cid)
    guard(obj.get('next_action')=='CONTINUE' and isinstance(obj.get('scientific_text'),str),'RECOVERED_WORKER_NOT_EXPECTED')
    assets=obj.get('assets',[]);problems=obj.get('new_problems',[])
    guard(isinstance(assets,list) and isinstance(problems,list) and all(isinstance(x,dict) for x in assets+problems),'RECOVERY_UNEXPECTED_SHAPE')
    source_body={'saved_model_call_id':cid,'response_blob_sha256':digest,'exact_original_model_text':text,
                 'origin':'PAID_MODEL_AUTHORED_UNVERIFIED','recovery':'READ_ONLY_INDEXED_IN_NEW_FORK'}
    j.add_source(sid,'OPERATOR',source_body,'Archival pointer to saved paid model text; operator indexing, not new science')
    work={
        'id':wid,'mode':'INFORMED','problem_id':problem,
        'question':'Archival recovery of the already paid response '+cid+'; NO new research was performed',
        'research_rationale':'Preserve scientifically relevant original outputs despite E2-R1 metadata ID collision',
        'source_ids':[sid], 'archival_only':True, 'no_new_model_research':True}
    j.append('EVOLUTION_APPLIED',{'id':evid,'operation':op,'asset_ids':parents,'work':work,
        'reason':'Archival indexing of saved model output, NOT autonomous new evolution',
        'origin':'OPERATOR_ARCHIVAL_RECOVERY_NOT_AUTONOMOUS_EVOLUTION',
        'source_model_call_id':cid,'science_work_executed':False})
    j.start(wid)
    original_ids=[p.get('id') for p in problems]
    guard(len(original_ids)==len(set(original_ids)),'RECOVERY_DUPLICATE_LOCAL_PROBLEM_ID')
    mapping={}
    for i,p in enumerate(problems,1):
        local=p.get('id');gid=f'P_REC_{label}_{i:02d}'
        guard(local and gid not in j.verify().problems,'RECOVERY_PROBLEM_ID_COLLISION')
        mapping[local]=gid
    j.step(wid,'ARCHIVAL_RECOVERY_OF_SAVED_MODEL_RESPONSE',{
        'origin_call_id':cid,'response_blob_sha256':digest,'original_next_action':obj['next_action'],
        'original_scientific_text':obj['scientific_text'],
        'problem_id_mapping':mapping,'origin_status':'MODEL_AUTHORED_UNVERIFIED',
        'interpretation':'Operator indexing of existing model output; NOT a model call or experimental verification'})
    nprob=0
    for p in problems:
        q=copy.deepcopy(p)
        q['id']=mapping[p['id']]
        # Parent list resolves prior existing global IDs, except explicit newly introduced local IDs.
        q['parents']=[mapping.get(x,x) for x in q.get('parents',[])]
        q['origin_model_call_id']=cid;q['original_model_local_id']=p['id']
        j.append('PROBLEM_CREATED',q)
        nprob+=1
    nassets=0
    for a in assets:
        pa=a.get('parent_ids',[])
        guard(all(x in j.verify().assets for x in pa),'RECOVERY_ASSET_PARENT_NOT_RESOLVABLE')
        # No rewording, upgrading, or scientific adjudication of any claim.
        s=j.verify();w=s.work[wid]
        p={'id':a['id'],'work_id':wid,'origin_step':len(w['steps']),
           'kind':a['kind'],'problem_id':a.get('problem_id',w['problem_id']),
           'claim':a['claim'],'assumptions':a['assumptions'],'scope':a['scope'],
           'predictions':a.get('predictions',[]),'limitations':a.get('limitations',[]),
           'parent_ids':pa,'delta_from_parents':a.get('delta_from_parents',''),
           'source_ids':[sid],'certification':'MODEL_PROPOSED_UNVERIFIED',
           'original_model_call_id':cid,'original_model_asset_id':a['id'],
           'indexing_origin':'EXPLICIT_OPERATOR_RECOVERY_NOT_NEW_MODEL_EXECUTION'}
        j.append('ASSET_PUBLISHED',p)
        nassets+=1
    j.finish(wid,'RETURN','Archive indexing ended; original Worker remains BLOCKED, and its original next_action CONTINUE remains unexecuted')
    return {'saved_call_id':cid,'archival_work_id':wid,'assets_indexed':nassets,'new_problems_indexed':nprob,'problem_id_mapping':mapping}

def fork_recover(source_root,new_root):
    source=pathlib.Path(source_root).resolve()
    dest=pathlib.Path(new_root).absolute()
    guard(source.exists() and source.is_dir() and source!=dest,'INVALID_RECOVERY_SOURCE')
    guard(not dest.exists(),'RECOVERY_NEW_ROOT_MUST_NOT_EXIST')
    guard(source.name=='E2_R1_SCIENCE_20261027_123239','RECOVERY_CASE_SOURCE_BASENAME_MISMATCH')
    guard(not any(p.is_symlink() for p in source.rglob('*')),'RECOVERY_SOURCE_SYMLINK_DENIED')
    j0=EvolutionJournal(source)
    inspect_case(j0)
    original_event_hashes=[sha(canon(e)) for e in j0._events()]
    dest.parent.mkdir(parents=True,exist_ok=True)
    staging=pathlib.Path(tempfile.mkdtemp(prefix='.e2-r2-stage-',dir=dest.parent))
    try:
        shutil.copytree(source,staging,dirs_exist_ok=True)
        j=EvolutionJournal(staging)
        inspect_case(j)
        indexed=[_archival_work(j,spec) for spec in WORKS]
        # Do not reinterpret second Controller's misplaced disposition/field as committed.
        ctrl_digest,_,bad=_read_response(j,'CTRL_D00002')
        guard('disposition' not in bad and any('disposition' in a for a in bad.get('actions',[]) if isinstance(a,dict)), 'RECOVERY_UNEXPECTED_SECOND_CONTROLLER_SHAPE')
        j.append('OPERATIONAL_PAUSE',{'reason':'RECOVERY_SECOND_CONTROLLER_NOT_COMMITTED; ORIGINAL_UNVALIDATED_MODEL_RESPONSE_PRESERVED; NEW_CONTROLLER_DECISION_REQUIRED',
          'call_id':'CTRL_D00002','response_blob_sha256':ctrl_digest})
        r=j.report()
        guard(len(r['assets'])==13 and len(r['problems'])==6 and r['work']['W_CONTROLLED_PERTURBATION_TABLE']['status']=='QUEUED','RECOVERY_ASSERTION_FAILURE')
        guard(r['work']['W_DISCRIMINANT_MATRIX']['outcome']=='BLOCKED' and r['work']['W_REPAIR_LAG_CALCULATION']['outcome']=='BLOCKED','HISTORICAL_WORK_STATUS_MUTATED')
        guard(len(r['controller_decisions'])==1,'HISTORICAL_CONTROLLER_ALTERED')
        j0.verify()
        guard([sha(canon(e)) for e in j0._events()]==original_event_hashes,'RECOVERY_SOURCE_CHANGED_DURING_FORK')
        os.rename(staging,dest)
        return {'status':'E2_R2_ARCHIVAL_RECOVERY_COMPLETED_NO_PAID','root':str(dest),'source_root_unmodified':True,
                'source_event_count':50,'fork_event_count':r['events'],'assets_total':len(r['assets']),
                'new_problems_total':len(r['problems']),'recoveries':indexed,'queued_original_work_preserved':True,
                'second_controller_status':'UNCOMMITTED_INVALID_ORIGINAL_PRESERVED',
                'science_certification':False,'paid_calls_during_recovery':0}
    except BaseException:
        shutil.rmtree(staging,ignore_errors=True)
        raise
