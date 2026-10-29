#!/usr/bin/env python3
"""V3: science-triggered evaluation and autonomous cross-Work continuation.

No new research manager. Historical UNKNOWN provider outcome is retained and
excluded solely when a saved, audited replacement is linked by the V1 receipt.
"""
from __future__ import annotations
import argparse, contextlib, fcntl, json, os, shutil, sys, tempfile, importlib
from pathlib import Path
from types import SimpleNamespace

from e2core.core import EvolutionJournal, EvidenceError, guard, canon, sha
from e2core.engine import Engine, _external_context, controller_plan, CONTROLLER_PROMPT, E3R1_CONTROLLER_ADDENDUM
from e2core.provider import strict_envelope, content_from_wire, DurableModel
import e2core.engine as e2_engine
import scientific_problem_evolution as spe

RECEIPT='EXPLICIT_OPERATOR_UNKNOWN_OUTCOME_REISSUE_IN_SEPARATE_FORK_V1'
FORK_RECEIPT='V3_FORK_FROM_RECOVERED_SCIENTIFIC_EVOLUTION_READONLY_SOURCE'
TERMINAL={'HOLD_WITH_RATIONALE','REVIEW_WORTHY_CANDIDATE','SCOPED_NEGATIVE'}
CANDIDATES={'HYPOTHESIS','PREDICTION','CALCULATION','NULL_MODEL','COUNTEREXAMPLE','SCOPED_NEGATIVE'}
# Never suppress a newly read fulltext/figure/method/supplement passage: it can
# contradict a prior claim even when no Worker knows its relevance yet.
DIRECT_EXT=set(spe.DIRECT_CLASSES)|{'OA_PDF_TEXT','OA_SUPPLEMENT_TEXT','DIRECT_SUPPLEMENT_EXCERPT'}
PINNED_SOURCE_HASHES={
 'scientific_problem_evolution.py':'9d3f61c33e16dd5b4953fe17043401856ff306d508794126693aacaf182db7da',
 'scientific_problem_autorun.py':'4d1948438af77eff16b92cdcc33564c77a44e210a979237510e18d54580c1536',
 'e2core/core.py':'fecd290b590d88e81e6fa5fbc4b083430cce088415a5bc7091821725402b5cfa',
 'e2core/provider.py':'dd7a2901ac7cca19dccf5b831b73581357cb6b7a22c71b4af95fcb0c352fbbeb',
 'e2core/engine.py':'57b848903d6004da52fffabd62f0776b365af9b177d3e998d88a02c150f220b1',
 'e2core/long_campaign.py':'50c4584d9a1970d76728e76502a9f86b0f130226f60678dcd06474e0279c8417',
}

def source_code_guard():
    # The input source zip was supplied by the user. Fail closed on drift of
    # implementation that could invalidate replay or provenance assumptions.
    locations={
      'scientific_problem_evolution.py':Path(spe.__file__).resolve(),
      'scientific_problem_autorun.py':Path(importlib.util.find_spec('scientific_problem_autorun').origin).resolve(),
      'e2core/core.py':Path(sys.modules[EvolutionJournal.__module__].__file__).resolve(),
      'e2core/provider.py':Path(sys.modules[DurableModel.__module__].__file__).resolve(),
      'e2core/engine.py':Path(sys.modules[Engine.__module__].__file__).resolve(),
      'e2core/long_campaign.py':Path(sys.modules[spe.base_drive.__module__].__file__).resolve(),
    }
    for key,filepath in locations.items():
        guard(filepath.is_file() and sha(filepath.read_bytes())==PINNED_SOURCE_HASHES[key],
              'UNVERIFIED_EXECUTION_SOURCE_VERSION:'+key)


