"""Read-only failure inspection and immutable fork recovery of saved Controller text.

Two outcomes are possible: (1) the saved authorial plan is valid when its
new-problem declarations are sorted by explicitly authored dependencies, so
revalidate without a new model call; (2) scientific referents are genuinely
invalid, so copy the failed root unchanged and allow a new Controller call to
see its own rejected text plus machine validation feedback. Neither route
invents parent problem references or injects external scientific answers.
"""
from __future__ import annotations
import argparse, fcntl, json, os, pathlib, shutil, tempfile
from .core import EvolutionJournal, EvidenceError, canon, guard, sha
from .engine import controller_plan, _ordered_new_problems
from .provider import content_from_wire, strict_envelope


def _failed_controller(j):
    s=j.verify()
    rejected=[]
    for evt in j._events():
        if evt['kind']=='OPERATIONAL_PAUSE':
            p=evt['payload'];reason=p.get('reason','')
            if reason.startswith(('CONTROLLER_PLAN_REJECTED:', 'CONTROLLER_INVALID_JSON')) and p.get('call_id'):
                rejected.append((p['call_id'],reason))
    guard(rejected,'NO_SAVED_REJECTED_CONTROLLER_IN_ROOT')
    call_id,reason=rejected[-1]
    c=s.model_calls.get(call_id)
    guard(c is not None and c['actor']=='CONTROLLER' and c['state']=='SAVED','FAILED_CONTROLLER_CALL_NOT_SAVED')
    guard(not any(d['call_id']==call_id for d in s.controller_decisions),'CONTROLLER_ALREADY_COMMITTED')
    text=content_from_wire(j.raw(c['response_blob']))
    control=strict_envelope(text)
    return call_id,reason,c['response_blob'],text,control


def audit(root):
    j=EvolutionJournal(root)
    s=j.verify()
    cid,error,digest,text,control=_failed_controller(j)
    diagnoses=[]
    ordered_ids=None
    if isinstance(control,dict):
        pp=control.get('new_problems',[])
        if isinstance(pp,list):
            allids={p.get('id') for p in pp if isinstance(p,dict) and isinstance(p.get('id'),str)}
            known=set(s.problems)
            for k,p in enumerate(pp):
                if not isinstance(p,dict):
                    diagnoses.append({'index':k,'error':'NOT_OBJECT'});continue
                parents=p.get('parents')
                diagnoses.append({'index':k,'id':p.get('id'),'parents':parents,
                    'undeclared_parents':[x for x in parents if not isinstance(x,str) or (x not in known and x not in allids)] if isinstance(parents,list) else ['INVALID_PARENT_LIST'],
                    'forward_references':[x for x in parents if isinstance(x,str) and x in allids and x not in known and x not in [v.get('id') for v in pp[:k] if isinstance(v,dict)]] if isinstance(parents,list) else []})
            try:ordered_ids=[p['id'] for p in _ordered_new_problems(s.problems,pp)]
            except EvidenceError as exc:ordered_ids={'error':str(exc)}
    try:
        if isinstance(control,dict):
            planned=controller_plan(j,control,cid,cid.removeprefix('CTRL_'))
            reusable=True;validation='VALID_WITH_DEPENDENCY_ORDER'
        else:
            reusable=False;validation='CONTROLLER_INVALID_JSON';planned=[]
    except (EvidenceError,KeyError,TypeError,ValueError) as exc:
        reusable=False;validation=str(exc);planned=[]
    return {'status':'SAVED_CONTROLLER_FAILURE_AUDITED_READ_ONLY','root':str(j.root),'model_call_id':cid,
        'saved_wire_sha256':digest,'original_rejection':error,'current_validation':validation,
        'can_commit_without_new_model_call':reusable,
        'original_model_text':text,'parsed_model_plan':control,
        'problem_diagnostics':diagnoses,'declaration_order_after_dependency_sort':ordered_ids,
        'planned_event_kinds':[k for k,_ in planned],
        'science_certification':False}


def fork_saved_controller(source_root,new_root):
    src=pathlib.Path(source_root).resolve();dst=pathlib.Path(new_root).resolve()
    guard(src.is_dir() and not dst.exists() and src!=dst and not dst.is_relative_to(src),
        'INVALID_RECOVERY_PATHS')
    guard(not any(p.is_symlink() for p in src.rglob('*')),'SOURCE_ROOT_SYMLINK_DENIED')
    guard((src/'.e2run.lock').is_file(),'SOURCE_LOCK_MISSING')
    with (src/'.e2run.lock').open('rb') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:raise EvidenceError('SOURCE_ROOT_CURRENTLY_ACTIVE')
        old=EvolutionJournal(src)
        before=old._events()
        status=audit(src)
        dst.parent.mkdir(parents=True,exist_ok=True)
        stage=pathlib.Path(tempfile.mkdtemp(prefix='.e2-r4r1-recover-',dir=dst.parent))
        try:
            shutil.copytree(src,stage,dirs_exist_ok=True)
            branch=EvolutionJournal(stage)
            branch.verify()
            if status['can_commit_without_new_model_call']:
                cid=status['model_call_id'];control=status['parsed_model_plan']
                did=cid.removeprefix('CTRL_')
                planned=controller_plan(branch,control,cid,did)
                branch.append('CONTROLLER_DECISION',{'id':did,'call_id':cid,
                    'parsed_blob':branch.blob(control),'rationale':control['rationale'],
                    'commit_origin':'R4R1_REVALIDATED_SAVED_MODEL_PLAN_WITH_DEPENDENCY_ORDER',
                    'operator_reworded_model_text':False,'science_certification':False})
                for kind,payload in planned:branch.append(kind,payload)
                branch.append('OPERATIONAL_PAUSE',{'reason':'R4R1_REVALIDATED_PREVIOUS_REJECTION_ON_FORK_NOT_NEW_SCIENCE','call_id':cid})
                outcome='SAVED_CONTROLLER_REVALIDATED_WITHOUT_PAID_CALL'
            else:
                outcome='FAILED_CONTROLLER_PRESERVED_MODEL_CORRECTION_REQUIRED'
            result=branch.report()
            guard(old._events()==before,'SOURCE_EVENTS_CHANGED_DURING_FORK')
            stage.rename(dst)
            return {'status':outcome,'root':str(dst),'source_root':str(src),
                    'source_events':len(before),'fork_events':result['events'],
                    'controller_decisions':len(result['controller_decisions']),
                    'model_calls_new':0,'source_unmodified':True,
                    'original_rejection':status['original_rejection'],
                    'current_validation':status['current_validation'],
                    'next_action':'Continue full-campaign using THIS new fresh root; do not pay again for rejected call ID.',
                    'science_certification':False}
        except BaseException:
            shutil.rmtree(stage,ignore_errors=True)
            raise
        finally:fcntl.flock(lock,fcntl.LOCK_UN)


def main():
    ap=argparse.ArgumentParser(description='Inspect/fork failed FRESH Controller without any API call')
    ss=ap.add_subparsers(dest='mode',required=True)
    a=ss.add_parser('audit');a.add_argument('--root',required=True);a.add_argument('--out')
    a=ss.add_parser('fork');a.add_argument('--source-root',required=True);a.add_argument('--new-root',required=True);a.add_argument('--out')
    ns=ap.parse_args()
    data=audit(ns.root) if ns.mode=='audit' else fork_saved_controller(ns.source_root,ns.new_root)
    if ns.out:
        pathlib.Path(ns.out).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    brief={k:v for k,v in data.items() if k not in ('original_model_text','parsed_model_plan','planned_event_kinds')}
    print(json.dumps(brief,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
