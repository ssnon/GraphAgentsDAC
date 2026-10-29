#!/usr/bin/env python3
"""E2 Scientific Knowledge -> Claim -> Problem feedback loop.

EXPERIMENTAL INFORMED continuation. Doesn't mutate a concluded source ROOT,
change core Journal semantics, force any scientific answer, or certify novelty.
NVT / PMI are durable advisory LLM calls, followed by the existing Opportunity
Assessor and the original Final Controller. All four raw calls are journaled.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import shutil
from typing import Any

from e2core.core import EvolutionJournal, EvidenceError, canon, sha, guard, proper_id
from e2core.engine import (Engine, CONTROLLER_PROMPT, E3R1_CONTROLLER_ADDENDUM,
                           _external_context, controller_plan)
import e2core.engine as e2_engine
from e2core.provider import strict_envelope
from science_frontier_campaign import OPPORTUNITY_PROMPT, validate_opp
from e2core.long_campaign import drive as base_drive, locked_sources

# A judgement is a model-authored assessment, not a literature fact.
NOVELTY_RELATIONS = {
    'PRIOR_OVERLAP_REPORTED', 'PRIOR_CONTRADICTION_REPORTED',
    'PARTIAL_OVERLAP_REPORTED', 'NOT_FOUND_IN_INSPECTED_SCOPE',
    'INSUFFICIENT_PRIMARY_EVIDENCE', 'UNCERTAIN',
}
IMPACT_STATES = {
    'UNCHANGED', 'REFINED', 'PARTIALLY_RESOLVED', 'SOLUTION_INVALIDATED',
    'PREMISE_CHALLENGED', 'POTENTIALLY_RESOLVED',
}
DIRECT_CLASSES = {'DIRECT_FULLTEXT_EXCERPT', 'DIRECT_FIGURE_OR_METHOD_EXCERPT', 'OA_FULLTEXT_TEXT', 'OA_FULLTEXT_CAPTION'}

NOVELTY_PROMPT = '''You are an autonomous scientific prior-art analyst, NOT an experimental certifier. Given P0, candidate AI claims, and the clearly classified retrieved or operator-supplied sources, assess the *causal scientific content* of each candidate against what the sources actually establish. Novelty of a phrase, jargon, a routine transfer function or a small parameter tweak is not novel science. Distinguish established measurements, authors' interpretations, generic mathematical consequences, true contradictory evidence, source insufficiency and unsearched scope. Do not claim no prior art exists from absent or inaccessible sources. You are allowed to say UNCERTAIN. Each overlap/contradiction MUST cite at least one supplied evidence id and quote or precisely name the supplied relevant passage; metadata and abstracts alone do not prove an experimental finding. Note when a broad physical idea is known but a precise prediction could remain novel, then state the strong nulls it must defeat. Do not manufacture citations, physics parameters, or evidence. Do not infer experimental validation of an AI hypothesis. Evaluate each claim at the level of (a) known physical mechanism, (b) published equation or generic mathematical consequence, (c) published intervention/measurement, and (d) a prediction uniquely remaining after strong nulls. Distinguish literal priority, prior art by implication, and unsearched scope. Use the prior working-problem ledger ONLY as previously recorded non-certified assessment, not proof. In a genuine revision, state precisely what causal or predictive content would change; changing nomenclature or introducing an extra nuisance parameter is not sufficient. Do not infer experimental validation of an AI hypothesis. Return ONE JSON object with:
{"claim_assessments":[{"asset_id":"EXISTING_ID","relation":"PRIOR_OVERLAP_REPORTED|PRIOR_CONTRADICTION_REPORTED|PARTIAL_OVERLAP_REPORTED|NOT_FOUND_IN_INSPECTED_SCOPE|INSUFFICIENT_PRIMARY_EVIDENCE|UNCERTAIN","evidence_ids":[],"overlapping_or_contradicting_content":"...","remaining_conditional_claim":"...","specific_differentiating_prediction":"...","strongest_competing_explanation":"...","evidence_limitations":"...","known_components":"...","residual_hypothesis":"...","decisive_test":"..."}],"research_gaps":[],"global_limitations":"..."}. Assess as many relevant candidates as scientifically meaningful without forcing a fixed count. If no adequate evidence, keep verdicts insufficient or uncertain; do NOT certify novelty.'''

IMPACT_PROMPT = '''You are a scientific problem-reassessment researcher, NOT a success classifier. Preserve P0 exactly as posed, including its pre-experiment success criterion. Given model-authored novelty assessments and their original cited source classifications, ask how *each established, contradicted, or uncertain solution claim* affects the ORIGINAL P0, not just the candidate's attractiveness. A disproved solution is NOT a disproved problem; an already-established mechanism is NOT necessarily a solution to P0 requiring a new distinguishable explanation; an empirical finding in another system is not automatically applicable here. Describe coverage, missing requirements, changed premises, any new subproblem, and whether a proposed direction remains relevant. Distinguish a revised interpretation of P0 from editing P0 itself. Do not claim a source is verified just because a prior model cited it. The cumulative working-problem state in your input describes earlier MODEL assessments, not verified facts. Explicitly distinguish a newly changed P0 requirement from a paraphrase of an old requirement; if no new scientific consequence exists, prefer UNCHANGED. A previously rejected candidate is not a rejected original problem. A validated paper may solve a previously unanswered subquestion without satisfying P0's criterion for a NEW mechanism. Report a bounded residual scientific opportunity when supported, rather than automatically shifting into generic identifiability or source-retrieval loops. Do NOT force new Work or continued research. Return ONE JSON object:
{"claim_to_problem":[{"asset_id":"EXISTING_ASSET","relation_to_p0":"explains which original requirement is advanced or not","evidence_ids":[],"impact_on_solution":"...","impact_on_original_problem":"...","remaining_open_requirement":"..."}],"problem_impact":{"state":"UNCHANGED|REFINED|PARTIALLY_RESOLVED|SOLUTION_INVALIDATED|PREMISE_CHALLENGED|POTENTIALLY_RESOLVED","reason":"...","affected_requirements":[],"still_unresolved_requirements":[],"original_problem_still_open":true},"opportunities":[{"question":"...","value":"...","falsifier":"..."}],"limitations":"..."}. The problem_impact state describes a *provisional science interpretation*; never certify that the program is solved. If evidence is absent mark UNCHANGED or REFINED rather than inventing resolution.'''

CONTROLLER_FEEDBACK_ADDENDUM = '''The additional fields claim_prior_art_assessment and problem_level_impact are unverified MODEL-REASONED science assessments, NOT discovered facts, not a mandatory policy, and not instructions to choose a specific work. The original P0 is unchanged and paramount. Independently consider which primary claims are already supported/refuted in cited literature, what remains genuinely unexplained, which source limitations exist, how a solution revision may change the *problem's unsolved requirements*, and whether any proposed hypothesis has a distinctive, plausible pre-experiment prediction. A contradicted candidate does not refute P0. No primary-data access does not categorically block conditional theory. You may accept/reject assessor proposals or HOLD. Do not invent references, certify novelty, force publications or rewrite the original objective. Use the usual Controller JSON contract. Prioritize actual causal or quantitative scientific delta toward P0 over the volume of status monitoring, literature searching, or general statistical-model sophistication. You can reject or disregard the working ledger if the underlying reasoning is wrong.'''


def _read_json_bytes(raw):
    try: return json.loads(raw)
    except (ValueError, TypeError): return None


def validate_packet(obj):
    """Exact attributed excerpts. No claim that the submitting operator verified content."""
    guard(isinstance(obj, dict) and isinstance(obj.get('records'), list), 'EVIDENCE_PACKET_RECORDS_REQUIRED')
    seen = set(); cleaned = []
    for rec in obj['records']:
        guard(isinstance(rec, dict) and proper_id(rec.get('id')) and rec['id'] not in seen,
              'BAD_OR_DUPLICATE_EVIDENCE_ID')
        seen.add(rec['id'])
        kind = rec.get('inspection_class')
        guard(kind in {'DIRECT_FULLTEXT_EXCERPT','DIRECT_FIGURE_OR_METHOD_EXCERPT', 'ABSTRACT_ONLY', 'BIBLIOGRAPHIC_METADATA', 'OPERATOR_SUMMARY'},
              'EVIDENCE_CLASS_REQUIRED')
        for k in ('title', 'locator', 'origin_url_or_doi', 'excerpt'):
            guard(isinstance(rec.get(k), str) and rec[k].strip(), 'EVIDENCE_FIELD_MISSING:'+k)
        guard(len(rec['excerpt']) <= 16000, 'EVIDENCE_EXCERPT_TOO_LARGE')
        if kind in DIRECT_CLASSES:
            guard(bool(str(rec.get('inspection_method','')).strip()) and
                  bool(str(rec.get('locator','')).strip()), 'DIRECT_EVIDENCE_NEEDS_METHOD_AND_LOCATOR')
        cleaned.append({k:rec.get(k) for k in ('id','inspection_class','title','locator',
             'origin_url_or_doi','excerpt','inspection_method','scope_limits')})
    guard(cleaned, 'EMPTY_EVIDENCE_PACKET')
    return cleaned


def ancestry(s, selected):
    ids = set();visiting=set()
    def visit(aid):
        guard(aid in s.assets, 'UNKNOWN_SELECTED_ASSET:'+str(aid))
        if aid in ids:return
        guard(aid not in visiting,'CYCLE_IN_ASSET_DAG')
        visiting.add(aid)
        for pid in s.assets[aid].get('parent_ids',[]):visit(pid)
        visiting.remove(aid);ids.add(aid)
    for aid in selected:visit(aid)
    return [aid for aid in s.assets if aid in ids]


def fork_informed(source_root, out_root, selected, evidence_json=None):
    src=pathlib.Path(source_root).expanduser().resolve()
    dst=pathlib.Path(out_root).expanduser().resolve()
    guard(src!=dst and not dst.exists(),'NO_OVERWRITE_AND_DISTINCT_ROOT_REQUIRED')
    with locked_sources(src):
        sj=EvolutionJournal(src);s=sj.verify()
        guard(s.program is not None,'SOURCE_HAS_NO_PROGRAM')
        chosen=ancestry(s,selected)
        guard(chosen,'AT_LEAST_ONE_SELECTED_CLAIM_REQUIRED')
        # Prepare as a new, explicitly informed ROOT. The source's scientific
        # terminal state is preserved, never erased or retroactively resumed.
        dj=EvolutionJournal(dst)
        dj.init(s.program['problem'],origin='EXPLICIT_INFORMED_CONTINUATION_AFTER_TERMINAL_ROOT',
                criteria='New pre-experiment hypothesis candidates and problem-level prior-art impact; original problem unchanged')
        dj.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        dj.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
        # Preserve the selected asset problem DAG and its parent science exactly.
        needed=set()
        def needed_problem(pid):
            if pid=='P0' or pid in needed:return
            guard(pid in s.problems,'UNKNOWN_PARENT_PROBLEM')
            for pa in s.problems[pid].get('parents',[]):needed_problem(pa)
            needed.add(pid)
        for aid in chosen:needed_problem(s.assets[aid]['problem_id'])
        for pid,p in s.problems.items():
            if pid in needed:
                dj.append('PROBLEM_CREATED',{k:v for k,v in p.items() if k!='status'})
        for aid in chosen:
            a=s.assets[aid];pid=a.get('parent_ids',[])
            guard(all(x in dj.verify().assets for x in pid), 'IMPORT_DAG_ORDER')
            sid='SRC_INHERITED_'+sha(canon({'root':str(src),'asset':aid}))[:23]
            # Exact archived model product and provenance. This is never
            # registered as external primary literature or a live discovery.
            digest=dj.add_source(sid,'HISTORICAL_AI',{
                'ref':str(src)+'#'+aid,
                'science':{'scientific_work':a['claim'],
                           'scientific_delta':a.get('delta_from_parents',''),
                           'scope':a.get('scope',''), 'assumptions':a.get('assumptions',''),
                           'predictions':a.get('predictions',[]),
                           'limitations':a.get('limitations',[]),
                           'original_parent_ids':a.get('parent_ids',[]),
                           'original_asset':a},
                'tool_result':{'status':'NOT_CERTIFIED_BY_IMPORT'},
                'science_sha256':sha(canon(a)),
                'original_root':str(src), 'original_asset_id':aid,
                'original_source_records':[s.sources[x] for x in a.get('source_ids',[])],
                'original_origin':'INHERITED_AI_NOT_NEW_SCIENCE'},
                'Inherited model claim, not a verified source: '+str(src)+'#'+aid)
            dj.append('HISTORICAL_ASSET_INDEXED',{
                'id':aid,'kind':a['kind'],'problem_id':a['problem_id'],
                'parent_ids':pid,'claim':a['claim'],'scope':a.get('scope') or 'Original source scope',
                'assumptions':a.get('assumptions') or 'Original conditional assumptions',
                'predictions':a.get('predictions',[]),'limitations':a.get('limitations',[]),
                'delta_from_parents':a.get('delta_from_parents',''),
                'original_root':str(src),'original_asset_id':aid,
                'source_ids':[sid],'source_ref':str(src)+'#'+aid,
                'source_science_sha256':sha(canon(a)),
                'catalog_sha256':digest})
        # Preserve inspectable original tool-returned literature (not bibliographic
        # links) as inherited evidence. This does NOT re-execute a search or
        # promote prior AI summaries into independent empirical findings.
        evidence_ids=[]
        for old_sid, source_record in s.sources.items():
            if source_record['kind']!='TOOL_RESULT':continue
            label=str(source_record.get('description',''))
            if not any(x in label for x in ('OA_FULLTEXT_TEXT','OA_FULLTEXT_CAPTION')):continue
            inherited_data=_read_json_bytes(sj.raw(source_record['blob']))
            if not isinstance(inherited_data,dict):continue
            tool_id=inherited_data.get('tool_id')
            source_tool=s.tool_results.get(tool_id)
            # Require recorded tool provenance, not merely a source label.
            if (not source_tool or source_tool.get('work_id')!=source_record.get('work_id')
                or inherited_data.get('result')!=_read_json_bytes(sj.raw(source_tool['result_blob']))):
                continue
            new_sid='SRC_INHERITED_TOOL_'+sha(canon({'root':str(src),'sid':old_sid}))[:22]
            dj.add_source(new_sid,'EXTERNAL_AUDIT',{
                'kind':'INHERITED_REAL_EXECUTION_TOOL_RESULT_NOT_NEW_OBSERVATION',
                'original_root':str(src),'original_tool_source_id':old_sid,
                'original_tool_id':tool_id,
                'original_record_sha256':sha(sj.raw(source_record['blob'])),
                'evidence_class':('OA_FULLTEXT_CAPTION' if 'OA_FULLTEXT_CAPTION' in label else 'OA_FULLTEXT_TEXT'),
                'original_returned_data':inherited_data,
                'not_independently_certified':True},
                'Inherited actual research-tool excerpt, not a new source inspection: '+old_sid)
            evidence_ids.append(new_sid)
        if evidence_json:
            packet_path=pathlib.Path(evidence_json).expanduser().resolve()
            packet_bytes=packet_path.read_bytes()
            records=validate_packet(json.loads(packet_bytes))
            for r in records:
                sid='SRC_PRIOR_'+r['id']
                guard(sid not in dj.verify().sources,'EVIDENCE_ID_COLLISION')
                dj.add_source(sid,'EXTERNAL_AUDIT',{
                    'kind':'OPERATOR_SUBMITTED_LITERATURE_EXCERPT_NOT_INDEPENDENTLY_VERIFIED',
                    'record':r, 'packet_sha256':sha(packet_bytes),
                    'original_file_name':packet_path.name},
                    'Operator-supplied prior-art candidate; not independently certified: '+r['title'])
                evidence_ids.append(sid)
        # This event forces the first Controller to explicitly consider the
        # carried-over science without pretending any newly concluded discovery.
        dj.append('R5_INTEGRATION_REQUESTED',{
            'foreign_root':str(src),'asset_ids':chosen,'event_seq':len(dj._events())+1,
            'reason':'Operator requested a new autonomous literature-to-claim-to-problem reassessment; no human-assigned scientific Work'})
        new=dj.verify()
        guard(new.program['problem']==s.program['problem'] and not new.work and not new.controller_decisions and not new.model_calls,
              'PREPARE_INVALID_ROOT_STATE')
        report={'status':'NEW_INFORMED_PROBLEM_FEEDBACK_ROOT_READY', 'root':str(dst),
                'original_root':str(src),'original_root_last_review':s.program_reviews[-1]['scientific_status'] if s.program_reviews else None,
                'original_program_sha256':sha(s.program['problem'].encode()),
                'selected_assets':selected,'imported_ancestor_assets':chosen,'submitted_evidence_source_ids':evidence_ids,
                'no_human_assigned_work':True,'novelty_certification':False,'science_certification':False}
        manifest=dst/'FEEDBACK_PREPARE_MANIFEST.json'
        manifest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
        guard(sj.verify().program['problem']==new.program['problem'],'SOURCE_PROGRAM_CHANGED')
        return report


def ingest_external_evidence(root, literature_json):
    """Append new operator-submitted literature to an ONGOING root, safely.

    The package is classified external operator input, never a live primary
    tool execution. New material may trigger a Controller reassessment but does
    not dictate a scientific direction or mutate existing claims.
    """
    path=pathlib.Path(root).expanduser().resolve()
    with locked_sources(path):
        j=EvolutionJournal(path);s=j.verify()
        guard(not (s.program_reviews and s.program_reviews[-1]['scientific_status'] in
            {'HOLD_WITH_RATIONALE','REVIEW_WORTHY_CANDIDATE','SCOPED_NEGATIVE'}),
            'TERMINAL_ROOT_REQUIRES_NEW_FORK')
        guard(all(x['state']=='SAVED' for x in s.model_calls.values()),
            'PENDING_OR_UNCERTAIN_MODEL_CALL_PREVENTS_EXTERNAL_MUTATION')
        raw=pathlib.Path(literature_json).expanduser().resolve().read_bytes()
        records=validate_packet(json.loads(raw))
        guard(all('SRC_PRIOR_'+x['id'] not in s.sources for x in records),'EVIDENCE_ALREADY_REGISTERED')
        ids=[]
        for record in records:
            ident='SRC_PRIOR_'+record['id']
            j.add_source(ident,'EXTERNAL_AUDIT',{
                'kind':'OPERATOR_SUBMITTED_LITERATURE_EXCERPT_NOT_INDEPENDENTLY_VERIFIED',
                'record':record,'packet_sha256':sha(raw),
                'original_file_name':pathlib.Path(literature_json).name},
                'New operator-submitted prior-art material; NOT a fact certification')
            ids.append(ident)
        return {'status':'APPEND_ONLY_NEW_PRIOR_ART_REGISTERED',
                'root':str(j.root),'new_evidence_ids':ids,
                'science_certification':False,'novelty_certification':False}


def classified_evidence(j):
    """Only original source material; classes enforce claims ≠ evidence."""
    s=j.verify(); items=[]
    for sid,rec in s.sources.items():
        if rec['kind']=='EXTERNAL_AUDIT' and sid.startswith('SRC_PRIOR_'):
            data=_read_json_bytes(j.raw(rec['blob'])) or {}
            r=data.get('record',{})
            if r:
                items.append({'evidence_id':sid,**r,
                      'source_kind':'OPERATOR_SUBMITTED_UNVERIFIED',
                      'not_independently_certified':True})
        elif rec['kind']=='EXTERNAL_AUDIT' and sid.startswith('SRC_INHERITED_TOOL_'):
            data=_read_json_bytes(j.raw(rec['blob'])) or {}
            returned=data.get('original_returned_data',{})
            result=returned.get('result',{})
            contents=json.dumps(result,ensure_ascii=False)
            items.append({'evidence_id':sid,'source_kind':'INHERITED_EXECUTED_TOOL_RESULT',
                'inspection_class':data.get('evidence_class'),
                'original_tool_id':data.get('original_tool_id'),
                'original_tool_source_id':data.get('original_tool_source_id'),
                'original_root':data.get('original_root'),
                'returned_content':contents[:6000], 'truncated':len(contents)>6000,
                'not_independently_certified':True})
        elif rec['kind']=='TOOL_RESULT':
            data=_read_json_bytes(j.raw(rec['blob'])) or {}
            result=data.get('result') or {}
            evidence_class=data.get('evidence_class') or result.get('evidence_class') or 'UNKNOWN'
            # Label actual tool-returned material without upgrading a bibliographic
            # search result or link to measured full text.
            items.append({'evidence_id':sid,'source_kind':'ACTUAL_TOOL_RESULT',
                'inspection_class':str(evidence_class), 'tool_result_id':data.get('tool_id'),
                'tool_name':data.get('request',{}).get('kind'),
                'returned_content':json.dumps(result,ensure_ascii=False)[:5000],
                'truncated':len(json.dumps(result,ensure_ascii=False))>5000,
                'not_independently_certified':True})
    return items


def target_claims(context,j):
    # Selected inherited claims + new live scientific claims, excluding evidence
    # acquisition status updates if they don't assert a mechanistic proposition.
    manifest_path=j.root/'FEEDBACK_PREPARE_MANIFEST.json'
    selection=set(json.loads(manifest_path.read_text(encoding='utf8')).get('selected_assets',[])) if manifest_path.is_file() else set()
    return [{'id':a['id'],'kind':a['kind'],'claim':a['claim'],
              'predictions':a.get('predictions',[]),'assumptions':a.get('assumptions'),
              'limitations':a.get('limitations',[]),'origin':a.get('origin')}
             for a in context['assets'] if (a['id'] in selection or a.get('origin')=='LIVE_WORK')
             and a['kind'] in
             {'HYPOTHESIS','PREDICTION','CALCULATION','NULL_MODEL','COUNTEREXAMPLE','SCOPED_NEGATIVE'}]


def validate_novelty(obj, asset_ids, evidence_items):
    valid_evidence={x['evidence_id']:x for x in evidence_items}
    guard(isinstance(obj,dict) and isinstance(obj.get('claim_assessments'),list),'INVALID_NOVELTY_OUTPUT')
    out=[];rejected=[]
    for i,a in enumerate(obj['claim_assessments']):
        if not isinstance(a,dict) or a.get('asset_id') not in asset_ids or a.get('relation') not in NOVELTY_RELATIONS:
            rejected.append({'index':i,'reason':'UNKNOWN_ASSET_OR_RELATION'});continue
        cites=a.get('evidence_ids',[])
        if not isinstance(cites,list) or any(x not in valid_evidence for x in cites):
            rejected.append({'index':i,'reason':'UNKNOWN_EVIDENCE_REFERENCE'});continue
        if a['relation'] in {'PRIOR_OVERLAP_REPORTED','PRIOR_CONTRADICTION_REPORTED','PARTIAL_OVERLAP_REPORTED'}:
            if not cites:
                rejected.append({'index':i,'reason':'CLAIM_OF_PRIOR_ART_WITHOUT_SOURCE'});continue
            if not any(valid_evidence[x].get('inspection_class') in DIRECT_CLASSES for x in cites):
                rejected.append({'index':i,'reason':'PRIOR_ART_CLAIM_ONLY_METADATA_OR_ABSTRACT'});continue
        if a['relation']=='NOT_FOUND_IN_INSPECTED_SCOPE' and not cites:
            rejected.append({'index':i,'reason':'NO_REVIEWED_SCOPE_DOCUMENTED'});continue
        # Evidence quality is explicit; literature metadata is never silently
        # promoted to a full-text verification.
        quality='DIRECT_TEXT_REFERENCED' if cites and all(valid_evidence[x].get('inspection_class') in DIRECT_CLASSES for x in cites) else 'INSUFFICIENT_OR_MIXED_EVIDENCE'
        out.append({**{k:a.get(k,'') for k in ('asset_id','relation','evidence_ids',
                 'overlapping_or_contradicting_content','remaining_conditional_claim',
                 'specific_differentiating_prediction','strongest_competing_explanation','evidence_limitations',
                 'known_components','residual_hypothesis','decisive_test')},
                 'evidence_quality':quality,'certification':False})
    return {'claim_assessments':out,'rejected':rejected,'research_gaps':obj.get('research_gaps',[]),
            'global_limitations':obj.get('global_limitations',''),'novelty_certification':False}


def validate_impact(obj, asset_ids, novelty, evidence_items=None, prior_working_problem_state=None):
    """Use registered citations, quarantine invented refs, never certify P0.

    A PMI advisor may read a registered source that the novelty advisor did not
    cite. The old implementation rejected the *whole* scientific decision when
    this happened. Conversely, a model-generated unknown ID must never become
    evidence. Keep raw PMI text in its durable MODEL_CALL_SAVED record, but
    quarantine affected advisory rows and conservatively downgrade the overall
    P0 status if they underpinned it. This is not a scientific rebuttal.
    """
    guard(isinstance(obj,dict) and isinstance(obj.get('claim_to_problem'),list) and
          isinstance(obj.get('problem_impact'),dict),'INVALID_PROBLEM_IMPACT_OUTPUT')
    accepted_novelty_cites={x for a in novelty.get('claim_assessments',[])
                            for x in a.get('evidence_ids',[])}
    evidence_by_id={r['evidence_id']:r for r in (evidence_items or [])}
    allowed=set(evidence_by_id) if evidence_items is not None else accepted_novelty_cites
    recs=[]; rejected=[]; not_novelty_reviewed=[]
    for i,a in enumerate(obj['claim_to_problem']):
        # Invalid model-authored cross-references must not veto every other
        # valid scientific assessment. The exact raw PMI remains saved in the
        # Journal, while this individual advisory is quarantined.
        if not isinstance(a,dict):
            rejected.append({'index':i,'asset_id':None,
                             'reason':'MALFORMED_IMPACT_ROW'})
            continue
        aid=a.get('asset_id')
        if not isinstance(aid,str) or aid not in asset_ids:
            rejected.append({'index':i,'asset_id':str(aid)[:200],
                             'reason':'IMPACT_ASSET_OUTSIDE_REVIEW_SCOPE'})
            continue
        refs=a.get('evidence_ids')
        if not isinstance(refs,list):
            rejected.append({'index':i,'asset_id':aid,
                             'reason':'INVALID_IMPACT_EVIDENCE_LIST'})
            continue
        invalid=sorted(set(str(x) for x in refs if not isinstance(x,str) or x not in allowed))
        if invalid:
            # No unsupported assertion is passed as an accepted claim-to-P0
            # inference. Preserve the exact original in the saved PMI wire.
            rejected.append({'index':i,'asset_id':a['asset_id'],
                             'reason':'UNREGISTERED_EVIDENCE_ID',
                             'unregistered_evidence_ids':invalid})
            continue
        additional=sorted(set(refs)-accepted_novelty_cites)
        if additional:
            not_novelty_reviewed.append({'index':i,'asset_id':a['asset_id'],
                                          'registered_but_not_novelty_reviewed_ids':additional})
        recs.append({**a,'is_provisional_model_assessment':True,
                     'evidence_review_status':('REGISTERED_NOT_ASSESSED_BY_NOVELTY'
                                               if additional else 'NOVELTY_CITATIONS_OR_NO_CITES'),
                     'evidence_certification':False})
    imp=obj['problem_impact']
    guard(imp.get('state') in IMPACT_STATES,'INVALID_PROBLEM_IMPACT_STATE')
    guard(isinstance(imp.get('still_unresolved_requirements'),list) and
          isinstance(imp.get('affected_requirements'),list) and
          isinstance(imp.get('original_problem_still_open'),bool),'BAD_IMPACT_REQUIREMENTS')
    proposed_state=imp['state']
    safe_impact={**imp,'is_provisional_model_assessment':True}
    safe_impact['original_problem_still_open']=True  # Only an advisory; never auto-close P0
    # When the model invents sources or claims the original problem closed,
    # no resolution/invalidation of P0 may travel downstream as a fact.
    if (proposed_state in {'PARTIALLY_RESOLVED','SOLUTION_INVALIDATED','PREMISE_CHALLENGED','POTENTIALLY_RESOLVED'}
          and not any(r.get('evidence_ids') and any(evidence_by_id.get(x,{}).get('inspection_class') in DIRECT_CLASSES
            for x in r['evidence_ids']) for r in recs) and evidence_items is not None):
        safe_impact['state']='REFINED'
        safe_impact['validation_downgrade_reason']='NO_DIRECT_SOURCE_FOR_STRONG_PROBLEM_CHANGE'
    if rejected:
        # Any discarded inference may have been used by the PMI model to
        # justify the global P0 conclusion. Keep valid individual rows, but
        # withhold ALL new global P0 inferences, including generated requirement
        # prose and opportunities potentially relying on a rejected claim.
        previous=((prior_working_problem_state or {}).get('latest_working_p0') or {})
        safe_impact['state']='UNCHANGED'
        safe_impact['original_problem_still_open']=True
        safe_impact['affected_requirements']=[]
        safe_impact['still_unresolved_requirements']=list(previous.get('still_unresolved_requirements') or [])
        safe_impact['reason']=('Some model-authored claim references or citations failed '
            'validation; only accepted per-claim assessments are forwarded. '
            'The original P0 remains open and no new global P0 conclusion is accepted.')
        reasons={x.get('reason') for x in rejected}
        safe_impact['validation_downgrade_reason']=(
            'INVALID_IMPACT_CLAIM_OR_EVIDENCE_REFERENCE'
            if reasons != {'UNREGISTERED_EVIDENCE_ID'}
            else 'UNREGISTERED_EVIDENCE_CITATIONS')
    elif (not_novelty_reviewed and safe_impact['state']==proposed_state and proposed_state in {
        'PARTIALLY_RESOLVED','SOLUTION_INVALIDATED','PREMISE_CHALLENGED','POTENTIALLY_RESOLVED'}):
        safe_impact['state']='REFINED'
        safe_impact['original_problem_still_open']=True
        safe_impact['reason']=('Some cited sources were registered but have not been '
            'accepted as relevant overlap/contradiction in the novelty assessment. '
            'Only provisional problem refinement may be forwarded.')
        safe_impact['validation_downgrade_reason']='REGISTERED_SOURCE_NOT_NOVELTY_REVIEWED'
    # Retain exact proposed semantics ONLY as clearly labeled raw model opinion;
    # the durable original source remains the journaled PMI response.
    return {'claim_to_problem':recs,'problem_impact':safe_impact,
            'model_proposed_impact_state':proposed_state,
            'rejected_impact_inferences':rejected,
            'registered_unreviewed_citations':not_novelty_reviewed,
            'citation_validation_complete':not rejected,
            'opportunities':([] if rejected else obj.get('opportunities',[])),
            'quarantined_unverified_opportunities':len(obj.get('opportunities',[])) if rejected and isinstance(obj.get('opportunities',[]),list) else 0,
            'limitations':obj.get('limitations',''),
            'original_problem_modified':False,
            'science_certification':False,'novelty_certification':False}



# This is a derived, READ-ONLY model-assessment ledger, not a second Controller
# or a truth table. Every entry is replayable from committed Controller inputs.
def _historical_problem_context(j, state=None):
    state=state or j.verify()
    for sid, rec in state.sources.items():
        if sid.startswith('SRC_HISTORICAL_PROBLEM_V2_') and rec['kind']=='HISTORICAL_AI':
            result=_read_json_bytes(j.raw(rec['blob']))
            if isinstance(result,dict):return result
    return None


def _read_controller_context(j, d, state=None):
    state=state or j.verify()
    rec=state.model_calls.get('CTRL_'+d['id'])
    if not rec or rec['state']!='SAVED':return None
    try:
        wire=json.loads(j.raw(rec['request_blob']))
        return json.loads(wire['messages'][1]['content'])
    except (ValueError,TypeError,KeyError,IndexError):return None


def _relation_key(row):
    return (row.get('relation'),tuple(sorted(set(row.get('evidence_ids',[])))))


def working_problem_state(j):
    """Compact cumulative claim/P0 interpretation, preserving source boundaries.

    Repeated free-form paraphrases do not count as scientific progress. Changes
    are keyed to existing claim identity, the accepted prior-art relation, and
    registered evidence IDs; an audit report can inspect full raw model prose.
    """
    s=j.verify(); latest={}; history=[]; latest_problem=None; previously=[]
    for d in s.controller_decisions:
        ctx=_read_controller_context(j,d,s)
        if not ctx:continue
        novelty=ctx.get('claim_prior_art_assessment') or {}
        for row in novelty.get('claim_assessments',[]):
            aid=row.get('asset_id')
            if not aid:continue
            key=_relation_key(row)
            old=latest.get(aid)
            if old is None or _relation_key(old)!=key:
                history.append({'decision':d['id'],'asset_id':aid,
                    'relation':row.get('relation'),'evidence_ids':row.get('evidence_ids',[]),
                    'change_type':'FIRST_REVIEW' if old is None else 'PRIOR_ART_RELATION_OR_SOURCE_CHANGED'})
            latest[aid]=row
        p=(ctx.get('problem_level_impact') or {}).get('problem_impact')
        if isinstance(p,dict):
            if latest_problem is None or p.get('state')!=latest_problem.get('state'):
                previously.append({'decision':d['id'],'state':p.get('state')})
            latest_problem=p
    manifest=j.root/'FEEDBACK_PREPARE_MANIFEST.json'
    selected=[]
    if manifest.is_file():
        try:selected=json.loads(manifest.read_text(encoding='utf8')).get('selected_assets',[])
        except (ValueError,TypeError):pass
    # Known facts ≠ reported claims. Carry current interpretation as advisory only.
    compact={aid:{'relation':r.get('relation'),
         'evidence_ids':sorted(set(r.get('evidence_ids',[]))),
         'remaining_conditional_claim':str(r.get('remaining_conditional_claim',''))[:1100],
         'specific_differentiating_prediction':str(r.get('specific_differentiating_prediction',''))[:1100],
         'residual_hypothesis':str(r.get('residual_hypothesis',''))[:900],
         'certification':False}
         for aid,r in latest.items()}
    return {'provenance':'RECONSTRUCTED_FROM_COMMITTED_CONTROLLER_PROMPTS',
        'model_assessment_only':True,'original_problem_immutable':True,
        'historical_source_assessment':_historical_problem_context(j,s),
        'current_claim_assessments':compact,
        'claim_relation_changes':history[-50:],
        'latest_working_p0':({
            'state':latest_problem.get('state'),
            'still_unresolved_requirements':latest_problem.get('still_unresolved_requirements',[]),
            'affected_requirements':latest_problem.get('affected_requirements',[]),
            'reason':str(latest_problem.get('reason',''))[:1600],
            'original_problem_still_open':True,
        } if latest_problem else {'state':'OPEN_UNREASSESSED','original_problem_still_open':True}),
        'historical_problem_status_changes':previously[-25:],
        'original_selected_candidates':selected}


def prior_art_delta(previous, novelty):
    """Classify changes in evidence-linked claims without truth certification."""
    baseline=previous.get('current_claim_assessments',{})
    changes=[];unchanged=[]
    for row in novelty.get('claim_assessments',[]):
        aid=row['asset_id'];old=baseline.get(aid)
        if old is None:why='FIRST_LIVE_CLAIM_ASSESSMENT'
        elif _relation_key(old)!=_relation_key(row):why='EVIDENCE_LINK_OR_PRIOR_RELATION_CHANGED'
        else:why=None
        if why:
            changes.append({'asset_id':aid,'change':why,
               'previous_relation':old.get('relation') if old else None,
               'current_relation':row['relation'],
               'previous_evidence_ids':old.get('evidence_ids',[]) if old else [],
               'current_evidence_ids':row.get('evidence_ids',[]),
               'certified':False})
        else:unchanged.append(aid)
    return {'status':'NEW_MODEL_INTERPRETATION' if changes else 'NO_NEW_CLAIM_SOURCE_RELATION',
        'new_or_changed_claims':changes,
        'unchanged_claim_ids':unchanged,
        'rejected_advisory_rows':len(novelty.get('rejected',[])),
        'note':'Source/claim differences only; neither semantic novelty nor causality is automatically certified.'}


def problem_impact_delta(previous, impact, novelty_delta):
    prev=previous.get('latest_working_p0') or {}
    this=impact.get('problem_impact') or {}
    old_state=prev.get('state','OPEN_UNREASSESSED')
    new_state=this.get('state','UNCHANGED')
    old_reqs={str(x).strip() for x in prev.get('still_unresolved_requirements',[]) if str(x).strip()}
    new_reqs={str(x).strip() for x in this.get('still_unresolved_requirements',[]) if str(x).strip()}
    # Exact text differences are only textual suggestions, NOT independent
    # scientific deltas. Source/claim relation changes and status changes are
    # recorded separately.
    return {'previous_status':old_state,'current_status':new_state,
            'status_changed':old_state!=new_state,
            'new_requirement_wording_not_necessarily_new_science':sorted(new_reqs-old_reqs)[:18],
            'old_requirement_wording_not_necessarily_resolved':sorted(old_reqs-new_reqs)[:18],
            'claim_evidence_relation_changed':bool(novelty_delta.get('new_or_changed_claims')),
            'requires_independent_scientific_interpretation':True,
            'original_p0_still_immutable':True,
            'proof_of_problem_resolution':False}


def _past_problem_summary_from_root(src, selected):
    """Carry source Controller knowledge without promoting it to primary evidence."""
    j=EvolutionJournal(src);s=j.verify();latest={};change_count={}
    for d in s.controller_decisions:
        ctx=_read_controller_context(j,d,s)
        if not ctx:continue
        for r in (ctx.get('claim_prior_art_assessment') or {}).get('claim_assessments',[]):
            aid=r.get('asset_id')
            if aid in selected:
                key=_relation_key(r)
                if aid not in latest or _relation_key(latest[aid])!=key:
                    change_count[aid]=change_count.get(aid,0)+1
                latest[aid]=r
    last=(s.controller_decisions[-1]['id'] if s.controller_decisions else None)
    last_ctx=_read_controller_context(j,{'id':last},s) if last else {}
    last_impact=((last_ctx or {}).get('problem_level_impact') or {}).get('problem_impact') or {}
    return {'source_root':str(j.root),'source_last_controller':last,
        'source_terminal_status':s.program_reviews[-1]['scientific_status'] if s.program_reviews else None,
        'origin_type':'HISTORICAL_MODEL_ASSESSMENTS_NOT_PRIMARY_LITERATURE',
        'selected_claim_prior_art':{aid:{
            'relation':r.get('relation'),'evidence_ids':r.get('evidence_ids',[]),
            'remaining_conditional_claim':r.get('remaining_conditional_claim'),
            'specific_differentiating_prediction':r.get('specific_differentiating_prediction'),
            'history_changes':change_count.get(aid,0),'independent_certification':False}
            for aid,r in latest.items()},
        'last_problem_impact':{'state':last_impact.get('state'),
            'still_unresolved_requirements':last_impact.get('still_unresolved_requirements',[]),
            'note':'Last model-authored advisory, not a proof or an update to P0'},
        'original_problem_immutable':True}


def prepare_delta_root(src, dst, selected, evidence_json=None):
    result=fork_informed(src,dst,selected,evidence_json)
    # Add after fork in append-only Journal. This source can be read by the next
    # Controller but never classified as an empirical literature result.
    j=EvolutionJournal(dst)
    context=_past_problem_summary_from_root(src,selected)
    ident='SRC_HISTORICAL_PROBLEM_V2_'+sha(canon(context))[:16]
    j.add_source(ident,'HISTORICAL_AI',context,
       'Inherited model-only prior-art and problem-impact assessments from concluded root')
    result['historical_problem_context_source']=ident
    result['new_root_science_certified']=False
    manifest=j.root/'FEEDBACK_PREPARE_MANIFEST.json'
    manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    return result


def _call_id(prefix, payload):
    # Cache by input science/evidence content, not by Controller decision number.
    # Distinct science inputs create distinct durable paid calls; identical ones
    # reuse the response without rebilling. The raw request is byte-replay checked.
    return prefix+'_'+sha(canon(payload))[:23]


def feedback_controller(self, ident):
    j=self.j
    base=_external_context(j,'NATIVE_RESEARCH_TOOLS' if self._native_tool_contract else 'CUSTOM_BACKEND_CAPABILITIES_UNDECLARED')
    evidence=classified_evidence(j); claims=target_claims(base,j)
    prior_state=working_problem_state(j)
    source={'program':base['program'], 'target_claims':claims, 'evidence':evidence,
            'prior_working_problem_state':prior_state,
            'original_success_criterion':base['program'].get('criteria'),
            'source_policy':'Model judgement only. Not proof or experimental certification.'}
    novelty_id=_call_id('NVT',source)
    novelty_obj=strict_envelope(self.model.call(novelty_id,'CONTROLLER',None,NOVELTY_PROMPT,source))
    # Invalid advisory models must not silently become declarations of novelty.
    if novelty_obj is None:
        j.append('OPERATIONAL_PAUSE',{'reason':'INVALID_NOVELTY_ADVISOR_JSON','call_id':novelty_id})
        return {'status':'INVALID_NOVELTY_ADVISOR_JSON'}
    novelty=validate_novelty(novelty_obj,{c['id'] for c in claims},evidence)
    science_delta=prior_art_delta(prior_state,novelty)
    impact_input={'program':base['program'],'current_problems':base['problems'],
           'novelty':novelty,'evidence':evidence, 'original_p0_unchanged':True,
           'prior_working_problem_state':prior_state, 'prior_art_delta':science_delta}
    impact_id=_call_id('PMI',impact_input)
    impact_obj=strict_envelope(self.model.call(impact_id,'CONTROLLER',None,IMPACT_PROMPT,impact_input))
    if impact_obj is None:
        j.append('OPERATIONAL_PAUSE',{'reason':'INVALID_PROBLEM_IMPACT_JSON','call_id':impact_id})
        return {'status':'INVALID_PROBLEM_IMPACT_JSON'}
    try:impact=validate_impact(impact_obj,{c['id'] for c in claims},novelty,evidence,prior_working_problem_state=prior_state)
    except EvidenceError as exc:
        j.append('OPERATIONAL_PAUSE',{'reason':'REJECTED_PROBLEM_IMPACT:'+str(exc),'call_id':impact_id})
        return {'status':'REJECTED_PROBLEM_IMPACT','detail':str(exc)}
    p0_delta=problem_impact_delta(prior_state,impact,science_delta)
    augmented={**base,'claim_prior_art_assessment':novelty,'problem_level_impact':impact,
       'working_problem_state_before_decision':prior_state,'prior_art_delta':science_delta,
       'problem_impact_delta':p0_delta,
       'feedback_call_provenance':{'novelty_model_call':novelty_id,'problem_impact_model_call':impact_id,
                 'not_source_verified':True,'source_materials':list(x['evidence_id'] for x in evidence)}}
    raw_opp=self.model.call('OPP_'+ident,'CONTROLLER',None,OPPORTUNITY_PROMPT,augmented)
    obj_opp=strict_envelope(raw_opp)
    opp=validate_opp(obj_opp,augmented)
    full={**augmented,'independent_opportunity_assessment':opp,
        'opportunity_assessment_origin':{'call_id':'OPP_'+ident,'status':'MODEL_ADVISORY_NOT_PRIMARY_EVIDENCE'}}
    prompt=CONTROLLER_PROMPT+(E3R1_CONTROLLER_ADDENDUM if j.verify().e3r1_policy else '')+'\n'+CONTROLLER_FEEDBACK_ADDENDUM
    raw=self.model.call('CTRL_'+ident,'CONTROLLER',None,prompt,full)
    control=strict_envelope(raw)
    if control is None:
        j.append('OPERATIONAL_PAUSE',{'reason':'CONTROLLER_INVALID_JSON','call_id':'CTRL_'+ident})
        return {'status':'CONTROLLER_INVALID_JSON'}
    try:planned=controller_plan(j,control,'CTRL_'+ident,ident)
    except (EvidenceError,KeyError,TypeError,ValueError) as exc:
        j.append('OPERATIONAL_PAUSE',{'reason':'CONTROLLER_PLAN_REJECTED:'+str(exc)[:95],'call_id':'CTRL_'+ident})
        return {'status':'CONTROLLER_PLAN_REJECTED','detail':str(exc)}
    j.append('CONTROLLER_DECISION',{'id':ident,'call_id':'CTRL_'+ident,
           'parsed_blob':j.blob(control),'rationale':control['rationale']})
    for kind,p in planned:j.append(kind,p)
    ass=control.get('objective_assessment') if j.verify().r5_policy else None
    return {'status':'CONTROLLER_COMMITTED','actions':len(control['actions']),
            'scientific_disposition':control['disposition'],
            'objective_status':ass.get('objective_status') if ass else None,
            'research_status':ass.get('research_status') if ass else None,
            'novelty_call_id':novelty_id,'problem_impact_call_id':impact_id,
            'opportunity_assessor_call_id':'OPP_'+ident}


def feedback_worker_input(j, wid, tool_capabilities=None):
    # Original pinned input and FRESH isolation contract remain unchanged.
    payload=_ORIGINAL_WORKER_INPUT(j,wid,tool_capabilities)
    if j.verify().work[wid]['mode']=='INFORMED':
        payload['working_problem_state']=working_problem_state(j)
        payload['scientific_literature_feedback']={
            'source_materials':classified_evidence(j),
            'status':'ORIGINAL_SOURCES_AND_EXECUTION_OUTPUTS_NOT_AUTOMATICALLY_CERTIFIED',
            'instruction':'Compare the original P0 and specific claim-level scientific deltas; do not present inherited AI claims as inspected primary evidence.'}
    return payload

_ORIGINAL_WORKER_INPUT=e2_engine._worker_input
_ORIGINAL_SHOULD_CONTROLLER_RUN=Engine._should_controller_run


def feedback_should_controller_run(self):
    if _ORIGINAL_SHOULD_CONTROLLER_RUN(self):return True
    # New actual literature evidence may arrive after the previous Controller
    # decision, while no workers remain. Let the Controller decide whether it
    # matters, without automatically generating or concluding any science.
    rows=self.j._events()
    last=max((i for i,r in enumerate(rows) if r['kind']=='CONTROLLER_DECISION'),default=-1)
    return any(r['kind']=='SOURCE_REGISTERED' and
               str(r['payload'].get('id','')).startswith('SRC_PRIOR_') for r in rows[last+1:])


def run_feedback(root,args):
    previous=Engine.controller
    worker_before=e2_engine._worker_input
    should_before=Engine._should_controller_run
    try:
        Engine.controller=feedback_controller
        Engine._should_controller_run=feedback_should_controller_run
        e2_engine._worker_input=feedback_worker_input
        return base_drive(root,budget=args.call_budget,chunk=args.checkpoint_iterations,
            max_tokens=args.max_tokens,model=args.model,cpu=args.science_cpu_seconds,
            wall=args.science_wall_seconds,paid=True,parallel=args.max_parallel)
    finally:
        Engine.controller=previous
        Engine._should_controller_run=should_before
        e2_engine._worker_input=worker_before


def audit(root):
    j=EvolutionJournal(root);s=j.verify();records=[]
    for d in s.controller_decisions:
        ident=d['id'];ctrl=s.model_calls.get('CTRL_'+ident)
        if not ctrl:continue
        req=json.loads(j.raw(ctrl['request_blob']))
        prompt_data=json.loads(req['messages'][1]['content'])
        prior=prompt_data.get('claim_prior_art_assessment',{})
        impact=prompt_data.get('problem_level_impact',{})
        record=json.loads(j.raw(d['parsed_blob']))
        records.append({'decision_id':ident,'claim_assessments':prior.get('claim_assessments',[]),
            'rejected_prior_art_assessments':prior.get('rejected',[]),
            'problem_level_impact':impact.get('problem_impact'),
            'claim_to_problem':impact.get('claim_to_problem',[]),
            'rejected_impact_inferences':impact.get('rejected_impact_inferences',[]),
            'registered_unreviewed_citations':impact.get('registered_unreviewed_citations',[]),
            'model_proposed_impact_state':impact.get('model_proposed_impact_state'),
            'prior_art_delta':prompt_data.get('prior_art_delta',{}),
            'problem_impact_delta':prompt_data.get('problem_impact_delta',{}),
            'problem_state_before_decision':prompt_data.get('working_problem_state_before_decision',{}).get('latest_working_p0',{}),
            'controller_disposition':record.get('disposition'),
            'controller_actions':[{'operation':x['operation'],'asset_ids':x['asset_ids'],
                   'work_id':x['work']['id'],'question':x['work']['question']} for x in record.get('actions',[])],
            'recorded_raw_model_calls':prompt_data.get('feedback_call_provenance',{})})
    return {'status':'READ_ONLY_PROBLEM_SCIENCE_EVOLUTION_AUDIT','root':str(j.root),
        'original_problem':s.program['problem'],'original_problem_modified':False,
        'working_problem_state':working_problem_state(j),
        'records':records,'last_objective_assessment':s.objective_assessments[-1] if s.objective_assessments else None,
        'science_certification':False,'novelty_certification':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('prepare');a.add_argument('--source-root',required=True);a.add_argument('--out-root',required=True)
    a.add_argument('--asset-id',action='append',required=True);a.add_argument('--literature-json')
    b=sub.add_parser('drive');b.add_argument('--root',required=True);b.add_argument('--paid',action='store_true')
    b.add_argument('--model',default='openai/gpt-5.6-luna');b.add_argument('--call-budget',type=int,default=16)
    b.add_argument('--checkpoint-iterations',type=int,default=12)
    b.add_argument('--max-parallel',type=int,default=2)
    b.add_argument('--max-tokens',type=int,default=16000)
    b.add_argument('--science-cpu-seconds',type=int,default=120)
    b.add_argument('--science-wall-seconds',type=int,default=160)
    i=sub.add_parser('ingest-evidence');i.add_argument('--root',required=True);i.add_argument('--literature-json',required=True)
    c=sub.add_parser('audit');c.add_argument('--root',required=True);c.add_argument('--out')
    w=sub.add_parser('state');w.add_argument('--root',required=True);w.add_argument('--out')
    args=p.parse_args()
    if args.cmd=='prepare':result=prepare_delta_root(args.source_root,args.out_root,args.asset_id,args.literature_json)
    elif args.cmd=='drive':
        guard(args.paid,'REQUIRES_EXPLICIT_--paid');result=run_feedback(args.root,args)
    elif args.cmd=='ingest-evidence':result=ingest_external_evidence(args.root,args.literature_json)
    else:
        result=working_problem_state(EvolutionJournal(args.root)) if args.cmd=='state' else audit(args.root)
        if args.out:
            path=pathlib.Path(args.out).expanduser().resolve()
            guard(not path.exists(),'NO_OVERWRITE_AUDIT')
            path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
