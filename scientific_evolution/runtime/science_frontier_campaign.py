#!/usr/bin/env python3
"""OPTIONAL SCIENTIFIC CONTROLLER REDESIGN TRIAL (not original pipeline).

Two paid calls per Controller choice: independent opportunity assessment then final
Controller judgement. Both are durable model calls in the same append-only Journal.
The Controller may select none, literature, theory, synthesis, or a real hold; no
human-selected science work. Does not certify novelty. Do not reuse an existing ROOT.
"""
from __future__ import annotations
import argparse, json, pathlib
from e2core.core import EvolutionJournal, EvidenceError
from e2core.long_campaign import prepare_isolated_fresh, transfer_isolated_fresh, drive as base_drive
from e2core.engine import Engine, _external_context, CONTROLLER_PROMPT, E3R1_CONTROLLER_ADDENDUM, controller_plan
from e2core.provider import strict_envelope

OPPORTUNITY_PROMPT = '''You are a scientific research-opportunity assessor, not the final Controller. Your task is to independently examine available primary evidence, unverified hypothesis assets, counterexamples, unsolved questions, and available tools, to identify scientifically informative research actions. The original program objective remains primary. Under no circumstances assert novelty, physical truth or measurements not supported by provenance. Both literature acquisition and conditional theoretical/computational work are admissible now; literature novelty uncertainty need NOT block mathematical tests of conditional mechanisms. A failed primary source search is not a scientific null. Existing active work may be a reason to avoid duplicates, not to suppress genuinely complementary avenues. Do not force any work or continuation. Critically compare the information value and limitations of possible next actions, including no action if rational; explain why an action may be blocked or premature. Do not treat number of completed research steps or asset count as science. Be domain-general, not SERS-specific. You do NOT assign Work or mutate the Journal. Return exactly one JSON object:
{"opportunities":[{"question":"scientifically precise next question", "operation":"FRESH|DEVELOP|CHALLENGE|VERIFY|FUSE|MUTATE|DECOMPOSE|REFRAME|NO_ACTION", "parent_asset_ids":[], "expected_scientific_delta":"testable mathematical/empirical change, including falsification", "expected_information_value":"reasoned qualitative comparison", "preconditions":"assumptions, evidence, instruments or tools required", "failure_or_negative_value":"meaningful non-success learning", "overlap_with_active_work":"assessment"}], "global_uncertainties":[], "limitations":"This is advisory, not a scientific disposition or a certification"}. No fixed number of opportunities is required. If no worthwhile action exists use opportunities=[] and explain limitations.'''
CHOICE_ADDENDUM = '''Separate independent opportunity-assessor model output is supplied under independent_opportunity_assessment. It is a non-authoritative scientific proposal, NOT primary empirical evidence, not an executable plan and not a binding requirement. Explicitly compare its anticipated scientific deltas and preconditions against current evidence-acquisition alternatives and portfolio responsibilities; reject any or all if scientifically justified. Literature novelty assessment and conditional physics/math verification may be pursued concurrently; do not silently impose a universal novelty-first gate. Respect existing active work. Do NOT make up evidence or parent assets. Select and record only a scientifically justified next step or HOLD in the normal Controller schema. The assessed proposals are *not* extra scientific assets.''' 

def validate_opp(obj, context):
    ids={a['id'] for a in context['assets']}
    if not isinstance(obj,dict) or not isinstance(obj.get('opportunities'),list):
        return {'status':'INVALID_ASSESSOR_FORMAT','opportunities':[]}
    approved=[];rejected=[]
    for i,rec in enumerate(obj['opportunities']):
        if not isinstance(rec,dict):rejected.append({'index':i,'reason':'NOT_OBJECT'});continue
        parents=rec.get('parent_asset_ids',[])
        if not isinstance(parents,list) or not all(isinstance(a,str) and a in ids for a in parents):
            rejected.append({'index':i,'reason':'UNVERIFIED_OR_UNKNOWN_ASSET_ID'});continue
        if rec.get('operation') not in {'FRESH','DEVELOP','CHALLENGE','VERIFY','FUSE','MUTATE','DECOMPOSE','REFRAME','NO_ACTION'}:
            rejected.append({'index':i,'reason':'UNKNOWN_OPERATION'});continue
        if not str(rec.get('question','')).strip():rejected.append({'index':i,'reason':'MISSING_QUESTION'});continue
        # The proposal only: unknown science is NEVER upgraded into an accepted evidence asset.
        approved.append({k:rec.get(k) for k in ('question','operation','parent_asset_ids','expected_scientific_delta','expected_information_value','preconditions','failure_or_negative_value','overlap_with_active_work')})
    return {'status':'ADVISORY_ASSESSMENT_VALIDATED','opportunities':approved,'rejected':rejected,
            'global_uncertainties':obj.get('global_uncertainties',[]),'limitations':obj.get('limitations','')}


