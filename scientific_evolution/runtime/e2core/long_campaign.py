"""Auditable long-horizon E2 orchestration, isolated cohort transfer.

No scientific instructions, hidden human judgements or unverified discoveries are
added to model inputs. Runtime budgets are operational pauses, not step quotas.
"""
from __future__ import annotations
import argparse, fcntl, hashlib, json, os, pathlib, shutil, tempfile
from contextlib import ExitStack, contextmanager
from .core import EvolutionJournal, guard, sha, canon, EvidenceError
from .engine import Engine
from .provider import DurableModel

@contextmanager
def locked_sources(*roots):
    with ExitStack() as stack:
        for root in sorted({str(pathlib.Path(r).resolve()) for r in roots}):
            f=stack.enter_context(open(pathlib.Path(root)/'.e2run.lock','a+b'))
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise EvidenceError('CONCURRENT_ROOT_RUN_DETECTED:'+root)
        yield

def prepare_isolated_fresh(root,problem):
    """Initialize a truly independent, seedless root. No old AI material."""
    text=pathlib.Path(problem).read_text(encoding='utf-8').strip()
    guard(bool(text) and len(text)<=12000,'INVALID_PROGRAM_PROBLEM')
    j=EvolutionJournal(root)
    j.init(text,origin='INDEPENDENT_UNSEEDED_FRESH_COHORT',criteria='Pre-experiment reviewable scientific hypotheses or rigorously scoped conclusions. Pause is not problem completion.')
    j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
    j.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
    return {'status':'ISOLATED_FRESH_ROOT_CREATED','root':str(j.root),'sources':0,'assets':0,'events':j.report()['events']}

def register_primary(root,source_id,source_file,description):
    """Only allowed on brand-new fresh root before any LLM Controller.

    JSON text file is parsed into real source data; never silently interpret
    model / earlier synthesized science as primary source.
    """
    j=EvolutionJournal(root)
    s=j.verify()
    guard(not s.model_calls and not s.work and not s.assets and not s.controller_decisions,'PRIMARY_REGISTRATION_AFTER_AI_STARTED_FORBIDDEN')
    data=json.loads(pathlib.Path(source_file).read_text(encoding='utf-8'))
    guard(isinstance(data,dict) and bool(data.get('title')) and bool(data.get('provenance')) and isinstance(data.get('content'),(str,dict,list)),'PRIMARY_JSON_NEEDS_TITLE_PROVENANCE_CONTENT')
    guard('REPLACE WITH' not in json.dumps(data,ensure_ascii=False),'PRIMARY_TEMPLATE_NOT_POPULATED')
    # This only controls declarative provenance. A primary source must really
    # have been verified by the operator; no automatic scientific certification.
    digest=j.add_source(source_id,'PRIMARY',data,description)
    return {'status':'PRIMARY_SOURCE_REGISTERED','root':str(j.root),'source_id':source_id,'sha256':digest,'scientific_certification':False}

def _first_controller_clean(j,s):
    calls=[c for c in s.model_calls.values() if c['actor']=='CONTROLLER']
    if not calls:return True
    first=calls[0]
    req=json.loads(j.raw(first['request_blob']))
    user=json.loads(req['messages'][1]['content'])
    return not user.get('assets') and not user.get('works') and len(user.get('problems',[]))==1

def _science_import_payload(a,src_root,src_state,model_text=None,model_call=None):
    root=str(src_root)
    wid=a.get('work_id')
    work=src_state.work.get(wid,{})
    return {
        'ref':root+'#'+a['id'],
        'science':{
            'scientific_work':a.get('claim',''),
            'scientific_delta':a.get('delta_from_parents',''),
            'scope':a.get('scope',''),
            'assumptions':a.get('assumptions',''),
            'predictions':a.get('predictions',[]),
            'limitations':a.get('limitations',[]),
            'isolated_origin_work_mode':work.get('mode'),
            'original_parent_ids':a.get('parent_ids',[]),
            'original_asset':a,
            'original_model_response_text':(model_text or {}).get('text'),
            'original_model_request_sha256':(model_call or {}).get('request_blob'),
            'original_model_response_sha256':(model_call or {}).get('response_blob'),
            'original_model_call_id':(model_text or {}).get('call_id'),
        },
        'tool_result':{'status':'NOT_CERTIFIED_BY_IMPORT'},
        'science_sha256':sha(canon(a)),
        'origin_type':'FOREIGN_ISOLATED_E2_RESEARCH_NOT_OPERATOR_SCIENCE',
        'origin_root':root,
        'origin_work_id':wid,
    }