def _recovery_receipt(j):
    receipts=[e['payload'] for e in j._events() if e['kind']=='OPERATIONAL_PAUSE'
              and e['payload'].get('reason')==RECEIPT]
    guard(len(receipts)==1,'EXACTLY_ONE_PRIOR_UNKNOWN_OUTCOME_RECEIPT_REQUIRED')
    p=receipts[0];s=j.verify()
    old=s.model_calls.get(p.get('original_call_id'))
    new=s.model_calls.get(p.get('reissue_call_id'))
    guard(old and old['state']=='UNCERTAIN' and old['request_blob']==p['original_request_blob'],
          'HISTORICAL_UNKNOWN_OUTCOME_NOT_PRESERVED')
    guard(new and new['state']=='SAVED','PRIOR_REISSUE_NOT_SAVED')
    guard(old['actor']=='CONTROLLER' and old['id'].startswith('NVT_') and new['id'].startswith('NVT_REISSUE_'),
          'REISSUE_NOT_MATCHING_EXPECTED_NVT')
    guard(p.get('original_unknown_outcome') is True and
          p.get('potential_duplicate_provider_charge_ack') is True,'REISSUE_RECEIPT_INVALID')
    unresolved=[cid for cid,r in s.model_calls.items() if r['state']!='SAVED' and cid!=p['original_call_id']]
    guard(not unresolved,'ADDITIONAL_UNCERTAIN_CALLS_REQUIRE_MANUAL_REVIEW')
    return p


def status(root):
    j=EvolutionJournal(Path(root).expanduser());s=j.verify();p=_recovery_receipt(j)
    rows=j._events()
    last=max((i for i,e in enumerate(rows) if e['kind']=='CONTROLLER_DECISION'),default=-1)
    recent=rows[last+1:]
    candidates=[{'seq':e['seq'],'kind':e['kind'],'asset_kind':e['payload'].get('kind')}
                for e in recent if _event_is_scientific(j,e)]
    return {'root':str(j.root),'journal_events':len(rows),
        'historical_unknown_call':p['original_call_id'],'historical_unknown_status':'UNCERTAIN',
        'replacement_call':p['reissue_call_id'],'replacement_status':'SAVED',
        'other_unknown_calls':[],
        'controller_decisions':len(s.controller_decisions),'assets':len(s.assets),
        'works':{k:w['status'] for k,w in s.work.items()},
        'science_trigger_events_since_last_controller':candidates[-15:],
        'last_scientific_disposition':s.program_reviews[-1]['scientific_status'] if s.program_reviews else None,
        'science_certification':False}


@contextlib.contextmanager
def _source_locks(root):
    with contextlib.ExitStack() as stack:
        for n in ('.scientific_feedback_autorun.lock','.e2run.lock'):
            p=root/n;fd=stack.enter_context(open(p,'a+b'))
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise EvidenceError('SOURCE_ROOT_IS_RUNNING:'+n)
            stack.callback(fcntl.flock,fd,fcntl.LOCK_UN)
        yield


def fork(src,dst):
    source_code_guard()
    src=Path(src).expanduser().resolve();dst=Path(dst).expanduser().absolute()
    guard(src.is_dir() and not dst.exists() and src!=dst and not dst.is_relative_to(src),
          'FORK_INVALID_PATH_OR_ALREADY_EXISTS')
    guard(dst.parent.is_dir() and not any(p.is_symlink() for p in src.rglob('*')),
          'FORK_UNSAFE_SOURCE')
    with _source_locks(src):
        j0=EvolutionJournal(src);status(src);o=j0.verify();events=j0._events()
        original_hashes=[sha(canon(x)) for x in events]
        stage=Path(tempfile.mkdtemp(prefix='.v3-science-continuation-',dir=dst.parent))
        try:
            shutil.rmtree(stage);shutil.copytree(src,stage,symlinks=False)
            new=EvolutionJournal(stage)
            guard([sha(canon(x)) for x in new._events()]==original_hashes,
                  'FORK_EVENT_HISTORY_NOT_IDENTICAL')
            new.append('OPERATIONAL_PAUSE',{'reason':FORK_RECEIPT,
               'source_root':str(src),'source_head_sha256':original_hashes[-1],
               'source_event_count':len(events),'source_model_call_count':len(o.model_calls),
               'source_controller_decision_count':len(o.controller_decisions),
               'operator_fork_not_scientific_evidence':True,
               'previous_uncertain_outcome_not_reinterpreted':True})
            n=new.verify()
            guard(n.program==o.program and len(n.assets)==len(o.assets) and
                  len(n.controller_decisions)==len(o.controller_decisions) and
                  len(n.model_calls)==len(o.model_calls),'FORK_CHANGED_SCIENTIFIC_STATE')
            status(stage)
            guard([sha(canon(x)) for x in j0._events()]==original_hashes,
                  'ORIGINAL_ROOT_CHANGED_DURING_FORK')
            stage.rename(dst)
        except BaseException:
            if stage.exists():shutil.rmtree(stage)
            raise
    return {'status':'V3_FORK_PREPARED_NO_PAID','original_root':str(src),
            'new_root':str(dst),'source_original_unchanged':True,
            'events_before':len(events),'events_after':len(events)+1,
            'historical_unknown_state_preserved':True,'science_certification':False}


