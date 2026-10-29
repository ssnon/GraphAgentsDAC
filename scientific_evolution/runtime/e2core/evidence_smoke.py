"""Live network smoke test: FREE open research API calls, no LLM calls."""
from __future__ import annotations
import argparse,json,pathlib
from .research_literature import research_literature

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--query',default='surface enhanced Raman spectroscopy intermittency')
    ap.add_argument('--pmcid',default='PMC4383902')
    ap.add_argument('--out')
    args=ap.parse_args()
    checks=[research_literature({'action':'search','provider':'openalex','query':args.query,'limit':3}),
            research_literature({'action':'search','provider':'europepmc','query':args.query,'limit':3}),
            research_literature({'action':'read_fulltext','pmcid':args.pmcid,'offset':0,'limit':2})]
    evidence={'smoke_test':'LIVE_PROVIDER_API_NO_LLM_CALLS','all_delivered':all(x['status']=='DELIVERED' for x in checks),
      'checks':[{'action':x.get('action'),'status':x.get('status'),'provider':x.get('provider'),
        'source_url':x.get('source_url') or x.get('requested_url'),
        'error_code':x.get('error_code'),'exception_type':x.get('exception_type'),'source_sha256':x.get('source_sha256'),
        'records':len(x.get('records',[])),'paragraphs':len(x.get('paragraphs',[])),
        'requested_provider':x.get('requested_provider'),
        'fallback_provider':x.get('fallback_provider'),
        'fallback_reason':x.get('fallback_reason'),
        'retrieval_attempts':x.get('retrieval_attempts',[]),
        'evidence_class':x.get('evidence_class'),
        'evidence_unavailable_not_scientific_negative':x.get('availability_not_evidence_of_scientific_absence',False)} for x in checks],
      'no_paid_model_calls':True,'science_certification':False}
    if args.out:pathlib.Path(args.out).write_text(json.dumps(evidence,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(evidence,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
