#!/usr/bin/env python3
"""A pinned, single-entry V4 operational baseline; no change to scientific policies.

A checkpoint branch at the last committed V4 Controller decision is a new
historical branch, not an edit or repair of the original source journal.
"""
from __future__ import annotations
import argparse
from collections import Counter
import contextlib
import fcntl
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from e2core.core import EvolutionJournal, EvidenceError, canon, sha, guard
import scientific_research_readiness_v4 as v4
import scientific_closed_loop_v3 as v3

EXPECTED_V4_SHA256 = 'bf5fe6a1a87df68e4055694dffa19f14e1c57ee8b49d240a34b219f4f07cf7ef'
CLEAN_RECEIPT = 'V4_CLEAN_COMMITTED_DECISION_CHECKPOINT_FORK_20261029'
DEFAULT_LAST = 'D00077'


def source_code_guard():
    v3.source_code_guard()
    guard(sha(Path(v4.__file__).read_bytes()) == EXPECTED_V4_SHA256,
          'V4_SOURCE_VERSION_DIFFERS_FROM_PINNED_BASELINE')


@contextlib.contextmanager
def source_read_lock(src):
    """Require existing lockfiles; never create them in the source root."""
    with contextlib.ExitStack() as stack:
        for name in ('.scientific_feedback_autorun.lock', '.e2run.lock'):
            path = src / name
            guard(path.is_file() and not path.is_symlink(),
                  'SOURCE_LOCKFILE_MISSING_OR_UNSAFE:' + name)
            fd = os.open(path, os.O_RDONLY)
            stack.callback(os.close, fd)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise EvidenceError('SOURCE_ROOT_CURRENTLY_RUNNING:' + name) from exc
            stack.callback(fcntl.flock, fd, fcntl.LOCK_UN)
        yield


def branch_analysis(src, decision_id=DEFAULT_LAST):
    source_code_guard()
    src = Path(src).expanduser().resolve(strict=True)
    j = EvolutionJournal(src)
    s = j.verify()
    guard(s.controller_decisions and s.controller_decisions[-1]['id'] == decision_id,
          'EXPECTED_LAST_COMMITTED_CONTROLLER_NOT_FOUND:' + decision_id)
    rows = j._events()
    matches = [i for i, row in enumerate(rows) if row['kind'] == 'CONTROLLER_DECISION'
               and row['payload'].get('id') == decision_id]
    guard(len(matches) == 1, 'CHECKPOINT_CONTROLLER_DECISION_NOT_UNIQUE')
    i = matches[0]
    prefix, excluded = rows[:i+1], rows[i+1:]
    tail_calls = [
        {'seq': row['seq'], 'kind': row['kind'],
         'call_id': row['payload'].get('id'),
         'reason': row['payload'].get('reason')}
        for row in excluded if row['kind'].startswith('MODEL_CALL_')
    ]
    tail_science = [
        {'seq': row['seq'], 'kind': row['kind'],
         'id': row['payload'].get('id'), 'asset_kind':row['payload'].get('kind')}
        for row in excluded if row['kind'] in
        {'ASSET_PUBLISHED', 'WORK_STEP', 'WORK_FINISHED', 'WORK_STARTED', 'PROBLEM_CREATED', 'EVOLUTION_APPLIED'}
    ]
    unknowns = [cid for cid, c in s.model_calls.items() if c['state'] == 'UNCERTAIN']
    receipt = v3._recovery_receipt(j)
    guard(set(unknowns) == {receipt['original_call_id']},
          'SOURCE_HAS_NEW_OR_UNACCOUNTED_UNCERTAIN_CALL')
    tail_new_unknown = [c for c in tail_calls if c['kind']=='MODEL_CALL_UNCERTAIN']
    guard(not tail_new_unknown, 'SOURCE_TAIL_CONTAINS_UNCERTAIN_CALL')
    return {
        'source_root':str(src), 'checkpoint_controller_id':decision_id,
        'checkpoint_seq':prefix[-1]['seq'], 'checkpoint_event_sha256':sha(canon(prefix[-1])),
        'source_head_sha256':sha(canon(rows[-1])),
        'source_event_count':len(rows), 'retained_events':len(prefix),
        'excluded_events':len(excluded),
        'excluded_kinds':dict(Counter(x['kind'] for x in excluded)),
        'excluded_model_call_events':tail_calls,
        'excluded_scientific_events':tail_science,
        'excluded_saved_call_count':sum(x['kind']=='MODEL_CALL_SAVED' for x in tail_calls),
        'historical_unknown_preserved_before_checkpoint':True,
        'source_controller_count':len(s.controller_decisions),
        '_prefix':prefix,
    }