def transfer_isolated_fresh(informed_root,isolated_root,destination_root):
    """Fork INFORMed, import isolated scientific outputs as explicitly historic AI.

    Prevent source contamination: fresh cohort starts with no old/human audit
    AI, first controller sees no external history. This bridge is operator
    indexing, not a scientific AI result, and always forks instead of mutating.
    """
    src=pathlib.Path(informed_root).resolve();fresh=pathlib.Path(isolated_root).resolve();dst=pathlib.Path(destination_root).resolve()
    guard(src!=fresh and src!=dst and fresh!=dst,'ROOTS_MUST_BE_DISTINCT')
    guard(not dst.exists(),'DESTINATION_ROOT_ALREADY_EXISTS')
    with locked_sources(src,fresh):
        ji=EvolutionJournal(src);jf=EvolutionJournal(fresh)
        old=ji.verify();fs=jf.verify()
        guard(old.program['problem']==fs.program['problem'],'PROGRAM_GOAL_MISMATCH')
        guard(fs.program.get('origin')=='INDEPENDENT_UNSEEDED_FRESH_COHORT','NOT_AN_ISOLATED_FRESH_ROOT')
        guard(all(v['kind']=='PRIMARY' or (v['kind']=='TOOL_RESULT' and v.get('work_id') in fs.work
            and v['work_id'] in {c['work_id'] for c in fs.model_calls.values() if c.get('actor')=='WORKER' and c.get('state')=='SAVED'})
            for v in fs.sources.values()),'FRESH_ROOT_HAS_AI_OR_AUDIT_SOURCE')
        # Every external research SOURCE must be an actual returned tool result,
        # not an ungrounded source manually inserted into an isolated cohort.
        # Retain exact request/result bytes in the original immutable Journal.
        for sid,source_rec in fs.sources.items():
            if source_rec['kind']!='TOOL_RESULT':continue
            data=json.loads(jf.raw(source_rec['blob']))
            tid=data.get('tool_id');tr=fs.tool_results.get(tid)
            guard(tr is not None and tr['work_id']==source_rec.get('work_id') and
                  data.get('work_id')==source_rec.get('work_id') and
                  data.get('request')==json.loads(jf.raw(tr['request_blob'])) and
                  data.get('result')==json.loads(jf.raw(tr['result_blob'])),
                  'FRESH_TOOL_SOURCE_NOT_EXECUTION_GROUNDED')
        guard(not any(a.get('origin')=='AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK' for a in fs.assets.values()),'FRESH_ROOT_HAS_IMPORTED_AI_ASSETS')
        guard(_first_controller_clean(jf,fs),'FIRST_FRESH_CONTROLLER_SAW_PREVIOUS_AI')
        guard(any(w.get('mode')=='FRESH' for w in fs.work.values()),'ISOLATED_ROOT_NO_FRESH_WORKER')
        guard(any(c.get('actor')=='WORKER' and c.get('billing_mode')=='EXTERNAL' and c.get('state')=='SAVED' for c in fs.model_calls.values()),'NO_ACTUAL_EXTERNAL_MODEL_WORK')
        # Keep any existing independent cohort's INFORMED continuation, but
        # label its exact origin. Do not relabel all outputs as FRESH.
        original_events=len(ji._events());fresh_events=len(jf._events())
        staging=dst.parent/(dst.name+'.STAGING')
        guard(not staging.exists(),'DESTINATION_STAGING_ALREADY_EXISTS')
        shutil.copytree(src,staging)
        try:
            target=EvolutionJournal(staging)
            guard(len(target._events())==original_events,'SOURCE_SNAPSHOT_CHANGED')
            if fs.r5_policy and not target.verify().r5_policy:
                target.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
            if fs.e3r1_policy and not target.verify().e3r1_policy:
                target.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
            problem_map={'P0':'P0'}
            if fs.r5_policy:
                # Original problems have causal parent references and declared order.
                # Keep the full original DAG, not a fake P0 for every asset.
                for problem in fs.problems.values():
                    if problem['id']=='P0':continue
                    oldpid=problem['id']
                    newid='P_ISO_'+sha(canon({'root':str(fresh),'problem':oldpid}))[:23]
                    problem_map[oldpid]=newid
                    payload={k:v for k,v in problem.items() if k!='status'}
                    payload['id']=newid
                    payload['parents']=[problem_map[x] for x in problem['parents']]
                    payload['original_problem_id']=oldpid
                    payload['original_cohort_root']=str(fresh)
                    target.append('PROBLEM_CREATED',payload)
            imported=[]
            asset_map={a['id']:'A_ISO_'+sha(canon({'root':str(fresh),'asset_id':a['id']}))[:23] for a in fs.assets.values() if a.get('work_id')}
            for a in fs.assets.values():
                if not a.get('work_id'):
                    continue
                work=fs.work[a['work_id']]
                ix=a.get('origin_step',0)
                guard(type(ix)==int and 1<=ix<=len(work['steps']),'FOREIGN_ASSET_HAS_NO_MODEL_ORIGIN')
                model_step=work['steps'][ix-1]
                guard(model_step['kind']=='MODEL_RESPONSE','FOREIGN_ASSET_NOT_FROM_MODEL_RESPONSE')
                model_text=json.loads(jf.raw(model_step['raw_blob']))
                model_call=fs.model_calls.get(model_text.get('call_id'),{})
                guard(model_call.get('actor')=='WORKER' and model_call.get('billing_mode')=='EXTERNAL' and model_call.get('state')=='SAVED','FOREIGN_ASSET_HAS_NO_REAL_SAVED_MODEL_CALL')
                foreign=sha(canon({'root':str(fresh),'asset_id':a['id']}))[:23]
                aid=asset_map[a['id']];sid='SRC_ISO_'+foreign
                # Future cycles can import from a different isolated root,
                # but never overwrite a provenance-bound earlier import.
                if aid in target.verify().assets:
                    continue
                guard(all(pid in asset_map for pid in a.get('parent_ids',[])),'FOREIGN_ASSET_DAG_INCOMPLETE')
                record=_science_import_payload(a,fresh,fs,model_text,model_call)
                target.add_source(sid,'HISTORICAL_AI',record,
                    'ISOLATED_RESEARCH_COHORT_IMPORT original_root='+str(fresh)+' original_asset='+a['id'])
                target.append('HISTORICAL_ASSET_INDEXED',{
                    'id':aid,'kind':a['kind'],'problem_id':problem_map[a['problem_id']],
                    'parent_ids':[asset_map[pid] for pid in a.get('parent_ids',[]) if pid in asset_map],
                    'original_problem_id':a['problem_id'],
                    'original_parent_ids':a.get('parent_ids',[]),
                    'origin_work_mode':fs.work[a['work_id']]['mode'],
                    'claim':a['claim'],'scope':a.get('scope') or 'Imported isolated-research claim',
                    'assumptions':a.get('assumptions') or 'As recorded in source; not independently certified',
                    'limitations':a.get('limitations',[])+['Transferred from isolated cohort; origin may be FRESH or own-cohort INFORMED','This indexing operation is not an LLM scientific discovery'],
                    'source_ids':[sid], 'source_ref':str(fresh)+'#'+a['id'],
                    'source_science_sha256':sha(canon(a)),
                    'source_tool_sha256':sha(canon({'status':'NOT_CERTIFIED_BY_IMPORT'})),
                    'catalog_sha256':sha(canon({'fresh_root':str(fresh),'asset_id':a['id'],'source_kind':'ISOLATED_E2'})),
                })
                imported.append({'old_asset_id':a['id'],'new_asset_id':aid,'original_work_mode':fs.work[a['work_id']]['mode']})
            if fs.r5_policy and imported:
                target.append('R5_INTEGRATION_REQUESTED',{'foreign_root':str(fresh),
                    'asset_ids':[x['new_asset_id'] for x in imported],
                    'event_seq':len(target._events())+1,
                    'reason':'Offer Controller scientific portfolio reconciliation, without mandatory continuation'})
            post=target.verify()
            post_events=len(target._events())
            guard(len(post.assets)==len(old.assets)+len(imported),'IMPORT_ASSET_COUNT_MISMATCH')
            guard(ji.verify().program==old.program and len(ji._events())==original_events,'INFORMED_ROOT_CHANGED')
            guard(len(jf._events())==fresh_events,'FRESH_ROOT_CHANGED')
            staging.rename(dst)
            return {'status':'ISOLATED_RESEARCH_IMPORTED_IN_NEW_INFORMED_FORK','original_informed_root':str(src),
                    'isolated_root':str(fresh),'new_informed_root':str(dst),'original_informed_events':original_events,
                    'new_informed_events':post_events,'problem_map':problem_map,'imported':imported,
                    'model_calls_new':0,'certification':False,'source_journals_unmodified':True,
                    'next_step':'Run Controller using the new informed fork; the import is not an ASSET_PUBLISHED event.'}
        except BaseException:
            if staging.exists():shutil.rmtree(staging)
            raise

