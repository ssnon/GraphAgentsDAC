#!/usr/bin/env python3
"""Resume the NEW informed scientific problem/claim feedback loop until MODEL HOLD.

Operational slices never change P0 or become scientific conclusions. This calls
scientific_problem_evolution.run_feedback (four-stage Controller), not the old
Two-Stage Controller. A spend ceiling is optional and never a science label.
"""
from __future__ import annotations
import argparse, fcntl, json, os, sys
from pathlib import Path
from types import SimpleNamespace
from e2core.core import EvolutionJournal
from scientific_problem_evolution import run_feedback

TERMINAL={'HOLD_WITH_RATIONALE','REVIEW_WORTHY_CANDIDATE','SCOPED_NEGATIVE'}

def snapshot(root):
    s=EvolutionJournal(root).verify()
    return {'disposition':s.program_reviews[-1]['scientific_status'] if s.program_reviews else None,
       'uncertain_calls':sorted(k for k,v in s.model_calls.items() if v['state']!='SAVED'),
       'saved_calls':len(s.model_calls),'controller_decisions':len(s.controller_decisions),
       'works':{k:w['status'] for k,w in s.work.items()}}

def classify(result,st,segment_calls):
    if st['uncertain_calls']:return 'STOP_UNCERTAIN_PROVIDER_CALL'
    if st['disposition'] in TERMINAL:return 'AUTONOMOUS_SCIENTIFIC_DISPOSITION'
    if result['stop_reason']=='CALL_BUDGET' and segment_calls>0:return 'CONTINUE_NEXT_OPERATIONAL_SLICE'
    return 'OPERATIONAL_STOP_NOT_SCIENTIFIC_HOLD'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True);p.add_argument('--preflight',action='store_true')
    p.add_argument('--paid',action='store_true');p.add_argument('--model',default='openai/gpt-5.6-luna')
    p.add_argument('--slice-budget',type=int,default=80)
    p.add_argument('--max-total-new-calls',type=int,default=None)
    p.add_argument('--checkpoint-iterations',type=int,default=12)
    p.add_argument('--max-tokens',type=int,default=16000)
    p.add_argument('--max-parallel',type=int,default=2)
    p.add_argument('--science-cpu-seconds',type=int,default=120)
    p.add_argument('--science-wall-seconds',type=int,default=160)
    args=p.parse_args()
    if not 1<=args.slice_budget<=1000:p.error('slice-budget out of range (1..1000)')
    if args.max_total_new_calls is not None and args.max_total_new_calls<1:p.error('max-total-new-calls must be positive')
    root=Path(args.root).expanduser().resolve()
    if not (root/'manifest.json').is_file():p.error('Not an existing Journal root')
    st=snapshot(root)
    print(json.dumps({'event':'PREFLIGHT','root':str(root),**st},ensure_ascii=False),flush=True)
    if args.preflight:return 0
    if st['uncertain_calls']:
        print('Uncertain paid calls require manual review; no silent retry.',file=sys.stderr)
        return 3
    if st['disposition'] in TERMINAL:
        print('Scientific terminal state already exists. Do not overwrite/restart.')
        return 0
    if not args.paid or os.getenv('FAKG_RESEARCH_ALLOW_PAID')!='YES':
        p.error('Explicit --paid and FAKG_RESEARCH_ALLOW_PAID=YES required')
    lockfile=(root/'.scientific_feedback_autorun.lock').open('a+b')
    try:fcntl.flock(lockfile.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        print('Another launcher already holds this root.',file=sys.stderr)
        return 6
    used=0;round_index=0
    try:
        while True:
            remaining=(args.max_total_new_calls-used if args.max_total_new_calls is not None else args.slice_budget)
            if remaining<=0:
                print(json.dumps({'event':'COST_GUARD','paid_calls_this_launch':used,
                                  'scientific_certification':False}),flush=True)
                return 4
            slice_budget=min(args.slice_budget,remaining)
            runargs=SimpleNamespace(call_budget=slice_budget,checkpoint_iterations=args.checkpoint_iterations,
                     max_tokens=args.max_tokens,model=args.model,max_parallel=args.max_parallel,
                     science_cpu_seconds=args.science_cpu_seconds,science_wall_seconds=args.science_wall_seconds)
            round_index+=1
            result=run_feedback(str(root),runargs)
            added=result.get('total_paid_new_calls',0)
            used+=added
            st=snapshot(root);verdict=classify(result,st,added)
            print(json.dumps({'event':'SCIENTIFIC_FEEDBACK_CHECKPOINT','round':round_index,
                 'new_calls_this_round':added,'cumulative_new_calls':used,'stop_reason':result['stop_reason'],
                 'next':verdict,'scientific_status':st['disposition'],
                 'controller_decisions':st['controller_decisions'],'works':st['works']},ensure_ascii=False),flush=True)
            if verdict=='CONTINUE_NEXT_OPERATIONAL_SLICE':continue
            return 0 if verdict=='AUTONOMOUS_SCIENTIFIC_DISPOSITION' else 5
    except KeyboardInterrupt:
        print('\nINTERRUPTED_BY_OPERATOR_NOT_SCIENTIFIC_HOLD',flush=True)
        return 130
    finally:
        fcntl.flock(lockfile.fileno(),fcntl.LOCK_UN);lockfile.close()

if __name__=='__main__':raise SystemExit(main())