def opportunity_controller(self, ident):
    payload=_external_context(self.j,'NATIVE_RESEARCH_TOOLS' if self._native_tool_contract else 'CUSTOM_BACKEND_CAPABILITIES_UNDECLARED')
    raw=self.model.call('OPP_'+ident,'CONTROLLER',None,OPPORTUNITY_PROMPT,payload)
    obj=strict_envelope(raw)
    advice=validate_opp(obj,payload)
    # Preserve exact raw input and returned model result through MODEL_CALL_* events.
    # Invalid opportunity proposals do not translate to arbitrary generated work.
    controller_payload={**payload,'independent_opportunity_assessment':advice,
      'opportunity_assessment_origin':{'call_id':'OPP_'+ident,'actor':'CONTROLLER_ADVISORY_MODEL_CALL',
            'status':'NOT_VERIFIED_PRIMARY_OR_CONTROLLER_DECISION',
            'original_raw_response_persisted':True}}
    prompt=CONTROLLER_PROMPT+(E3R1_CONTROLLER_ADDENDUM if self.j.verify().e3r1_policy else '')+'\n'+CHOICE_ADDENDUM
    text=self.model.call('CTRL_'+ident,'CONTROLLER',None,prompt,controller_payload)
    raw_obj=strict_envelope(text)
    if raw_obj is None:
        self.j.append('OPERATIONAL_PAUSE',{'reason':'CONTROLLER_INVALID_JSON','call_id':'CTRL_'+ident})
        return {'status':'CONTROLLER_INVALID_JSON'}
    try:planned=controller_plan(self.j,raw_obj,'CTRL_'+ident,ident)
    except (EvidenceError,KeyError,TypeError,ValueError) as exc:
        self.j.append('OPERATIONAL_PAUSE',{'reason':'CONTROLLER_PLAN_REJECTED:'+str(exc)[:95],'call_id':'CTRL_'+ident})
        return {'status':'CONTROLLER_PLAN_REJECTED','detail':str(exc)}
    self.j.append('CONTROLLER_DECISION',{'id':ident,'call_id':'CTRL_'+ident,'parsed_blob':self.j.blob(raw_obj),'rationale':raw_obj['rationale']})
    for kind,p in planned:self.j.append(kind,p)
    assessment=raw_obj.get('objective_assessment') if self.j.verify().r5_policy else None
    return {'status':'CONTROLLER_COMMITTED','actions':len(raw_obj['actions']),
      'scientific_disposition':raw_obj['disposition'],
      'objective_status':assessment.get('objective_status') if assessment else None,
      'research_status':assessment.get('research_status') if assessment else None,
      'opportunity_assessor_call_id':'OPP_'+ident}


