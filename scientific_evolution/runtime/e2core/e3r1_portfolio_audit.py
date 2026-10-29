"""Read-only E3R1 portfolio scheduling and disposition inventory; not a science certificate."""
import argparse, collections, json, pathlib
from .core import EvolutionJournal
from .engine import _portfolio_context


def audit(root):
    j=EvolutionJournal(root);s=j.verify()
    last_decision=s.program_reviews[-1] if s.program_reviews else None
    work_states=collections.Counter(w['status'] for w in s.work.values())
    ops=collections.defaultdict(collections.Counter)
    for w in s.work.values():ops[w['operation']][w['status']]+=1
    r={'status':'READ_ONLY_E3R1_PORTFOLIO_AUDIT','root':str(j.root),
       'policy_enabled':s.e3r1_policy,'journal_events':len(j._events()),
       'controller_decisions':len(s.controller_decisions),'model_calls_saved_external':sum(c['state']=='SAVED' and c.get('billing_mode')=='EXTERNAL' for c in s.model_calls.values()),
       'work_statuses':dict(work_states),'operations_by_status':{k:dict(v) for k,v in ops.items()},
       'portfolio_assessment_events':sum(e['kind']=='WORK_PORTFOLIO_ASSESSED' for e in j._events()),
       'work_portfolio_history':{wid:w.get('portfolio_history',[]) for wid,w in s.work.items() if w.get('portfolio_history')},
       'last_program_review':last_decision,
       'last_objective_assessment':s.objective_assessments[-1] if s.objective_assessments else None,
       'open_frontier':_portfolio_context(s),
       'unassessed_open_works':[wid for wid,w in s.work.items() if w['status'] in {'QUEUED','ACTIVE','DEFERRED'} and not w.get('portfolio_history')],
       'warning':'Scheduling fairness and model-authored portfolio judgments are NOT scientific materiality or novelty certification; open work may be preserved under program HOLD.'}
    return r


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);ns=p.parse_args()
    data=audit(ns.root);out=pathlib.Path(ns.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':data['status'],'output':str(out),'work_statuses':data['work_statuses']},ensure_ascii=False))
if __name__=='__main__':main()