def _recent_controller_schema_failures(j):
    """Consecutive plan/JSON problems since most recent committed decision.

    Schema failures can be repaired by the model after seeing machine feedback;
    a provider outage or unknown billing outcome must still fail closed.
    """
    failed=set()
    e3r1=j.verify().e3r1_policy
    for evt in reversed(j._events()):
        if evt['kind'] in {'CONTROLLER_DECISION','RUNTIME_CONTRACT_UPGRADED'}:break
        if e3r1 and evt['kind'] in {'ASSET_PUBLISHED','PROBLEM_CREATED','WORK_FINISHED',
                                    'HISTORICAL_ASSET_INDEXED'}:break
        if evt['kind']!='OPERATIONAL_PAUSE':continue
        p=evt['payload'];reason=p.get('reason','');cid=p.get('call_id')
        if cid and reason.startswith(('CONTROLLER_PLAN_REJECTED:', 'CONTROLLER_INVALID_JSON')):
            failed.add(cid)
    return len(failed)


def drive(root,*,budget,chunk,max_tokens,model,cpu,wall,paid,parallel=1):
    """Autonomous long run; recover schema failures without injecting science.

    Schema recovery attempts are a finite operational safety guard, not a
    scientific step or generation cap. Raw rejected calls remain preserved.
    """
    guard(paid and os.getenv('FAKG_RESEARCH_ALLOW_PAID')=='YES','EXPLICIT_PAID_APPROVAL_REQUIRED')
    guard(isinstance(budget,int) and 1<=budget<=1000 and 1<=chunk<=1000,'INVALID_OPERATIONAL_LIMITS')
    guard(1<=cpu<=240 and cpu+4<=wall<=300,'INVALID_SANDBOX_LIMITS')
    guard(isinstance(parallel,int) and 1<=parallel<=12,'INVALID_PARALLEL_WORKERS')
    j=EvolutionJournal(root)
    with locked_sources(root):
        j.verify()
        model_gateway=DurableModel(j,approved=True,max_new_calls=budget,model=model,max_tokens=max_tokens)
        e=Engine(j,model_gateway,serial_fair=(parallel==1),science_cpu_seconds=cpu,science_wall_seconds=wall)
        cycles=[]
        stop_reason='CALL_BUDGET'
        max_schema_attempts=4
        while model_gateway.new_calls<budget:
            if _recent_controller_schema_failures(j)>=max_schema_attempts:
                # A saved rejected Controller proposal does not revoke active
                # Work assignments. When science-state is unchanged, step the
                # already approved Worker instead of retrying rejected JSON.
                continue_existing=(j.verify().e3r1_policy and bool(e.ready_workers(parallel))
                                   and not e._should_controller_run())
                if not continue_existing:
                    stop_reason='SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED';break
            before=model_gateway.new_calls
            out=e.run(max_iterations=chunk,max_parallel=parallel)
            current=j.verify()
            brief={'status':out['status'],'new_calls_this_segment':model_gateway.new_calls-before,
                'new_calls_total':model_gateway.new_calls,'controller_decisions':len(current.controller_decisions),
                'assets':len(current.assets),'events':len(j._events()),'segment_statuses':out['decisions']}
            cycles.append(brief)
            print(json.dumps({'checkpoint':brief},ensure_ascii=False),flush=True)
            if out['status']=='SCIENTIFIC_DISPOSITION_PROPOSED':
                final_objective=j.verify().objective_assessments[-1] if j.verify().objective_assessments else None
                stop_reason=('OBJECTIVE_COMPLETED' if final_objective and final_objective['research_status']=='COMPLETED' else ('AUTONOMOUS_RESEARCH_PAUSED_NOT_OBJECTIVE_COMPLETED' if final_objective else 'AUTONOMOUS_SCIENTIFIC_DISPOSITION'));break
            stop=False;recoverable_controller=False
            for d in out['decisions']:
                if d.get('operational_pause') and 'OPERATIONAL_CALL_BUDGET_REACHED' not in d['operational_pause']:
                    stop=True
                ctl=d.get('controller',{})
                if ctl and ctl.get('status')!='CONTROLLER_COMMITTED':
                    if ctl.get('status') in ('CONTROLLER_PLAN_REJECTED','CONTROLLER_INVALID_JSON'):
                        recoverable_controller=True
                    else:stop=True
            if recoverable_controller and not stop:
                if _recent_controller_schema_failures(j)>=max_schema_attempts:
                    existing_ok=(j.verify().e3r1_policy and bool(e.ready_workers(parallel))
                                 and not e._should_controller_run())
                    if not existing_ok:
                        stop_reason='SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED';break
                # Valid next call has a fresh call ID, and input includes only
                # the model's own rejected answer plus machine validation reason.
                if model_gateway.new_calls<budget:continue
            if not e.ready_workers(1) and not e._should_controller_run():
                stop=True
            if stop or model_gateway.new_calls==before:
                stop_reason='OPERATIONAL_ERROR_OR_NO_RESEARCH_ACTION';break
        return {'status':'LONG_HORIZON_CAMPAIGN_FINISHED_OR_OPERATIONAL_PAUSE',
                'total_paid_new_calls':model_gateway.new_calls,'budget':budget,
                'science_certification':False,'scientific_reviews':j.report()['program_reviews'][-3:],
                'checkpoints':len(cycles),'root':str(j.root),'stop_reason':stop_reason,'max_parallel_workers':parallel,
                'objective_assessment':j.verify().objective_assessments[-1] if j.verify().objective_assessments else None,
                'recent_schema_rejections':_recent_controller_schema_failures(j)}

