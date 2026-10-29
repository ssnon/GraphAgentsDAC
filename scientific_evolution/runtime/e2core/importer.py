"""Immutable P6L review import: all 115 records searchable, selected provisional seeds.

Never infer new scientific findings from text classification. Labels are editorial
indexes and every indexed claim points to an original committed science hash.
"""
from __future__ import annotations
import json, pathlib, re
from .core import EvolutionJournal, EvidenceError, canon, sha, guard

SEED_SPEC={
 'A_SHARED_LAG':('I001:0028','CALCULATION','Conditional Raman/plasmon lag covariance result'),
 'A_RESONANCE':('I002:0004','NULL_MODEL','Resonance wandering competing explanation'),
 'A_OCCUPANCY':('I002:0007','HYPOTHESIS','Competitive occupancy and negative covariance discriminator (externally challenged; no verdict imported)'),
 'A_PHOTOCHARGE':('I002:0013','HYPOTHESIS','Photocharge/trap gating with unconstrained parameters'),
 'A_ORIENTATION':('I002:0021','HYPOTHESIS','Orientation-dependent Raman tensor mechanism'),
 'A_THERMO':('I002:0026','HYPOTHESIS','Nonlinear thermo-optic proposal, associated tool did not validate claim'),
 'A_DUTY_NULL':('C001:0002','NULL_MODEL','Independent emitter duty-cycle null and thermal diffusion limitation'),
 'A_PORTFOLIO_HOLD':('S001:0003','FAILURE','Historical Synthesis-scoped scientific HOLD (not universal impossibility)'),
}

def validated_review(path):
    data=pathlib.Path(path).read_bytes(); obj=json.loads(data)
    guard(obj.get('committed_steps')==115 and obj.get('journal_status')=='P5_HASHED_REPLAY_PASS', 'P6L_REVIEW_EXPECTED_115')
    rows=obj.get('records');guard(isinstance(rows,list) and len(rows)==115,'P6L_ROWS_115_REQUIRED')
    refs=set()
    for r in rows:
        ref=r.get('ref')
        guard(isinstance(ref,str) and re.fullmatch(r'[A-Z]\d{3}:\d{4}',ref) and ref not in refs,'P6L_REF_INVALID_OR_DUPLICATE')
        refs.add(ref)
        guard(sha(canon(r['science']))==r['science_sha256'],'P6L_SCIENCE_DIGEST_MISMATCH:'+ref)
        guard(sha(canon(r['tool_result']))==r['tool_sha256'],'P6L_TOOL_DIGEST_MISMATCH:'+ref)
    guard(obj.get('program_hold',{}).get('reason')=='SYNTHESIS_EXPLICIT_PORTFOLIO_HOLD','P6L_SCIENTIFIC_HOLD_EXPECTED')
    return obj,sha(data)

def make_catalog(review_path):
    obj,source_hash=validated_review(review_path)
    def firstline(value,n=260):return ' '.join(str(value or '').split())[:n]
    rows=[]
    for r in obj['records']:
        s=r['science']; rows.append({'ref':r['ref'],'role':r['role'],'wave':r['wave'],
            'science_sha256':r['science_sha256'],'tool_sha256':r['tool_sha256'],
            'next_action':s.get('next_action'),'scientific_delta_excerpt':firstline(s.get('scientific_delta')),
            'scientific_work_excerpt':firstline(s.get('scientific_work')),
            'next_question_excerpt':firstline(s.get('next_research_question')),
            'tool_status':r['tool_result'].get('status','WRAPPED_NATIVE_RESULT') if isinstance(r['tool_result'],dict) else 'UNPARSED',
            'scope':'HISTORICAL_AI_RESEARCH_NOT_SCIENTIFICALLY_CERTIFIED'})
    return {'kind':'P6L_ALL_115_COMMITTED_SCIENTIFIC_STEPS','source_review_sha256':source_hash,
        'record_count':115,'source_export_journal_status':obj['journal_status'],
        'historical_hold':obj['program_hold'],'records':rows,
        'external_audit_included':False,'scientific_certification':False}

def seed_e2(j:EvolutionJournal,review_path,selected=None):
    """Register historical seeds as PROVISIONAL source indexed claims, not model work."""
    obj,source_hash=validated_review(review_path); by_ref={r['ref']:r for r in obj['records']}
    selected=list(SEED_SPEC) if selected is None else selected
    guard(all(x in SEED_SPEC for x in selected),'UNKNOWN_SEED_SELECTION')
    s=j.verify()
    guard(len(s.assets)==0 and len(s.sources)==0 and len(s.work)==0,'EMPTY_NEW_E2_ROOT_REQUIRED')
    for name in selected:
        ref,kind,label=SEED_SPEC[name];rec=by_ref[ref]; sid='SRC_'+name
        digest=j.add_source(sid,'HISTORICAL_AI',rec,'P6L committed '+ref+'; science:'+rec['science_sha256']+'; source review:'+source_hash)
        text=rec['science'].get('scientific_delta') or rec['science'].get('scientific_work') or label
        j.append('HISTORICAL_ASSET_INDEXED',{'id':name,'kind':kind,'problem_id':'P0','claim':label+' — '+ ' '.join(text.split())[:500],
          'assumptions':'Historical model narrative; assumptions not independently audited at import',
          'scope':'P6L '+ref+'; provisional extraction ONLY; no experimental or prior-art certification',
          'source_ids':[sid],'source_ref':ref,'source_science_sha256':rec['science_sha256'],
          'source_tool_sha256':rec['tool_sha256'],'catalog_sha256':source_hash,
          'limitations':['Index extracted by operator tooling; not a live LLM conclusion','Historical science HOLD must remain unchanged']})
    return {'status':'PROVISIONAL_SEEDS_REGISTERED','count':len(selected),'source_review_sha256':source_hash,'selected':selected}