def prep(source_workspace, out_workspace):
    src=pathlib.Path(source_workspace).resolve();out=pathlib.Path(out_workspace).resolve()
    if out.exists():raise FileExistsError('NO_OVERWRITE:'+str(out))
    for cohort in ('FRESH_A','FRESH_B'):
        EvolutionJournal(src/cohort).verify()
    problem=src/'DISCOVERY_P0.txt'
    if not problem.is_file():raise FileNotFoundError('ORIGINAL_SERS_P0_MISSING')
    out.mkdir(parents=True)
    neutral=out/'NEUTRAL_BASE';phase_a=out/'AFTER_A';joined=out/'INFORMED_DUAL_JUDGEMENT'
    prepare_isolated_fresh(neutral,problem)
    a=transfer_isolated_fresh(neutral,src/'FRESH_A',phase_a)
    b=transfer_isolated_fresh(phase_a,src/'FRESH_B',joined)
    j=EvolutionJournal(joined);s=j.verify()
    if s.work or s.model_calls or s.controller_decisions:raise EvidenceError('PREPARED_ROOT_NOT_EMPTY')
    report={'status':'INDEPENDENT_A_B_IMPORTED_CONTROLLER_PROPOSAL_TRIAL_READY','root':str(joined),
            'imported_A':len(a['imported']),'imported_B':len(b['imported']),
            'controller_decisions':0,'paid_calls':0,'human_assigned_science_work':0,
            'experimental_intervention':'SECOND_ADVISORY_LLM_CALL_BEFORE_EACH_CONTROLLER_DECISION',
            'scientific_certification':False}
    (out/'TRIAL_MANIFEST.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return report


def run_with_proposals(root,args):
    # Scoped monkey patch for this process only: existing e2core files, existing ROOTs are unchanged.
    old=Engine.controller
    try:
        Engine.controller=opportunity_controller
        return base_drive(root,budget=args.call_budget,chunk=args.checkpoint_iterations,
                          max_tokens=args.max_tokens,model=args.model,cpu=args.science_cpu_seconds,
                          wall=args.science_wall_seconds,paid=True,parallel=args.max_parallel)
    finally:
        Engine.controller=old


def audit(root):
    j=EvolutionJournal(root);s=j.verify();records=[]
    for d in s.controller_decisions:
        ident=d['id'];op=s.model_calls.get('OPP_'+ident)
        ctrl=s.model_calls.get('CTRL_'+ident)
        if not ctrl:continue
        inp=json.loads(j.raw(ctrl['request_blob']))
        advice=json.loads(inp['messages'][1]['content']).get('independent_opportunity_assessment',{})
        d_raw=json.loads(j.raw(d['parsed_blob']))
        records.append({'id':ident,'assessor_call_saved':bool(op and op['state']=='SAVED'),
             'assessor_opportunities':advice.get('opportunities',[]),
             'controller_actions':[{'operation':a.get('operation'),
                                  'parent_asset_ids':a.get('asset_ids',[]),
                                  'question':(a.get('work') or {}).get('question')} for a in d_raw.get('actions',[])],
             'controller_scientific_disposition':d_raw.get('disposition'),
             'controller_reason':d_raw.get('rationale')})
    return {'status':'READ_ONLY_TWO_STAGE_CONTROLLER_AUDIT','root':str(j.root),
          'controller_decisions_with_assessor':len(records), 'records':records,
          'human_assigned_science_work':0,'scientific_certification':False}


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('prepare');a.add_argument('--source-workspace',required=True);a.add_argument('--out-workspace',required=True)
    b=sub.add_parser('drive');b.add_argument('--root',required=True);b.add_argument('--paid',action='store_true');b.add_argument('--model',default='openai/gpt-5.6-luna');b.add_argument('--max-parallel',type=int,default=2);b.add_argument('--call-budget',type=int,default=8);b.add_argument('--checkpoint-iterations',type=int,default=12);b.add_argument('--max-tokens',type=int,default=16000);b.add_argument('--science-cpu-seconds',type=int,default=120);b.add_argument('--science-wall-seconds',type=int,default=160)
    c=sub.add_parser('audit');c.add_argument('--root',required=True);c.add_argument('--out')
    args=p.parse_args()
    if args.cmd=='prepare':r=prep(args.source_workspace,args.out_workspace)
    elif args.cmd=='drive':
        if not args.paid:raise ValueError('REQUIRES_EXPLICIT_--paid')
        r=run_with_proposals(args.root,args)
    else:
        r=audit(args.root)
        if args.out:
            f=pathlib.Path(args.out).resolve()
            if f.exists():raise FileExistsError('NO_OVERWRITE:'+str(f))
            f.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(r,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