def full_campaign(fresh_root,informed_root,joined_root,*,fresh_budget,informed_budget,chunk,max_tokens,model,cpu,wall,paid):
    """One command controls BOTH operationally independent phases.

    No human science selection between phases; import ALL valid actual model
    outputs and let the informed Controller decide what to do with them.
    """
    guard(paid and os.getenv('FAKG_RESEARCH_ALLOW_PAID')=='YES','EXPLICIT_PAID_APPROVAL_REQUIRED')
    guard(not pathlib.Path(joined_root).exists(),'JOIN_ROOT_ALREADY_EXISTS')
    fresh=drive(fresh_root,budget=fresh_budget,chunk=chunk,max_tokens=max_tokens,model=model,cpu=cpu,wall=wall,paid=paid)
    if fresh['stop_reason'] in {'OPERATIONAL_ERROR_OR_NO_RESEARCH_ACTION','SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED'}:
        return {'status':'FRESH_OPERATIONAL_ERROR_NO_MERGE','fresh':fresh,'informed_run_not_started':True}
    s=EvolutionJournal(fresh_root).verify()
    if not any(a.get('work_id') for a in s.assets.values()):
        return {'status':'FRESH_NO_ACTUAL_SCIENCE_ASSETS_NO_MERGE','fresh':fresh,'informed_run_not_started':True}
    joined=transfer_isolated_fresh(informed_root,fresh_root,joined_root)
    informed=drive(joined_root,budget=informed_budget,chunk=chunk,max_tokens=max_tokens,model=model,cpu=cpu,wall=wall,paid=paid)
    return {'status':'TWO_PHASE_ISOLATED_FRESH_AND_INFORMED_COMPLETED_OR_PAUSED',
            'fresh':fresh,'bridge':joined,'informed':informed,'joint_scientific_certification':False,
            'note':'No forced scientific generation count, independent audit results withheld'}

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('fresh-init');a.add_argument('--root',required=True);a.add_argument('--problem-file',required=True)
    a=sub.add_parser('primary-add');a.add_argument('--root',required=True);a.add_argument('--id',required=True);a.add_argument('--json',required=True);a.add_argument('--description',required=True)
    a=sub.add_parser('transfer');a.add_argument('--informed-root',required=True);a.add_argument('--isolated-root',required=True);a.add_argument('--new-root',required=True)
    a=sub.add_parser('full-campaign');a.add_argument('--fresh-root',required=True);a.add_argument('--informed-root',required=True);a.add_argument('--joined-root',required=True);a.add_argument('--fresh-call-budget',type=int,default=100);a.add_argument('--informed-call-budget',type=int,default=140);a.add_argument('--paid',action='store_true');a.add_argument('--checkpoint-iterations',type=int,default=12);a.add_argument('--max-tokens',type=int,default=16000);a.add_argument('--model',default='openai/gpt-5.6-luna');a.add_argument('--science-cpu-seconds',type=int,default=120);a.add_argument('--science-wall-seconds',type=int,default=160)
    a=sub.add_parser('drive');a.add_argument('--max-parallel',type=int,default=1);a.add_argument('--root',required=True);a.add_argument('--paid',action='store_true');a.add_argument('--call-budget',type=int,default=80);a.add_argument('--checkpoint-iterations',type=int,default=12);a.add_argument('--max-tokens',type=int,default=14000);a.add_argument('--model',default='openai/gpt-5.6-luna');a.add_argument('--science-cpu-seconds',type=int,default=120);a.add_argument('--science-wall-seconds',type=int,default=160)
    ns=ap.parse_args()
    if ns.cmd=='fresh-init':out=prepare_isolated_fresh(ns.root,ns.problem_file)
    elif ns.cmd=='primary-add':out=register_primary(ns.root,ns.id,ns.json,ns.description)
    elif ns.cmd=='transfer':out=transfer_isolated_fresh(ns.informed_root,ns.isolated_root,ns.new_root)
    elif ns.cmd=='full-campaign':out=full_campaign(ns.fresh_root,ns.informed_root,ns.joined_root,fresh_budget=ns.fresh_call_budget,informed_budget=ns.informed_call_budget,chunk=ns.checkpoint_iterations,max_tokens=ns.max_tokens,model=ns.model,cpu=ns.science_cpu_seconds,wall=ns.science_wall_seconds,paid=ns.paid)
    else:out=drive(ns.root,budget=ns.call_budget,chunk=ns.checkpoint_iterations,max_tokens=ns.max_tokens,model=ns.model,cpu=ns.science_cpu_seconds,wall=ns.science_wall_seconds,paid=ns.paid,parallel=ns.max_parallel)
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