def public_report(r):
    return {k:v for k,v in r.items() if not k.startswith('_')}


def fork(src, dst, decision_id=DEFAULT_LAST, acknowledge_paid_tail=False,
         acknowledge_scientific_tail=False):
    src=Path(src).expanduser().resolve(strict=True)
    dst=Path(dst).expanduser().absolute()
    guard(not dst.exists() and dst.parent.is_dir() and not dst.is_relative_to(src)
          and src != dst, 'DESTINATION_EXISTS_OR_UNSAFE')
    guard(not any(p.is_symlink() for p in src.rglob('*')),
          'SOURCE_HAS_SYMLINK')
    with source_read_lock(src):
        info=branch_analysis(src, decision_id)
        guard(info['excluded_events']>0,
              'SOURCE_ALREADY_AT_CHECKPOINT_USE_V4_FORK_INSTEAD')
        guard(acknowledge_paid_tail or info['excluded_saved_call_count']==0,
              'PAID_SAVED_CALLS_IN_EXCLUDED_TAIL_ACKNOWLEDGEMENT_REQUIRED')
        guard(acknowledge_scientific_tail or not info['excluded_scientific_events'],
              'SCIENTIFIC_EVENTS_IN_EXCLUDED_TAIL_ACKNOWLEDGEMENT_REQUIRED')
        original_head=info['source_head_sha256']
        stage=Path(tempfile.mkdtemp(prefix='.v4-clean-',dir=dst.parent))
        try:
            shutil.rmtree(stage)
            shutil.copytree(src,stage,symlinks=False)
            for path in (stage/'events').glob('*.json'):
                if int(path.stem)>info['checkpoint_seq']:
                    path.unlink()
            j=EvolutionJournal(stage)
            before=j._events()
            guard([sha(canon(x)) for x in before] ==
                  [sha(canon(x)) for x in info['_prefix']],
                  'CHECKPOINT_EVENT_PREFIX_CHANGED')
            # All blobs are retained, even those referenced only in the excluded
            # tail.  This does not invent source evidence or drop content.
            state=j.verify()
            guard(state.controller_decisions[-1]['id']==decision_id,
                  'CHECKPOINT_REPLAY_WRONG_LAST_DECISION')
            guard(set(cid for cid,c in state.model_calls.items()
                      if c['state']=='UNCERTAIN')==
                  {v3._recovery_receipt(j)['original_call_id']},
                  'CHECKPOINT_HAS_NEW_UNCERTAIN_MODEL_CALLS')
            j.append('OPERATIONAL_PAUSE',{
                'reason':CLEAN_RECEIPT,
                'source_root':str(src),
                'source_full_head_sha256':original_head,
                'retained_history_head_sha256':info['checkpoint_event_sha256'],
                'checkpoint_controller_id':decision_id,
                'retained_event_count':info['retained_events'],
                'excluded_event_count':info['excluded_events'],
                'excluded_tail_model_call_events':info['excluded_model_call_events'],
                'excluded_tail_scientific_events':info['excluded_scientific_events'],
                'potential_repeated_provider_charge_ack':bool(acknowledge_paid_tail),
                'excluded_tail_science_ack':bool(acknowledge_scientific_tail),
                'historical_branch_not_silent_journal_edit':True,
                'scientific_interpretation_unchanged':True,
                'original_p0_immutable':True,
            })
            j.verify()
            v4.inspect(stage)  # Real V4 engine and historical receipt must work
            original=EvolutionJournal(src)
            guard(sha(canon(original._events()[-1]))==original_head,
                  'ORIGINAL_SOURCE_CHANGED_DURING_FORK')
            stage.rename(dst)
        except BaseException:
            if stage.exists():shutil.rmtree(stage)
            raise
    return {'event':'V4_CLEAN_FORK_CREATED_NO_PAID',
            'new_root':str(dst),'original_root_unchanged':True,
            **public_report(info), 'new_events':info['retained_events']+1}