def _last_controller_input(j):
    s=j.verify()
    if not s.controller_decisions:return None
    return spe._read_controller_context(j,s.controller_decisions[-1],s)


def _science_fingerprint(base,claims,evidence):
    # The state of the posed problem and actual mechanism claims is an explicit
    # trigger. Retrieval-only bibliographic metadata is NOT directly decisive;
    # keep it in Controller context and journal for retrieval work decisions.
    credible=[x for x in evidence if x.get('inspection_class') in DIRECT_EXT or
              x.get('source_kind')=='OPERATOR_SUBMITTED_UNVERIFIED']
    # Full exact evidence including ID is intentional: never lose a novel
    # physical passage just because a prior paper with same DOI was read.
    material={'program':base['program'],'problems':base['problems'],
              'candidate_claims':claims,'potentially_relevant_primary_evidence':credible}
    return sha(canon(material))


def _event_is_scientific(j,event):
    kind=event['kind'];p=event['payload']
    if kind in {'WORK_FINISHED','PROBLEM_CREATED','HISTORICAL_ASSET_INDEXED',
                'INTEGRATION_REQUESTED'}:return True
    if kind=='SOURCE_REGISTERED' and str(p.get('id','')).startswith('SRC_PRIOR_'):return True
    if kind!='ASSET_PUBLISHED':return False
    if p.get('kind') in CANDIDATES:return True
    if p.get('kind')=='LITERATURE_CLAIM':
        # Direct literature claim with actual primary text can alter null
        # models even if it isn't yet a hypothesis.
        s=j.verify()
        return any(s.sources.get(sid,{}).get('kind')=='TOOL_RESULT' and
             (json.loads(j.raw(s.sources[sid]['blob'])).get('evidence_class') in DIRECT_EXT or
              (json.loads(j.raw(s.sources[sid]['blob'])).get('result') or {}).get('evidence_class') in DIRECT_EXT)
             for sid in p.get('source_ids',[]) if sid in s.sources)
    return False


def should_controller_run(self):
    # Preserve base operational/serial-fair protections and active Worker
    # independence. Only change the frequency of additional reassessment.
    if self.serial_fair and self._uninterpreted_tool_feedback():return False
    rows=self.j._events();s=self.j.verify()
    if s.r5_policy and s.integration_requests:
        last_req=s.integration_requests[-1]['event_seq']
        if not any(x['kind']=='CONTROLLER_DECISION' and x['seq']>last_req for x in rows):return True
    if not s.controller_decisions:
        return not any(w['status'] in {'QUEUED','ACTIVE'} for w in s.work.values())
    last=max((i for i,row in enumerate(rows) if row['kind']=='CONTROLLER_DECISION'),default=-1)
    recent=rows[last+1:]
    # Do not retry a rejected Controller plan without new material science.
    if s.e3r1_policy and any(w['status'] in {'QUEUED','ACTIVE'} for w in s.work.values()):
        if not any(_event_is_scientific(self.j,e) for e in recent):return False
    return any(_event_is_scientific(self.j,e) for e in recent)


V3_ADVISORY='''\nV3 scientific-continuation perspective (advisory, NOT policy):
- P0 seeks a physically plausible and falsifiable NEW pre-experiment hypothesis, not experimental proof of a mechanism already proposed. Missing experiment data may constrain novelty/certainty, but does not by itself prohibit explicitly assumed theory, calculation, or a distinct mechanistic prediction.
- An active source-acquisition/FRESH Worker is not a dependency barrier for an independent INFORMED Worker. Consider whether the accumulated partial findings ALREADY enable a high-information-value hypothesis-development, derivation, independent null/challenge or alternative mechanism Work concurrently. You may decide no such Work is justified.
- Distinguish (i) source acquisition to fill a genuine missing prior-art gap, (ii) new causal/quantitative claim creation, (iii) independent strong-null stress test, and (iv) administrative evaluation. Which action (including no action or HOLD) advances P0 most given what is already known? No fixed minimum Work, research direction, count, cadence or generation is expected.
- Consider reasons WHY a proposed next Work would materially differ from a currently active Work. Parallel Work only if its science is genuinely nonredundant. Prior reports and inherited model assessments are never experimental certification.
- A prior-art finding can invalidate novelty of one component while leaving a distinct prediction under explicit assumptions to investigate; neither require novelty at all costs nor let source incompleteness indefinitely veto theoretical proposals.
'''


