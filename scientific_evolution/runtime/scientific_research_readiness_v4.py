#!/usr/bin/env python3
"""V4: autonomous pre-experiment research readiness and claim/problem handoff.

Production V3/V2/E2 sources are not edited. No research actions are mandated.
The original research problem, FRESH isolation, Journal provenance and uncertainty
recovery rules remain in force.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
from e2core.core import EvolutionJournal, EvidenceError, guard, canon, sha
import scientific_closed_loop_v3 as v3
import scientific_problem_evolution as spe

V4_FORK_RECEIPT='V4_PREEXPERIMENT_RESEARCH_READINESS_FORK_FROM_V3'
V4_COMPARISON_CONTRACT='V4_RESEARCH_START_VS_CERTIFICATION_SEPARATED'

# We use the actual V3 policy-independent Controller, not a new manager.
# The underlying Controller and Opportunity JSON schema is unchanged.
OPPORTUNITY_ADVISORY = '''\nV4 pre-experiment scientific research opportunity comparison (advisory):
The objective is pre-experiment, independently reviewable scientific novelty,
NOT experimental confirmation or causal attribution to an existing dataset.
Distinguish three independent readiness questions for EACH prospective action:
 (a) theoretical readiness: can explicit, physically defensible assumptions yield a
     causal mechanism or prediction that can be challenged or falsified?
 (b) computational readiness: could a reproducible analytic/numerical model test
     concrete consequences and strong competing nulls without fabricated parameters?
 (c) empirical readiness: can available experimental evidence test whether the
     mechanism ACTUALLY operates in the target system?
A negative (c) must not automatically veto (a) or (b), provided the result is
honestly labeled conditional/unverified and the proposed calculations materially
advance a *new* question, instead of recycling generic non-identifiability.
For each proposed action, compare its intended scientific deliverable and
information gain against active Work's deliverables. Similar subject matter or
an ACTIVE FRESH evidence-acquisition Worker alone is NOT proof of duplicate Work.
A source-retrieval Work and a distinct theory Work can run concurrently;
there is no requirement or quota to create new work. It is valid to recommend
NO_ACTION when the *scientific* expected value is low, but say WHY a feasible
conditional theory or mechanism-development alternative has lower value.
Prior-art novelty is claim-level, distinguishing observation, author interpretation,
mathematical implication, and tested causal claims. Prior overlap can narrow a
hypothesis without settling P0; a hypothesis's refutation does not refute P0.
Only cite source IDs that genuinely exist. Preserve original P0 exactly.
Return the pre-existing opportunity JSON contract; do not invent fields that
make the validation schema fail.\n'''

CONTROLLER_ADVISORY = '''\nV4 scientific readiness and action/learning connection (advisory, not hard policy):
The success criterion is a scientifically reviewable *pre-experiment* novel
mechanistic claim with a physically defensible derivation, conditional distinctive
prediction against strong nulls, and a falsifying experiment. It is NOT an
already measured effect. Empirical source incompleteness constrains the claim's
certification, but is not in itself a dependency that blocks theoretical reasoning.
Consider whether a new theoretical, computational or independent challenge Work
can make a real scientific advance now, in parallel with an ACTIVE literature
FRESH Work. Compare deliverables; reject only if scientifically redundant or
unproductive, rather than because the literature Work is open.
A new Work can revise an old hypothesis, formulate a new mechanism, challenge
physical assumptions, discover a rival model, or address a changed P0 residual.
Neither continue the charge branch by default nor force a pivot; pursue the best
available scientific contribution to P0. The existing source Work may continue.
When selecting work, connect prior-art findings to: (i) the precise claim weakened
or contradicted; (ii) the remaining causal/predictive statement; (iii) which P0
requirement stays open; (iv) the particular new proof, computation, contradiction,
or prospective discriminant that the Work would produce. Do not confuse a paper's
absence of proof with proof of absence.
An actions=[] decision and a justified scientific HOLD remain valid. Explain why
independent pre-experiment theory is premature ON SCIENTIFIC GROUNDS when choosing
only further literature retrieval. No Work-count targets, fixed stages, hard research
sequence or forced science. Original P0 and prior reviews are immutable.\n'''

READINESS_TEMPLATE={
 'purpose':'Science selection advice, not an empirical certification or machine permission gate',
 'theoretical_readiness':{
   'question':'Can an explicit physically defensible model make a new falsifiable conditional claim?',
   'data_required_to_begin':'Not necessarily raw experimental trajectories',
   'appropriate_output':'Derivation, competing physical mechanisms, predictions, counterexample, falsifier'},
 'computational_readiness':{
   'question':'Can a reproducible model distinguish predictions across assumption/parameter ranges?',
   'data_required_to_begin':'Symbolic or literature-bounded inputs may suffice; unknowns must be explicit',
   'appropriate_output':'Sensitivity, identifiability limits, alternative nulls, domain of validity'},
 'empirical_readiness':{
   'question':'Can present data establish applicability or causal truth in the target system?',
   'data_required_to_begin':'Experimental evidence is required for empirical attribution and validation',
   'appropriate_output':'Experiment/data adequacy judgement; not an automatic veto on theory'},
 'candidate_maturity_rule':'Model-proposed != physically verified != novel independently certified',
 'controller_autonomy':{'may_select_no_action':True,'may_select_parallel_work':True,
                         'may_defer':True,'no_fixed_minimum_work_or_steps':True},
}

# Only previously committed MODEL advice is reused for the research handoff.
# It is NOT a new primary science asset and may be challenged by the Worker.
def committed_delta_handoff(j, work_id=None):
    s=j.verify()
    if not s.controller_decisions:
        return {'status':'NO_PRIOR_COMMITTED_DELTA','model_assessment_only':True}
    context=v3._last_controller_input(j) or {}
    state=spe.working_problem_state(j)
    claim_rows=(context.get('claim_prior_art_assessment') or {}).get('claim_assessments',[])
    p0_rows=(context.get('problem_level_impact') or {}).get('claim_to_problem',[])
    changes=(context.get('prior_art_delta') or {}).get('new_or_changed_claims',[])
    # An INFORMED Work receives relevant parents first, but may question its
    # starting assumptions in the broader P0 context. No status is certified.
    parents=set()
    if work_id and work_id in s.work:
        parents.update(s.work[work_id].get('asset_input_ids',[]))
    def compact_row(r,fields):
        return {k:r[k] for k in fields if k in r}
    def priority(r):return (0 if r.get('asset_id') in parents else 1,str(r.get('asset_id','')))
    return {
      'status':'LAST_COMMITTED_MODEL_ADVISORY_NOT_VERIFIED_SCIENCE',
      'controller_decision':s.controller_decisions[-1]['id'],
      'model_assessment_only':True,'original_problem_immutable':True,
      'relevant_parent_asset_ids':sorted(parents),
      'novelty_claim_rows':[compact_row(r,('asset_id','relation','evidence_ids',
          'overlapping_or_contradicting_content','remaining_conditional_claim',
          'specific_differentiating_prediction','strongest_competing_explanation',
          'evidence_limitations','residual_hypothesis','decisive_test'))
           for r in sorted(claim_rows,key=priority)[:30]],
      'claim_to_original_problem':[compact_row(r,('asset_id','relation_to_p0',
          'impact_on_solution','impact_on_original_problem','remaining_open_requirement','evidence_ids'))
          for r in sorted(p0_rows,key=priority)[:30]],
      'recent_prior_art_assessment_changes':changes[:25],
      'working_problem_interpretation':state.get('latest_working_p0',{}),
      'research_instruction':'Develop or challenge the scientifically strongest residual claim or alternative; do not treat any model novelty opinion as established evidence. The source records can be verified using their IDs.',
    }

BASE_FINGERPRINT=v3._science_fingerprint

def readiness_science_fingerprint(base,claims,evidence):
    # One-time advisory-protocol change invalidates V3 assessor reuse without
    # changing durable NVT/PMI request identities. Once V4 is committed, exact
    # same science/context can be reused safely in later V4 decisions.
    return sha(canon({'science':BASE_FINGERPRINT(base,claims,evidence),
                      'assessment_context_version':V4_COMPARISON_CONTRACT}))

BASE_WORK_OPTIONS=v3._work_options
BASE_WORKER_INPUT=spe.feedback_worker_input
BASE_OPPORTUNITY_PROMPT=spe.OPPORTUNITY_PROMPT
BASE_FEEDBACK_ADDENDUM=spe.CONTROLLER_FEEDBACK_ADDENDUM
BASE_V3_ADVISORY=v3.V3_ADVISORY

def science_work_options(j):
    base=BASE_WORK_OPTIONS(j)
    # The Assessor/Controller (not this deterministic layer) determines which
    # theoretical opportunity is scientifically sound or worth selecting.
    base['v4_research_readiness']=READINESS_TEMPLATE
    base['v4_scientific_delta_handoff']=committed_delta_handoff(j)
    base['v4_active_work_overlap_rule']='Compare precise scientific question, evidence dependency, methods and intended output; same domain or active FRESH source Work is insufficient to show duplication.'
    return base


def worker_input(j,wid,tool_capabilities=None):
    base=BASE_WORKER_INPUT(j,wid,tool_capabilities)
    if j.verify().work[wid]['mode']=='INFORMED':
        base['v4_claim_problem_scientific_handoff']=committed_delta_handoff(j,wid)
        base['v4_research_readiness']=READINESS_TEMPLATE
        base['v4_preexperiment_science_instruction']='The research can develop physically plausible conditional mechanisms without claiming empirical discovery. Identify derivations, falsifiers and strong nulls; revise claim and P0 interpretation on actual evidence, not by paraphrase. Compare the Work objective with P0 and account for failed theories.'
    # IMPORTANT: FRESH receives exactly the old pinned input.
    return base

@contextmanager
def runtime():
    # Revert all prompt/module hooks, including on exceptions.
    previous=(v3._work_options, v3._science_fingerprint, v3.V3_ADVISORY, spe.OPPORTUNITY_PROMPT,
              spe.CONTROLLER_FEEDBACK_ADDENDUM,spe.feedback_worker_input)
    try:
        v3._work_options=science_work_options
        v3._science_fingerprint=readiness_science_fingerprint
        v3.V3_ADVISORY=BASE_V3_ADVISORY+CONTROLLER_ADVISORY
        spe.OPPORTUNITY_PROMPT=BASE_OPPORTUNITY_PROMPT+OPPORTUNITY_ADVISORY
        spe.CONTROLLER_FEEDBACK_ADDENDUM=BASE_FEEDBACK_ADDENDUM
        spe.feedback_worker_input=worker_input
        yield
    finally:
        (v3._work_options,v3._science_fingerprint,v3.V3_ADVISORY,spe.OPPORTUNITY_PROMPT,
         spe.CONTROLLER_FEEDBACK_ADDENDUM,spe.feedback_worker_input)=previous


def fork(src,dst):
    v3.source_code_guard()
    src=Path(src).expanduser().resolve();dst=Path(dst).expanduser().absolute()
    guard(src.is_dir() and not dst.exists() and src!=dst and not dst.is_relative_to(src),
          'INVALID_OR_EXISTING_FORK_TARGET')
    guard(dst.parent.is_dir() and not any(p.is_symlink() for p in src.rglob('*')),
          'UNSAFE_SOURCE_FOR_FORK')
    with v3._source_locks(src):
        old=EvolutionJournal(src);v3.status(src);saved=old.verify()
        original=[sha(canon(e)) for e in old._events()]
        stage=Path(tempfile.mkdtemp(prefix='.v4-science-',dir=dst.parent))
        try:
            shutil.rmtree(stage);shutil.copytree(src,stage,symlinks=False)
            new=EvolutionJournal(stage)
            guard([sha(canon(e)) for e in new._events()]==original,
                  'FORK_JOURNAL_HISTORY_CHANGED')
            new.append('OPERATIONAL_PAUSE',{'reason':V4_FORK_RECEIPT,'source_root':str(src),
               'source_head_sha256':original[-1],'source_event_count':len(original),
               'new_science_not_manually_committed':True,
               'research_start_and_certification_remain_distinct':True,
               'historical_unknown_outcome_not_reinterpreted':True})
            nexts=new.verify()
            guard(nexts.program==saved.program and len(nexts.assets)==len(saved.assets)
                  and len(nexts.work)==len(saved.work)
                  and len(nexts.model_calls)==len(saved.model_calls)
                  and len(nexts.controller_decisions)==len(saved.controller_decisions),
                  'FORK_MUTATED_SCIENCE')
            v3.status(stage)
            guard([sha(canon(e)) for e in old._events()]==original,
                  'FORK_SOURCE_CHANGED_DURING_COPY')
            stage.rename(dst)
        except BaseException:
            if stage.exists():shutil.rmtree(stage)
            raise
    return {'status':'V4_ROOT_PREPARED_NO_PAID','source_root':str(src),
            'new_root':str(dst),'original_event_count':len(original),
            'forked_event_count':len(original)+1,
            'original_root_unchanged':True,'P0_unchanged':True,
            'historical_unknown_outcome_preserved':True,'science_certification':False}


def inspect(root):
    st=v3.status(root)
    j=EvolutionJournal(root)
    receipts=[e for e in j._events() if e['kind']=='OPERATIONAL_PAUSE' and e['payload'].get('reason')==V4_FORK_RECEIPT]
    guard(len(receipts)==1,'V4_FORK_RECEIPT_REQUIRED')
    return {'event':'V4_PREFLIGHT',**st,'v4_fork_receipt':V4_FORK_RECEIPT,
            'v4_research_readiness_separated':True,
            'latest_delta_has_prior_committed_controller':bool(j.verify().controller_decisions),
            'informed_context_only_on_informed_workers':True}


def run(root,paid,model,slice_budget,max_total_new_calls,iterations,parallel,tokens,cpu,wall,preflight=False):
    st=inspect(root)
    print(json.dumps(st,ensure_ascii=False),flush=True)
    if preflight:return 0
    # Real call budget, incomplete call, and provenance guards are inherited
    # from V3; no simulated research outcome is reported as actual discovery.
    with runtime():
        return v3.run(root,paid,model,slice_budget,max_total_new_calls,iterations,parallel,tokens,cpu,wall,preflight=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('fork');p.add_argument('--source-root',required=True);p.add_argument('--out-root',required=True)
    p=sub.add_parser('inspect');p.add_argument('--root',required=True)
    p=sub.add_parser('run');p.add_argument('--root',required=True);p.add_argument('--preflight',action='store_true')
    p.add_argument('--paid',action='store_true');p.add_argument('--model',default='openai/gpt-5.6-luna')
    p.add_argument('--slice-budget',type=int,default=12);p.add_argument('--max-total-new-calls',type=int,default=24)
    p.add_argument('--checkpoint-iterations',type=int,default=12);p.add_argument('--max-parallel',type=int,default=2)
    p.add_argument('--max-tokens',type=int,default=16000)
    p.add_argument('--science-cpu-seconds',type=int,default=120);p.add_argument('--science-wall-seconds',type=int,default=160)
    a=parser.parse_args()
    try:
        v3.source_code_guard()
        if a.cmd=='fork':result=fork(a.source_root,a.out_root)
        elif a.cmd=='inspect':result=inspect(a.root)
        else:return run(a.root,a.paid,a.model,a.slice_budget,a.max_total_new_calls,
                        a.checkpoint_iterations,a.max_parallel,a.max_tokens,
                        a.science_cpu_seconds,a.science_wall_seconds,a.preflight)
        print(json.dumps(result,indent=2,ensure_ascii=False));return 0
    except EvidenceError as exc:
        print('V4_STOPPED_WITHOUT_SCIENCE_CLAIM:'+str(exc),file=sys.stderr);return 3

if __name__=='__main__':raise SystemExit(main())