def inspect(root):
    source_code_guard()
    root=Path(root).expanduser().resolve(strict=True)
    j=EvolutionJournal(root)
    s=j.verify()
    receipts=[e['payload'] for e in j._events()
              if e['kind']=='OPERATIONAL_PAUSE'
              and e['payload'].get('reason')==CLEAN_RECEIPT]
    guard(len(receipts)==1,'CLEAN_CHECKPOINT_FORK_RECEIPT_REQUIRED')
    r=receipts[0]
    guard(len(s.controller_decisions)>=1 and len(s.model_calls)>0,
          'INVALID_CLEAN_RESEARCH_STATE')
    guard(s.program is not None and s.problems['P0']['question']==s.program['problem'],
          'P0_MISMATCH')
    status=v4.inspect(root)
    return {'event':'V4_CLEAN_BASELINE_PREFLIGHT',
            'checkpoint_controller_id':r.get('checkpoint_controller_id',DEFAULT_LAST),
            'receipt':CLEAN_RECEIPT,
            'source_full_head_sha256':r['source_full_head_sha256'],
            'excluded_event_count':r['excluded_event_count'],
            'excluded_tail_saved_calls':sum(x['kind']=='MODEL_CALL_SAVED'
                  for x in r['excluded_tail_model_call_events']),
            'frozen_science_policy':'V4_UNCHANGED',
            'V5_not_loaded_or_required':True,
            **status}


def run(root, preflight=False, paid=False, model='openai/gpt-5.6-luna',
        slice_budget=8, max_total_new_calls=8, checkpoint_iterations=12,
        max_parallel=2, max_tokens=16000, science_cpu_seconds=120,
        science_wall_seconds=160):
    st=inspect(root)
    print(json.dumps(st,ensure_ascii=False),flush=True)
    if preflight:return 0
    guard(paid and os.environ.get('FAKG_RESEARCH_ALLOW_PAID')=='YES',
          'EXPLICIT_PAID_APPROVAL_REQUIRED')
    guard(bool(os.environ.get('OPENROUTER_API_KEY','').strip()),
          'OPENROUTER_API_KEY_REQUIRED_BEFORE_MODEL_INTENT')
    guard(1<=max_total_new_calls<=slice_budget and 1<=slice_budget,
          'INVALID_CALL_BUDGET')
    # Avoid a new risky implementation of Controller / durable gateway.
    # Only the pinned V4 science runtime is invoked.
    return v4.run(root,True,model,slice_budget,max_total_new_calls,
                  checkpoint_iterations,max_parallel,max_tokens,
                  science_cpu_seconds,science_wall_seconds,preflight=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest='cmd',required=True)
    i=subs.add_parser('source-audit');i.add_argument('--source-root',required=True)
    i.add_argument('--last-controller',default=DEFAULT_LAST)
    f=subs.add_parser('fork');f.add_argument('--source-root',required=True)
    f.add_argument('--out-root',required=True)
    f.add_argument('--last-controller',default=DEFAULT_LAST)
    f.add_argument('--acknowledge-excluded-saved-calls',action='store_true')
    f.add_argument('--acknowledge-excluded-scientific-events',action='store_true')
    x=subs.add_parser('inspect');x.add_argument('--root',required=True)
    r=subs.add_parser('run');r.add_argument('--root',required=True)
    r.add_argument('--preflight',action='store_true');r.add_argument('--paid',action='store_true')
    r.add_argument('--model',default='openai/gpt-5.6-luna')
    r.add_argument('--slice-budget',type=int,default=8)
    r.add_argument('--max-total-new-calls',type=int,default=8)
    r.add_argument('--checkpoint-iterations',type=int,default=12)
    r.add_argument('--max-parallel',type=int,default=2)
    r.add_argument('--max-tokens',type=int,default=16000)
    r.add_argument('--science-cpu-seconds',type=int,default=120)
    r.add_argument('--science-wall-seconds',type=int,default=160)
    a=p.parse_args()
    try:
        if a.cmd=='source-audit':value=public_report(branch_analysis(a.source_root,a.last_controller))
        elif a.cmd=='fork':value=fork(a.source_root,a.out_root,a.last_controller,a.acknowledge_excluded_saved_calls,
                                              a.acknowledge_excluded_scientific_events)
        elif a.cmd=='inspect':value=inspect(a.root)
        else:return run(a.root,a.preflight,a.paid,a.model,a.slice_budget,
                        a.max_total_new_calls,a.checkpoint_iterations,
                        a.max_parallel,a.max_tokens,a.science_cpu_seconds,a.science_wall_seconds)
        print(json.dumps(value,indent=2,ensure_ascii=False));return 0
    except (EvidenceError, FileNotFoundError) as exc:
        print('V4_CLEAN_STOPPED_WITHOUT_SCIENCE_CLAIM:'+str(exc),file=sys.stderr)
        return 3

if __name__=='__main__':raise SystemExit(main())
