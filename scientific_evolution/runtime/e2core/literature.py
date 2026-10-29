"""Grounded live bibliographic discovery, NOT full-text or primary-data proof.

This tool deliberately uses a single, pre-approved metadata provider endpoint.
Retrieved metadata are marked third-party, source URLs and DOI are retained,
and content is never interpreted as instructions by the runtime.
"""
from __future__ import annotations
import datetime,json,re,urllib.parse,urllib.request,urllib.error

BASE='https://api.crossref.org/works'
DOI=re.compile(r'^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$',re.I)

def crossref_lookup(args,*,transport=None):
    if not isinstance(args,dict):return {'status':'REJECTED','error_code':'INVALID_LOOKUP_ARGUMENTS'}
    query=args.get('query');doi=args.get('doi')
    if (bool(query)+bool(doi))!=1:return {'status':'REJECTED','error_code':'SUPPLY_QUERY_OR_DOI'}
    if doi:
        if not isinstance(doi,str) or len(doi)>200 or not DOI.fullmatch(doi):return {'status':'REJECTED','error_code':'INVALID_DOI'}
        url=BASE+'/'+urllib.parse.quote(doi,safe='/')
    else:
        if not isinstance(query,str) or not 3<=len(query.strip())<=300:return {'status':'REJECTED','error_code':'INVALID_QUERY'}
        url=BASE+'?'+urllib.parse.urlencode({'query.bibliographic':query.strip(),'rows':5})
    fetch=transport or _fetch
    try:
        raw=fetch(url)
        if not isinstance(raw,dict) or not isinstance(raw.get('message'),(dict,list)):
            raise ValueError('INVALID_PROVIDER_SCHEMA')
        m=raw['message'];rows=m if isinstance(m,list) else (m.get('items',[]) if 'items' in m else [m]);rows=rows[:5]
        citations=[]
        for x in rows:
            if not isinstance(x,dict):continue
            did=x.get('DOI','');titles=x.get('title',[])
            if not isinstance(titles,list):titles=[titles]
            citations.append({'doi':did,'title':(titles[0] if titles else '')[:450],
             'year':(((x.get('published',{}) or {}).get('date-parts') or [[None]])[0] or [None])[0],
             'publisher':x.get('publisher',''), 'type':x.get('type',''),
             'landing_page':x.get('URL',''), 'source_metadata':'CROSSREF_BIBLIOGRAPHIC_METADATA',
             'primary_experimental_observations_verified':False})
        return {'status':'DELIVERED','provider':'Crossref REST works metadata','requested_url':url,
            'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'records':citations,'scientific_certification':False,
            'warning':'Bibliographic metadata are NOT the full primary article, nor verification of its experimental findings. Verify primary contents separately.'}
    except (OSError,TimeoutError,ValueError,KeyError,TypeError,urllib.error.URLError) as exc:
        return {'status':'REJECTED','error_code':'LITERATURE_METADATA_UNAVAILABLE', 'exception_type':type(exc).__name__,
                'requested_url':url,'scientific_certification':False}

def _fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'E2-AIScientist-R5/1.0 (metadata provenance research)','Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=15) as response:
        if response.status!=200:raise OSError('PROVIDER_STATUS')
        # Cap response size even if provider sends an unexpected bulk payload.
        blob=response.read(512_001)
        if len(blob)>512_000:raise ValueError('TOO_LARGE_METADATA_RESPONSE')
        return json.loads(blob.decode('utf-8'))