def _work_options(j):
    s=j.verify();items=[]
    for wid,w in s.work.items():
        if w['status'] in {'QUEUED','ACTIVE','DEFERRED'}:
            items.append({'work_id':wid,'mode':w.get('mode'),
                          'status':w['status'],'question':w.get('question'),
                          'published_count':len(w.get('published',[])),
                          'steps':len(w.get('steps',[]))})
    return {'active_scientific_work':items,
       'concurrent_informed_work_is_permitted':True,
       'existing_worker_remains_independent':True,
       'no_requirement_to_create_work':True,
       'success_target':'New defensible conditional physical hypothesis with distinguishing prediction against strong nulls; no prior experimental confirmation required',
       'research_selection_independently_decided_by_controller':True}


def controller_v3(self,ident):
    j=self.j
    base=_external_context(j,'NATIVE_RESEARCH_TOOLS' if self._native_tool_contract else 'CUSTOM_BACKEND_CAPABILITIES_UNDECLARED')
    evidence=spe.classified_evidence(j);claims=spe.target_claims(base,j)
    state=spe.working_problem_state(j)
    fingerprint=_science_fingerprint(base,claims,evidence)
    prior=_last_controller_input(j)
    reused=False
    if (prior and prior.get('v3_material_science_fingerprint')==fingerprint and
        isinstance(prior.get('claim_prior_art_assessment'),dict) and
        isinstance(prior.get('problem_level_impact'),dict)):
        # Reuse only previously committed, validated advisory, never a raw
        # rejected model response or a fictional new completion.
        novelty=prior['claim_prior_art_assessment']
        impact=prior['problem_level_impact']
        provenance=prior['feedback_call_provenance']
        novelty_id=provenance['novelty_model_call']
        impact_id=provenance['problem_impact_model_call']
        reused=True
    else:
        source={'program':base['program'],'target_claims':claims,'evidence':evidence,
          'prior_working_problem_state':state,'original_success_criterion':base['program'].get('criteria'),
          'source_policy':'Model judgement only. Not proof or experimental certification.'}
        novelty_id=spe._call_id('NVT',source)
        old=j.verify().model_calls.get(novelty_id)
        if old and old['state']=='UNCERTAIN':
            receipt=_recovery_receipt(j)
            guard(novelty_id==receipt['original_call_id'],'UNRELATED_UNKNOWN_OUTCOME_NOT_RETRIABLE')
            same_wire=canon({'model':self.model.model,'temperature':0.7,'max_tokens':self.model.max_tokens,
                  'response_format':{'type':'json_object'},'messages':[
                     {'role':'system','content':spe.NOVELTY_PROMPT},
                     {'role':'user','content':json.dumps(source,ensure_ascii=False,sort_keys=True,allow_nan=False)}]})
            guard(sha(same_wire)==old['request_blob'],'HISTORICAL_UNCERTAIN_INPUT_MISMATCH')
            replacement=j.verify().model_calls.get(receipt['reissue_call_id'])
            guard(replacement and replacement['state']=='SAVED' and
                  replacement['request_blob']==old['request_blob'],
                  'HISTORICAL_REISSUE_NOT_EXACT_REQUEST_MATCH')
            novelty_id=receipt['reissue_call_id']
            raw_novelty=content_from_wire(j.raw(replacement['response_blob']))
        else:
            raw_novelty=self.model.call(novelty_id,'CONTROLLER',None,spe.NOVELTY_PROMPT,source)
        novelty_obj=strict_envelope(raw_novelty)
        if novelty_obj is None:
            j.append('OPERATIONAL_PAUSE',{'reason':'INVALID_NOVELTY_ADVISOR_JSON','call_id':novelty_id})
            return {'status':'INVALID_NOVELTY_ADVISOR_JSON'}
        novelty=spe.validate_novelty(novelty_obj,{c['id'] for c in claims},evidence)
        science_delta=spe.prior_art_delta(state,novelty)
        impact_input={'program':base['program'],'current_problems':base['problems'],
                      'novelty':novelty,'evidence':evidence,'original_p0_unchanged':True,
                      'prior_working_problem_state':state,'prior_art_delta':science_delta}
        impact_id=spe._call_id('PMI',impact_input)
        impact_obj=strict_envelope(self.model.call(impact_id,'CONTROLLER',None,spe.IMPACT_PROMPT,impact_input))
        if impact_obj is None:
            j.append('OPERATIONAL_PAUSE',{'reason':'INVALID_PROBLEM_IMPACT_JSON','call_id':impact_id})
            return {'status':'INVALID_PROBLEM_IMPACT_JSON'}
        try:impact=spe.validate_impact(impact_obj,{c['id'] for c in claims},novelty,evidence,
                                      prior_working_problem_state=state)
        except EvidenceError as exc:
            j.append('OPERATIONAL_PAUSE',{'reason':'REJECTED_PROBLEM_IMPACT:'+str(exc),'call_id':impact_id})
            return {'status':'REJECTED_PROBLEM_IMPACT','detail':str(exc)}
    delta=spe.prior_art_delta(state,novelty)
    p0_delta=spe.problem_impact_delta(state,impact,delta)
    augmented={**base,'claim_prior_art_assessment':novelty,'problem_level_impact':impact,
       'working_problem_state_before_decision':state,'prior_art_delta':delta,
       'problem_impact_delta':p0_delta,'v3_material_science_fingerprint':fingerprint,
       'v3_assessment_status':'REUSED_PREVIOUS_COMMITTED_ASSESSMENT' if reused else 'NEW_MODEL_ASSESSMENT',
       'v3_science_work_options':_work_options(j),
       'feedback_call_provenance':{'novelty_model_call':novelty_id,
          'problem_impact_model_call':impact_id,
          'not_source_verified':True,'source_materials':[x['evidence_id'] for x in evidence],
          'assessment_reused':reused}}
    # Independent Opportunity Assessor remains a model advisory. Only call it
    # when scientific inputs or portfolio situation have genuinely changed.
    prior_actions=prior.get('v3_science_work_options') if prior else None
    def portfolio_identity(x):
        return sorted((w['work_id'],w['mode'],w['status']) for w in x.get('active_scientific_work',[])) if x else None
    if (reused and portfolio_identity(prior_actions)==portfolio_identity(augmented['v3_science_work_options'])
        and prior.get('independent_opportunity_assessment') is not None):
        opp=prior['independent_opportunity_assessment']
        opp_id=prior['opportunity_assessment_origin']['call_id']
        opp_reused=True
    else:
        opp_id='OPP_'+ident
        raw=self.model.call(opp_id,'CONTROLLER',None,spe.OPPORTUNITY_PROMPT,augmented)
        opp=spe.validate_opp(strict_envelope(raw),augmented)
        opp_reused=False
    full={**augmented,'independent_opportunity_assessment':opp,
        'opportunity_assessment_origin':{'call_id':opp_id,'status':'MODEL_ADVISORY_NOT_PRIMARY_EVIDENCE',
          'assessment_reused':opp_reused}}
    prompt=(CONTROLLER_PROMPT+(E3R1_CONTROLLER_ADDENDUM if j.verify().e3r1_policy else '')+
            '\n'+spe.CONTROLLER_FEEDBACK_ADDENDUM+'\n'+V3_ADVISORY)
    raw=self.model.call('CTRL_'+ident,'CONTROLLER',None,prompt,full)
    control=strict_envelope(raw)
    if control is None:
        j.append('OPERATIONAL_PAUSE',{'reason':'CONTROLLER_INVALID_JSON','call_id':'CTRL_'+ident})
        return {'status':'CONTROLLER_INVALID_JSON'}
    try:planned=controller_plan(j,control,'CTRL_'+ident,ident)
    except (EvidenceError,KeyError,TypeError,ValueError) as exc:
        j.append('OPERATIONAL_PAUSE',{'reason':'CONTROLLER_PLAN_REJECTED:'+str(exc)[:95],
                    'call_id':'CTRL_'+ident})
        return {'status':'CONTROLLER_PLAN_REJECTED','detail':str(exc)}
    j.append('CONTROLLER_DECISION',{'id':ident,'call_id':'CTRL_'+ident,
       'parsed_blob':j.blob(control),'rationale':control['rationale']})
    for kind,p in planned:j.append(kind,p)
    assess=control.get('objective_assessment') if j.verify().r5_policy else None
    return {'status':'CONTROLLER_COMMITTED','actions':len(control['actions']),
       'scientific_disposition':control['disposition'],
       'objective_status':assess.get('objective_status') if assess else None,
       'research_status':assess.get('research_status') if assess else None,
       'novelty_call_id':novelty_id,'problem_impact_call_id':impact_id,
       'opportunity_assessor_call_id':opp_id,'v3_reused_novelty_impact':reused,
       'v3_reused_opportunity':opp_reused}


