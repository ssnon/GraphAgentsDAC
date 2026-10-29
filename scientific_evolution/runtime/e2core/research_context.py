"""Read-only factual research-tool affordances and actual evidence-attempt accounting.

R6R2 is deliberately NOT a scientific policy engine.  It does not require a
literature call, award points for search, choose papers or overrule Controller
scientific decisions. It supplies missing operational facts to the model.

Fresh Workers receive only their own attempts and public PRIMARY inventory;
never leak INFORMED/older-model artifacts across the isolation boundary.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from .core import EvolutionJournal

NATIVE_TOOLS = [
    {'kind':'literature_research','purpose':'Autonomously discover scholarly records and read accessible original evidence',
     'actions':['search (openalex/europepmc)','resolve (DOI/openalex ID)','abstract (DOI)','read_fulltext (DOI/PMCID)',
                'find_evidence (PMCID and phrase)','references','figure_captions',
                'supplements','supplement_files','data_links','zenodo','read_zenodo_file','read_arxiv_pdf'],
     'evidence_caveat':'Search hits/links are metadata, not experimental evidence. Read the text before making literature-grounded scientific claims.'},
    {'kind':'literature_lookup','purpose':'Crossref bibliographic metadata by topic/DOI (NOT full text)'},
    {'kind':'source_lookup','purpose':'Read explicitly permitted locally registered primary records or your own TOOL_RESULT source IDs'},
    {'kind':'primary_catalog','purpose':'List available operator-verified PRIMARY registrations'},
    {'kind':'python_science','purpose':'Request sandboxed scientific code execution; inspect the recorded tool result'},
    {'kind':'verified_calculation','purpose':'Request bounded numeric calculations on explicitly provided scenarios'},
]


def _attempts(j, allowed_work=None):
    """Only recorded tool results count; requests in unexecuted LLM text do not."""
    state=j.verify()
    attempts=[]
    for tid,row in state.tool_results.items():
        if allowed_work is not None and row['work_id']!=allowed_work:
            continue
        req=json.loads(j.raw(row['request_blob']))
        result=json.loads(j.raw(row['result_blob']))
        kind=req.get('kind','UNKNOWN') if isinstance(req,dict) else 'UNKNOWN'
        action=(req.get('arguments') or {}).get('action') if isinstance(req,dict) and isinstance(req.get('arguments',{}),dict) else None
        if not isinstance(result,dict):result={'status':'UNRECOGNIZED_RESULT'}
        attempts.append({
          'tool_id':tid,'work_id':row['work_id'],'tool_kind':kind,
          'action':action,'result_status':result.get('status'),
          'evidence_class':result.get('evidence_class'),
          'provider':result.get('provider'),
          'error_code':result.get('error_code'),
          'fallback_reason':result.get('fallback_reason'),
          'linked_source_id':result.get('linked_source_id'),
          'source_url':result.get('source_url') or result.get('requested_url'),
        })
    return attempts


def _evidence_inventory(state, allowed_work=None, only_primary=False):
    summary=Counter(); available=[]
    for sid,record in state.sources.items():
        kind=record.get('kind')
        if only_primary and kind!='PRIMARY':continue
        if allowed_work is not None and kind!='PRIMARY' and not (
                kind=='TOOL_RESULT' and record.get('work_id')==allowed_work):continue
        if kind not in {'PRIMARY','TOOL_RESULT'}:continue
        summary[kind]+=1
        available.append({'source_id':sid,'kind':kind,
           'description':(record.get('description') or '')[:200]})
    return dict(summary),available


def _capabilities(contract):
    if contract=='NATIVE_RESEARCH_TOOLS':
        return {'backend':'NATIVE_ENGINE_BACKEND','available_tools':NATIVE_TOOLS,
          'limitations':['The provider may be unavailable; no successful live request is implied by the tool inventory.',
            'Crossref/OpenAlex search metadata and abstract are not original experimental observations.',
            'OA fulltext access is contingent on hosting/rights/provider availability. Some PDFs, images, tables and SI are not fully readable.',
            'Registered tool outputs do not independently certify the scientific correctness of model claims.']}
    return {'backend':'CUSTOM_BACKEND_CAPABILITIES_UNDECLARED',
       'available_tools':[],
       'limitations':['A custom backend is configured; runtime cannot attest which tool kinds are implemented. The Worker prompt lists supported native request formats, but this backend may differ.']}


def research_capability_state(j,contract=None):
    """Portfolio-level facts the informed Controller is authorized to assess."""
    s=j.verify();attempts=_attempts(j)
    summaries, sources=_evidence_inventory(s)
    literature=[a for a in attempts if a['tool_kind'] in {'literature_research','literature_lookup'}]
    return {'capabilities':_capabilities(contract),
      'evidence_inventory':{'primary_count':summaries.get('PRIMARY',0),
        'retrieved_tool_source_count':summaries.get('TOOL_RESULT',0),
        'recent_registered_evidence':sources[-8:]},
      'attempt_inventory':{'total_recorded_tools':len(attempts),
        'recorded_literature_attempts':len(literature),
        'by_kind':dict(Counter(a['tool_kind'] for a in attempts)),
        'by_result_status':dict(Counter(str(a['result_status']) for a in attempts)),
        'by_evidence_class':dict(Counter(str(a['evidence_class']) for a in literature if a['evidence_class'])),
        'recent_literature_attempts':literature[-8:]},
      'interpretation':'ZERO literature attempts means NOT YET TRIED, NOT EVIDENCE UNAVAILABLE. '
           'Nonzero unsuccessful attempts may be access failures or invalid requests; inspect results. '
           'An accessible source may still be insufficient to solve the science. This does not prescribe a decision.',
      'scientific_action_discretion':'You decide whether obtaining literature/data or doing other scientific work offers enough information value. No forced search or research continuation.'}


def research_worker_context(j,work_id,contract=None):
    """Worker-private facts only. Never reveal other workers' histories to FRESH."""
    s=j.verify();w=s.work[work_id]
    attempts=_attempts(j,work_id)
    inventory, available=_evidence_inventory(s, work_id,
          only_primary=(w['mode']=='FRESH' and not s.r5_policy))
    return {'capabilities':_capabilities(contract),
      'worker_id':work_id,'worker_mode':w['mode'],
      'available_sources':available[-8:],
      'primary_count':inventory.get('PRIMARY',0),
      'own_tool_result_source_count':inventory.get('TOOL_RESULT',0),
      'own_recorded_tool_attempts':len(attempts),
      'own_recent_tool_attempts':attempts[-6:],
      'guidance':'If source evidence is critical and may be accessible, consider asking a tool, reading its actual return, and linking exact source IDs to scientific claims. '
       'If sources are not relevant, proceed theoretically or RETURN; no tool-use quota exists. An unattempted search cannot be called a failed search.'}


def main(argv=None):
    p=argparse.ArgumentParser(description='Read-only operational evidence access audit')
    p.add_argument('--root',required=True)
    p.add_argument('--out')
    args=p.parse_args(argv)
    j=EvolutionJournal(args.root)
    data=research_capability_state(j,'NATIVE_RESEARCH_TOOLS')
    data['root']=str(j.root)
    data['journal_events']=len(j._events())
    data['read_only']=True
    s=j.verify();data['latest_objective_assessment']=s.objective_assessments[-1] if s.objective_assessments else None
    if args.out:
        from pathlib import Path
        Path(args.out).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False,indent=2))
    return data

if __name__=='__main__':main()
