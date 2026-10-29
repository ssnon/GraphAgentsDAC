"""Read-only evidence provenance / paper-vs-link reporting from verified E2 journal."""
import argparse,collections,datetime,json,pathlib
from .core import EvolutionJournal

def evidence_report(root):
    j=EvolutionJournal(root);s=j.verify()
    sources=[]
    citations=collections.defaultdict(list)
    for asset in s.assets.values():
        for sid in asset.get('source_ids',[]):citations[sid].append(asset['id'])
    for sid,v in s.sources.items():
        r={'source_id':sid,'kind':v['kind'],'work_id':v.get('work_id'),
           'linked_asset_ids':citations.get(sid,[]),'scientific_certification':False}
        record=json.loads(j.raw(v['blob']))
        if v['kind']=='TOOL_RESULT':
            result=record.get('result') or {}
            r.update({'tool_id':record.get('tool_id'), 'evidence_class':record.get('evidence_class') or result.get('evidence_class'),
                'actual_tool_status':result.get('status'),
                'source_url':result.get('source_url') or result.get('requested_url'),
                'source_sha256':result.get('source_sha256'),
                'pmcid':result.get('pmcid'),
                'provider':result.get('provider'),
                'requested_provider':result.get('requested_provider'),
                'automatic_fallback':result.get('automatic_fallback',False),
                'fallback_reason':result.get('fallback_reason'),
                'retrieval_attempts':result.get('retrieval_attempts',[]),
                'document_or_data_contents_retrieved':(result.get('evidence_class') in {
                    'OA_FULLTEXT_TEXT','OA_FULLTEXT_CAPTION','OA_SUPPLEMENT_TEXT','OA_PDF_TEXT','DATA_FILE_TEXT'}),
                'metadata_or_link_only':(result.get('evidence_class') in {
                    'BIBLIOGRAPHIC_METADATA','ABSTRACT_TEXT','SUPPLEMENT_LINK_METADATA','DATA_LINK_METADATA'})})
        elif v['kind']=='HISTORICAL_AI':
            r.update({'evidence_class':'HISTORICAL_AI_CLAIM_NOT_VERIFIED',
             'origin_root':record.get('origin_root'),'origin_work_id':record.get('origin_work_id'),
             'scientific_certification':False})
        else:r['evidence_class']=v['kind']
        sources.append(r)
    outages=[]
    for tid,rec in s.tool_results.items():
        raw=json.loads(j.raw(rec['result_blob']))
        if raw.get('status')=='EVIDENCE_UNAVAILABLE' or raw.get('automatic_fallback'):
            outages.append({'tool_id':tid,'work_id':rec['work_id'],
                'status':raw.get('status'),'action':raw.get('action'),
                'requested_provider':raw.get('requested_provider'),
                'actual_provider':raw.get('provider'),
                'fallback_reason':raw.get('fallback_reason'),
                'error_code':raw.get('error_code'),
                'retrieval_attempts':raw.get('retrieval_attempts',[]),
                'is_scientific_negative':False})
    counts=collections.Counter(x.get('evidence_class','UNKNOWN') for x in sources)
    return {'status':'READ_ONLY_VERIFIED_E2_EVIDENCE_INVENTORY',
      'root':str(j.root),'journal_events':len(j._events()),'total_source_records':len(sources),
      'source_classes':dict(counts),'source_records':sources,
      'literature_provider_incidents':outages,
      'assets_with_source_ids':sum(bool(x.get('source_ids')) for x in s.assets.values()),
      'assets_without_source_ids':sum(not bool(x.get('source_ids')) for x in s.assets.values()),
      'science_certification':False,
      'warning':'Even complete original article reading does not independently validate a paper’s conclusions; citations are model-authored.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);args=p.parse_args()
    d=evidence_report(args.root)
    pathlib.Path(args.out).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':d['status'],'source_classes':d['source_classes'],
      'total_source_records':d['total_source_records'],'out':args.out,'scientific_certification':False},ensure_ascii=False))
if __name__=='__main__':main()