@contextlib.contextmanager
def v3_runtime():
    oldc,oldg=spe.feedback_controller,spe.feedback_should_controller_run
    spe.feedback_controller=controller_v3
    spe.feedback_should_controller_run=should_controller_run
    try:yield
    finally:spe.feedback_controller=oldc;spe.feedback_should_controller_run=oldg


def run(root, paid, model, slice_budget,max_total_new_calls,iterations,parallel,tokens,cpu,wall,preflight=False):
    st=status(root)
    print(json.dumps({'event':'V3_PREFLIGHT',**st},ensure_ascii=False),flush=True)
    if preflight:return 0
    source_code_guard()
    guard(paid and os.environ.get('FAKG_RESEARCH_ALLOW_PAID')=='YES','EXPLICIT_PAID_APPROVAL_REQUIRED')
    guard(max_total_new_calls>0 and slice_budget>0,'INVALID_OPERATIONAL_BUDGET')
    if st['last_scientific_disposition'] in TERMINAL:return 0
    root=Path(root).expanduser().resolve()
    with open(root/'.scientific_feedback_autorun.lock','a+b') as fd:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise EvidenceError('ANOTHER_RUNNER_ACTIVE')
        try:
            used=0
            with v3_runtime():
                while used<max_total_new_calls:
                    remaining=max_total_new_calls-used
                    args=SimpleNamespace(call_budget=min(slice_budget,remaining),
                         checkpoint_iterations=iterations,max_parallel=parallel,
                         max_tokens=tokens,model=model,science_cpu_seconds=cpu,
                         science_wall_seconds=wall)
                    out=spe.run_feedback(str(root),args)
                    count=out['total_paid_new_calls'];used+=count
                    latest=status(root)
                    print(json.dumps({'event':'V3_CHECKPOINT','new_calls':count,
                         'paid_new_calls_this_launch':used,'stop_reason':out['stop_reason'],
                         'controllers':latest['controller_decisions'],'works':latest['works'],
                         'disposition':latest['last_scientific_disposition']},ensure_ascii=False),flush=True)
                    if latest['last_scientific_disposition'] in TERMINAL:return 0
                    if out['stop_reason']=='CALL_BUDGET' and count>0:continue
                    return 5
            print(json.dumps({'event':'OPERATOR_COST_GUARD','paid_new_calls_this_launch':used}),flush=True)
            return 4
        finally:fcntl.flock(fd,fcntl.LOCK_UN)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='cmd',required=True)
    x=sub.add_parser('fork');x.add_argument('--source-root',required=True);x.add_argument('--out-root',required=True)
    x=sub.add_parser('inspect');x.add_argument('--root',required=True)
    x=sub.add_parser('run');x.add_argument('--root',required=True);x.add_argument('--preflight',action='store_true')
    x.add_argument('--paid',action='store_true');x.add_argument('--model',default='openai/gpt-5.6-luna')
    x.add_argument('--slice-budget',type=int,default=12);x.add_argument('--max-total-new-calls',type=int,default=24)
    x.add_argument('--checkpoint-iterations',type=int,default=12);x.add_argument('--max-parallel',type=int,default=2)
    x.add_argument('--max-tokens',type=int,default=16000)
    x.add_argument('--science-cpu-seconds',type=int,default=120);x.add_argument('--science-wall-seconds',type=int,default=160)
    a=ap.parse_args()
    try:
        source_code_guard()
        if a.cmd=='fork':data=fork(a.source_root,a.out_root)
        elif a.cmd=='inspect':data=status(a.root)
        else:return run(a.root,a.paid,a.model,a.slice_budget,a.max_total_new_calls,
             a.checkpoint_iterations,a.max_parallel,a.max_tokens,a.science_cpu_seconds,
             a.science_wall_seconds,a.preflight)
        print(json.dumps(data,ensure_ascii=False,indent=2));return 0
    except EvidenceError as exc:
        print('V3_STOPPED_WITHOUT_SCIENTIFIC_DISPOSITION:'+str(exc),file=sys.stderr)
        return 3

if __name__=='__main__':raise SystemExit(main())
