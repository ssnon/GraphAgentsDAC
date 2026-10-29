"""E1 core. Append-only scientific lineage journal; no LLM, network or experiment.

Designed to preserve distinctions: scientific claims vs evidence; human audits vs AI
work; scientific decisions vs operations; fresh input vs informed input. Tests are
structural and do not certify novelty or physical plausibility.
"""
from __future__ import annotations
import hashlib, json, os, pathlib, re, tempfile, threading
from dataclasses import dataclass, field
from typing import Any

PROTOCOL='E2_AUTONOMOUS_EVOLUTION_V1'
IDENT=re.compile(r'^[A-Za-z][A-Za-z0-9_\-]{0,100}$')
HASH=re.compile(r'^[a-f0-9]{64}$')
OPERATIONS={'FRESH','DEVELOP','CHALLENGE','MUTATE','FUSE','DECOMPOSE','REFRAME','VERIFY'}
KINDS={'HYPOTHESIS','COUNTEREXAMPLE','NULL_MODEL','CALCULATION','LITERATURE_CLAIM','PREDICTION','FAILURE','SUBPROBLEM','SCOPED_NEGATIVE'}
REVIEW_DECISIONS={'PROPOSED','CONDITIONAL','CHALLENGED','RESTRICTED','REJECTED_IN_SCOPE','READY_FOR_HUMAN_REVIEW','PARKED','RETAINED','RETAINED_WITH_LIMITS'}
# A free-form MODEL review label is not a scientific certificate. Preserve the
# exact authored label, but use a neutral state for unfamiliar vocabulary.
REVIEW_LABEL=re.compile(r'^[A-Z][A-Z0-9_]{1,63}$')
WORK_OUTCOMES={'RETURN','HOLD','BLOCKED','CONTINUE_IN_CHILD'}
SOURCE_TYPES={'PRIMARY','HISTORICAL_AI','TOOL_RESULT','EXTERNAL_AUDIT','OPERATOR'}

class EvidenceError(ValueError):pass

def guard(cond,reason):
    if not cond: raise EvidenceError(reason)

def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def proper_id(x):return isinstance(x,str) and IDENT.fullmatch(x) is not None

def atomic(path,data):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'xb') as f:
        f.write(data);f.flush();os.fsync(f.fileno())

@dataclass
class State:
    program:dict|None=None
    sources:dict=field(default_factory=dict)
    problems:dict=field(default_factory=dict)
    assets:dict=field(default_factory=dict)
    reviews:dict=field(default_factory=dict)
    work:dict=field(default_factory=dict)
    evolution:list=field(default_factory=list)
    program_reviews:list=field(default_factory=list)
    operational_pauses:list=field(default_factory=list)
    model_calls:dict=field(default_factory=dict)
    tool_results:dict=field(default_factory=dict)
    controller_decisions:list=field(default_factory=list)
    r5_policy:bool=False
    e3r1_policy:bool=False
    objective_assessments:list=field(default_factory=list)
    integration_requests:list=field(default_factory=list)
    runtime_contract_version:str|None=None
    def apply(self,kind,p):
        guard(isinstance(p,dict),'PAYLOAD_OBJECT_REQUIRED')
        if kind=='PROGRAM_CREATED':
            guard(not self.program and isinstance(p.get('problem'),str) and p['problem'].strip(),'DUPLICATE_OR_EMPTY_PROGRAM')
            self.program=p
            self.problems['P0']={'id':'P0','question':p['problem'],'parents':[],'status':'OPEN','rationale':'Original problem'}
        elif kind=='R5_POLICY_ACTIVATED':
            guard(self.program and not self.r5_policy and p.get('policy')=='OBJECTIVE_AND_DISPOSITION_V1','INVALID_R5_ACTIVATION')
            self.r5_policy=True
        elif kind=='E3R1_POLICY_ACTIVATED':
            guard(self.program and not self.e3r1_policy and p.get('policy')=='PORTFOLIO_DECISIONS_V1', 'INVALID_E3R1_ACTIVATION')
            self.e3r1_policy=True
        elif kind=='RUNTIME_CONTRACT_UPGRADED':
            guard(self.e3r1_policy and self.runtime_contract_version is None
                  and p.get('version')=='E3R1R2_FRONTIER_CONTINUATION_V1'
                  and isinstance(p.get('reason'),str) and p['reason'].strip(),
                  'INVALID_OR_DUPLICATE_RUNTIME_CONTRACT_UPGRADE')
            guard(all(c['state']=='SAVED' for c in self.model_calls.values()),
                  'UNRESOLVED_MODEL_CALL_BEFORE_UPGRADE')
            self.runtime_contract_version=p['version']
        elif kind=='R5_INTEGRATION_REQUESTED':
            guard(self.r5_policy and isinstance(p.get('foreign_root'),str) and isinstance(p.get('asset_ids'),list) and all(x in self.assets for x in p['asset_ids']), 'INVALID_INTEGRATION_REQUEST')
            self.integration_requests.append(p)
        elif kind=='PROGRAM_OBJECTIVE_ASSESSED':
            guard(self.r5_policy and proper_id(p.get('reviewer_id')) and p.get('objective_status') in {'UNRESOLVED','REVIEW_WORTHY_CANDIDATE','SOLVED','PROVEN_NEGATIVE_IN_SCOPE'},'INVALID_OBJECTIVE_STATUS')
            guard(p.get('research_status') in {'CONTINUING','PAUSED_EVIDENCE','PAUSED_LOW_INFORMATION','COMPLETED'},'INVALID_RESEARCH_STATUS')
            guard(isinstance(p.get('resolved_scope'),str) and isinstance(p.get('remaining_questions'),list) and isinstance(p.get('untried_approaches_considered'),list) and isinstance(p.get('reason'),str) and p['reason'].strip(),'INVALID_OBJECTIVE_ASSESSMENT')
            guard(p.get('objective_coverage') in {'ORIGINAL_PROBLEM','SUBPROBLEM_ONLY','NO_OBJECTIVE_RESULT'} and isinstance(p.get('supporting_asset_ids'),list) and all(a in self.assets for a in p['supporting_asset_ids']),'INVALID_OBJECTIVE_COVERAGE_OR_SUPPORT')
            if p['research_status']=='COMPLETED':
                guard(p['objective_status']!='UNRESOLVED' and p['objective_coverage']=='ORIGINAL_PROBLEM' and bool(p['supporting_asset_ids']),'COMPLETED_WITHOUT_P0_LEVEL_EVIDENCE')
            self.objective_assessments.append(p)
        elif kind=='SOURCE_REGISTERED':
            i=p.get('id')
            guard(proper_id(i) and i not in self.sources and p.get('kind') in SOURCE_TYPES and HASH.fullmatch(p.get('blob','')),'BAD_SOURCE')
            self.sources[i]=p
        elif kind=='PROBLEM_CREATED':
            i=p.get('id');parents=p.get('parents');reason=p.get('decomposition_rationale')
            guard(proper_id(i) and i not in self.problems and isinstance(parents,list) and len(parents)>0 and all(x in self.problems for x in parents),'INVALID_PROBLEM_PARENTS')
            guard(bool(reason and str(reason).strip()) and p.get('contribution_to_parent') and p.get('scope') and p.get('question'),'DECOMPOSITION_EXPLANATION_REQUIRED')
            self.problems[i]={**p,'status':'OPEN'}
        elif kind=='EVOLUTION_APPLIED':
            i=p.get('id');op=p.get('operation');w=p.get('work');parents=p.get('asset_ids')
            guard(proper_id(i) and i not in [v['id'] for v in self.evolution] and op in OPERATIONS,'BAD_EVOLUTION_ID_OR_OPERATOR')
            guard(isinstance(parents,list) and len(parents)==len(set(parents)) and all(x in self.assets for x in parents),'BAD_INPUT_ASSETS')
            # Schema-level parent counts are distinct from science policy:
            # never synthesize missing parent assets or change the operation.
            # Specific machine feedback helps the Controller repair its own
            # proposal without hiding a model-authored mistake.
            arity_ok=(op=='FUSE' and len(parents)>=2 or
                      op=='FRESH' and len(parents)==0 or
                      op in {'DEVELOP','CHALLENGE','MUTATE','VERIFY'} and len(parents)>=1 or
                      op in {'DECOMPOSE','REFRAME'})
            required=('AT_LEAST_2' if op=='FUSE' else
                      'EXACTLY_0' if op=='FRESH' else
                      'AT_LEAST_1' if op in {'DEVELOP','CHALLENGE','MUTATE','VERIFY'} else
                      'ANY')
            guard(arity_ok,f'OPERATOR_PARENT_ARITY:{op}:GOT_{len(parents)}:REQUIRED_{required}')
            guard(bool(p.get('reason') and str(p['reason']).strip()) and isinstance(w,dict),'EVOLUTION_REASON_AND_WORK_REQUIRED')
            wid=w.get('id');mode=w.get('mode');pi=w.get('problem_id')
            guard(proper_id(wid) and wid not in self.work and pi in self.problems and mode in {'FRESH','INFORMED'},'BAD_WORK')
            guard(op!='FRESH' or mode=='FRESH','FRESH_OPERATOR_MODE')
            guard(mode!='FRESH' or (op=='FRESH' and not parents),'FRESH_MUST_BE_UNINFORMED')
            guard(mode!='INFORMED' or op!='FRESH','INFORMED_NOT_FRESH')
            guard(all(x in self.sources for x in w.get('source_ids',[])),'UNKNOWN_WORK_SOURCES')
            guard(all(self.sources[x]['kind']=='PRIMARY' for x in w.get('source_ids',[]) if mode=='FRESH'),'FRESH_SOURCE_CONTAMINATION')
            guard(bool(w.get('question')) and bool(w.get('research_rationale')),'WORK_QUESTION_AND_RATIONALE_REQUIRED')
            self.evolution.append({**p,'work_id':wid})
            self.work[wid]={**w,'operation':op,'asset_input_ids':parents,'evolution_id':i,'status':'QUEUED','steps':[], 'published':[], 'processed_steps':[]}
        elif kind=='WORK_PORTFOLIO_ASSESSED':
            w=self.work.get(p.get('id'))
            action=p.get('action')
            assessment=p.get('assessment')
            guard(self.e3r1_policy and w and action in {'KEEP','CANCEL','DEFER','REACTIVATE'}
                  and assessment in {'VALUABLE','REDUNDANT','SUPERSEDED','WAIT_NEW_EVIDENCE','LOW_INFORMATION','OTHER'}
                  and proper_id(p.get('reviewer_id')) and isinstance(p.get('rationale'),str) and p['rationale'].strip(),
                  'BAD_PORTFOLIO_WORK_ASSESSMENT')
            guard(isinstance(p.get('evidence_asset_ids'),list) and all(a in self.assets for a in p['evidence_asset_ids']),
                  'PORTFOLIO_EVIDENCE_ASSETS_INVALID')
            if action in {'KEEP','CANCEL','DEFER'}:
                guard(w['status'] in {'QUEUED','ACTIVE','DEFERRED'},'PORTFOLIO_WORK_NOT_OPEN')
            # A repeated scientific DEFER of an already deferred Work is a
            # provenance-bearing reaffirmation, not a second state transition.
            # A deferred research opportunity can also be cancelled explicitly
            # when new evidence supersedes it. Both decisions remain journaled.
            if action=='DEFER':
                guard(w['status'] in {'QUEUED','ACTIVE','DEFERRED'},'WORK_ALREADY_DISPOSITIONED')
            if action=='CANCEL':
                guard(w['status'] in {'QUEUED','ACTIVE','DEFERRED'},'WORK_ALREADY_DISPOSITIONED')
            if action=='REACTIVATE':guard(w['status']=='DEFERRED','REACTIVATE_REQUIRES_DEFERRED')
            w.setdefault('portfolio_history',[]).append(dict(p))
            if action=='CANCEL':
                w['status']='CANCELLED';w['portfolio_disposition']=p
            elif action=='DEFER':
                if w['status']!='DEFERRED':
                    w['pre_defer_status']=w['status']
                w['status']='DEFERRED';w['portfolio_disposition']=p
            elif action=='REACTIVATE':
                w['status']=w.get('pre_defer_status','QUEUED');w['portfolio_disposition']=p
            else:w['portfolio_disposition']=p
        elif kind=='WORK_STARTED':
            w=self.work.get(p.get('id'))
            guard(w and w['status']=='QUEUED' and HASH.fullmatch(p.get('input_blob','')),'WORK_NOT_QUEUED_OR_MISSING_INPUT_PIN')
            w['status']='ACTIVE';w['input_blob']=p['input_blob']
        elif kind=='WORK_STEP':
            w=self.work.get(p.get('id'))
            guard(w and w['status']=='ACTIVE' and HASH.fullmatch(p.get('raw_blob','')),'STEP_NOT_ACTIVE_OR_NOT_GROUNDED')
            guard(p.get('step')==len(w['steps'])+1 and bool(p.get('kind')),'STEP_ORDER')
            w['steps'].append(p)
        elif kind=='ASSET_PUBLISHED':
            i=p.get('id');w=self.work.get(p.get('work_id'));pa=p.get('parent_ids',[])
            guard(proper_id(i) and i not in self.assets and w and w['status']=='ACTIVE','ASSET_SOURCE_WORK_INVALID')
            guard(p.get('kind') in KINDS and p.get('problem_id') in self.problems,'ASSET_KIND_OR_PROBLEM_INVALID')
            guard(isinstance(pa,list) and len(pa)==len(set(pa)) and all(x in self.assets for x in pa),'BAD_ASSET_PARENTS')
            authorized=set(w['asset_input_ids'])|{x for x in w['published']}
            guard(set(pa).issubset(authorized),'UNAUTHORIZED_ASSET_PARENT')
            guard(all(x in self.sources for x in p.get('source_ids',[])),'UNKNOWN_ASSET_SOURCE')
            authorized_sources=set(w.get('source_ids',[]))
            # An INFORMED child may cite sources already linked to a pinned
            # parent asset. This is not a new tool execution or a discovery:
            # the original source ID, evidence class, and owner stay intact.
            # No general cross-worker source access; only declared lineage.
            if w['mode']=='INFORMED':
                for parent_id in w['asset_input_ids']:
                    authorized_sources.update(self.assets[parent_id].get('source_ids',[]))
            if self.r5_policy:
                authorized_sources.update(sid for sid,source in self.sources.items()
                    if source['kind']=='TOOL_RESULT' and source.get('work_id')==w['id'])
                authorized_sources.update(sid for sid,source in self.sources.items() if source['kind']=='PRIMARY')
            guard(set(p.get('source_ids',[])).issubset(authorized_sources),'ASSET_UNAUTHORIZED_SOURCE')
            guard(bool(w['steps']) and p.get('origin_step')==len(w['steps']),'ASSET_MUST_REFERENCE_WORK_STEP')
            guard(bool(p.get('claim')) and bool(p.get('scope')) and bool(p.get('assumptions')),'CLAIM_SCOPE_ASSUMPTIONS_REQUIRED')
            guard(isinstance(p.get('predictions'),list) and isinstance(p.get('limitations'),list),'ASSET_PREDICTIONS_LIMITATIONS_REQUIRED')
            if pa:guard(bool(p.get('delta_from_parents')),'PARENT_DELTA_REQUIRED')
            if w['mode']=='FRESH':
                guard(not pa or all(self.assets[x]['work_id']==w['id'] for x in pa),'FRESH_INHERITED_ASSET_FORBIDDEN')
                guard(all(self.sources[x]['kind']=='PRIMARY' or (self.r5_policy and self.sources[x]['kind']=='TOOL_RESULT' and self.sources[x].get('work_id')==w['id']) for x in p.get('source_ids',[])),'FRESH_ASSET_SOURCE_CONTAMINATION')
            self.assets[i]={**p,'status':'PROPOSED'}
            w['published'].append(i)
        elif kind=='ASSET_REVIEWED':
            a=self.assets.get(p.get('id'));decision=p.get('decision')
            guard(a and isinstance(decision,str) and REVIEW_LABEL.fullmatch(decision)
                  and isinstance(p.get('rationale'),str) and p['rationale'].strip()
                  and proper_id(p.get('reviewer_id')),'BAD_ASSET_REVIEW')
            guard(all(x in self.sources for x in p.get('source_ids',[])),'REVIEW_SOURCE_UNKNOWN')
            # Scientific conclusions are assertions by reviewers, never automated certifications.
            self.reviews.setdefault(a['id'],[]).append({**p,
                'normalized_state':decision if decision in REVIEW_DECISIONS else 'MODEL_DEFINED_REVIEW',
                'scientific_certification':False})
            a['status']=decision if decision in REVIEW_DECISIONS else 'MODEL_DEFINED_REVIEW'
            # Keep legacy asset materialization exactly as in R2 for all labels
            # recognized by R2. WORK_STARTED pins a hash of this representation.
            # The authored label remains in reviews; only unfamiliar labels need
            # the additional field to retain their normalized interpretation.
            if decision not in REVIEW_DECISIONS:
                a['latest_model_review_label']=decision
        elif kind=='WORK_RESPONSE_PROCESSED':
            w=self.work.get(p.get('id')); index=p.get('response_step')
            guard(w is not None and type(index)==int and 1<=index<=len(w['steps']), 'BAD_RESPONSE_PROCESS_MARKER')
            guard(w['steps'][index-1]['kind']=='MODEL_RESPONSE' and index not in w['processed_steps'],'DUPLICATE_OR_INVALID_PROCESS_MARKER')
            w['processed_steps'].append(index)
        elif kind=='WORK_FINISHED':
            w=self.work.get(p.get('id'))
            guard(w and w['status']=='ACTIVE' and p.get('outcome') in WORK_OUTCOMES and p.get('rationale'),'BAD_WORK_FINISH')
            w['status']='DONE';w['outcome']=p['outcome'];w['finish_rationale']=p['rationale']
        elif kind=='PROGRAM_REVIEWED':
            guard(self.program and p.get('scientific_status') in {'ONGOING','REVIEW_WORTHY_CANDIDATE','SCOPED_NEGATIVE','HOLD_WITH_RATIONALE','UNRESOLVED'},'BAD_PROGRAM_REVIEW')
            guard(proper_id(p.get('reviewer_id')) and bool(p.get('rationale')) and isinstance(p.get('considered_asset_ids'),list),'UNATTRIBUTED_PROGRAM_REVIEW')
            guard(all(a in self.assets for a in p['considered_asset_ids']),'UNKNOWN_PROGRAM_ASSETS')
            guard(isinstance(p.get('unresolved_opportunities'),list),'MISSING_OPEN_OPPORTUNITIES')
            self.program_reviews.append(p)
        elif kind=='HISTORICAL_ASSET_INDEXED':
            i=p.get('id'); refs=p.get('source_ids',[])
            guard(proper_id(i) and i not in self.assets and p.get('kind') in KINDS and p.get('problem_id') in self.problems,'BAD_HISTORICAL_ASSET')
            guard(refs and all(r in self.sources and self.sources[r]['kind']=='HISTORICAL_AI' for r in refs),'HISTORICAL_PROVENANCE_REQUIRED')
            guard(bool(p.get('claim')) and bool(p.get('scope')) and isinstance(p.get('assumptions'),str) and bool(p['assumptions']),'BAD_HISTORICAL_CLAIM_SCOPE')
            pa=p.get('parent_ids',[])
            guard(isinstance(pa,list) and len(pa)==len(set(pa)) and all(x in self.assets for x in pa),'INVALID_IMPORT_ASSET_PARENTS')
            self.assets[i]={**p,'status':'PROPOSED','origin':'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK','certification':'PROVISIONAL_UNVERIFIED'}
        elif kind=='MODEL_CALL_INTENT':
            i=p.get('id')
            guard(proper_id(i) and i not in self.model_calls and p.get('actor') in {'CONTROLLER','WORKER'} and HASH.fullmatch(p.get('request_blob','')),'MODEL_INTENT_INVALID')
            if p['actor']=='WORKER':guard(p.get('work_id') in self.work,'MODEL_WORK_UNKNOWN')
            self.model_calls[i]={**p,'state':'INTENT'}
        elif kind=='MODEL_CALL_SAVED':
            i=p.get('id');call=self.model_calls.get(i)
            guard(call and call['state']=='INTENT' and HASH.fullmatch(p.get('response_blob','')),'BAD_MODEL_RESPONSE')
            call['state']='SAVED';call['response_blob']=p['response_blob'];call['usage']=p.get('usage')
        elif kind=='MODEL_CALL_UNCERTAIN':
            i=p.get('id');call=self.model_calls.get(i)
            guard(call and call['state']=='INTENT','BAD_MODEL_UNCERTAIN')
            call['state']='UNCERTAIN';call['reason']=p.get('reason','PROVIDER_UNKNOWN')
        elif kind=='TOOL_RECORDED':
            i=p.get('id');w=self.work.get(p.get('work_id'))
            guard(proper_id(i) and i not in self.tool_results and w and w['status']=='ACTIVE' and HASH.fullmatch(p.get('request_blob','')) and HASH.fullmatch(p.get('result_blob','')),'BAD_TOOL_PROVENANCE')
            self.tool_results[i]=p
        elif kind=='CONTROLLER_DECISION':
            guard(proper_id(p.get('id')) and p.get('call_id') in self.model_calls and self.model_calls[p['call_id']]['state']=='SAVED','BAD_CONTROLLER_CALL')
            guard(not any(x['id']==p['id'] for x in self.controller_decisions),'DUPLICATE_CONTROLLER_DECISION')
            guard(HASH.fullmatch(p.get('parsed_blob','')) and bool(p.get('rationale')),'BAD_CONTROLLER_DECISION')
            self.controller_decisions.append(p)
        elif kind=='OPERATIONAL_PAUSE':
            guard(p.get('reason'),'PAUSE_REQUIRES_REASON')
            self.operational_pauses.append(p)
        else:raise EvidenceError('UNKNOWN_EVENT:'+str(kind))

class EvolutionJournal:
    def __init__(self,root):self.root=pathlib.Path(root).resolve();self._lock=threading.RLock()
    def init(self,problem,origin='NEW_PROJECT_NO_PRIOR_AI',criteria=None):
        guard(not self.root.exists(),'NEW_ROOT_REQUIRED')
        self.root.mkdir(parents=True);(self.root/'events').mkdir();(self.root/'blobs').mkdir()
        atomic(self.root/'manifest.json',canon({'protocol':PROTOCOL,'origin':origin,'immutability':'append_only','science_certified':False}))
        self.append('PROGRAM_CREATED',{'problem':problem,'criteria':criteria or 'Hypothesis ready for independent human review or scoped negative conclusion','origin':origin})
    def blob(self, content):
        """Publish a complete content-addressed blob atomically.

        A worker must never expose a partially written hash-named file to
        another worker's verify(). Staging happens outside blobs/, and link()
        creates the final name atomically without overwriting an existing
        blob. The RLock also serializes same-process readers and writers.
        """
        if not isinstance(content, bytes):
            content=canon(content)
        digest=sha(content)
        path=self.root/'blobs'/digest
        with self._lock:
            if not path.exists():
                fd, staging=tempfile.mkstemp(prefix='.e2-blob-stage-', dir=self.root)
                try:
                    with os.fdopen(fd,'wb') as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())
                    try:
                        os.link(staging,path)
                    except FileExistsError:
                        # Another process may have published the same hash.
                        pass
                finally:
                    os.unlink(staging)
            guard(path.read_bytes()==content,'BLOB_COLLISION_OR_TAMPER')
        return digest
    def raw(self,digest):
        guard(isinstance(digest,str) and HASH.fullmatch(digest),'INVALID_BLOB_ID')
        with self._lock:
            data=(self.root/'blobs'/digest).read_bytes()
            guard(sha(data)==digest,'BLOB_TAMPER')
            return data
    def _events(self):
        paths=sorted((self.root/'events').glob('*.json'))
        guard([p.name for p in paths]==[f'{i:08d}.json' for i in range(1,len(paths)+1)],'EVENT_GAP')
        old=None;out=[]
        for i,p in enumerate(paths,1):
            b=p.read_bytes();o=json.loads(b)
            guard(b==canon(o) and o.get('protocol')==PROTOCOL and o.get('seq')==i and o.get('prev')==old,'EVENT_HASH_CHAIN')
            old=sha(b);out.append(o)
        return out
    def verify(self):
        with self._lock:
            manifest=(self.root/'manifest.json').read_bytes();m=json.loads(manifest)
            guard(canon(m)==manifest and m.get('protocol')==PROTOCOL,'BAD_MANIFEST')
            s=State()
            for row in self._events():
                if row['kind']=='WORK_STARTED':
                    pin=row['payload'].get('input_blob')
                    guard(pin==sha(canon(self._context(s,row['payload']['id']))),'WORK_INPUT_SNAPSHOT_MISMATCH')
                s.apply(row['kind'],row['payload'])
                for k in ('raw_blob','blob','input_blob','request_blob','response_blob','result_blob','parsed_blob'):
                    if k in row['payload']:self.raw(row['payload'][k])
            # Content-addressable objects are verified even if unreferenced.
            for item in (self.root/'blobs').iterdir():
                guard(item.is_file() and item.name==sha(item.read_bytes()),'BLOB_INTEGRITY')
            return s
    def append(self,kind,payload):
        with self._lock:
            s=self.verify();s.apply(kind,payload)
            es=self._events();old=sha(canon(es[-1])) if es else None
            row={'protocol':PROTOCOL,'seq':len(es)+1,'prev':old,'kind':kind,'payload':payload}
            atomic(self.root/'events'/f'{len(es)+1:08d}.json',canon(row))
            return row
    def add_source(self,ident,kind,content,description):
        digest=self.blob(content)
        self.append('SOURCE_REGISTERED',{'id':ident,'kind':kind,'blob':digest,'description':description})
        return digest
    def evolve(self,ident,operation,asset_ids,work,reason):
        self.append('EVOLUTION_APPLIED',{'id':ident,'operation':operation,'asset_ids':asset_ids,'work':work,'reason':reason})
    def start(self,ident):
        pinned=self.blob(self.input_for(ident))
        self.append('WORK_STARTED',{'id':ident,'input_blob':pinned})
    def step(self,ident,kind,content):
        state=self.verify();num=len(state.work[ident]['steps'])+1
        digest=self.blob(content)
        self.append('WORK_STEP',{'id':ident,'kind':kind,'raw_blob':digest,'step':num})
        return digest
    def asset(self,ident,work_id,kind,problem_id,claim,assumptions,scope,predictions=None,limitations=None,
              parent_ids=None,delta_from_parents='',source_ids=None):
        s=self.verify();w=s.work[work_id]
        self.append('ASSET_PUBLISHED',{'id':ident,'work_id':work_id,'origin_step':len(w['steps']),'kind':kind,
            'problem_id':problem_id,'claim':claim,'assumptions':assumptions,'scope':scope,
            'predictions':predictions or [],'limitations':limitations or [],'parent_ids':parent_ids or [],
            'delta_from_parents':delta_from_parents,'source_ids':source_ids or [],'certification':'MODEL_PROPOSED_UNVERIFIED'})
    def finish(self,ident,outcome,rationale):
        self.append('WORK_FINISHED',{'id':ident,'outcome':outcome,'rationale':rationale})
    @staticmethod
    def _context(s,ident):
        w=s.work[ident]
        p={'problem':{'id':w['problem_id'],'question':s.problems[w['problem_id']]['question']},
           'work':{'id':ident,'question':w['question'],'mode':w['mode'],'operation':w['operation'],
             'research_rationale':w['research_rationale']},
           'source_entries':[{**s.sources[i]} for i in w.get('source_ids',[])],
           'parent_assets':[{**s.assets[i]} for i in w['asset_input_ids']]}
        if w['mode']=='FRESH':
            guard(not p['parent_assets'] and all(r['kind']=='PRIMARY' for r in p['source_entries']),'FRESH_CONTEXT_LEAK')
        return p
    def input_for(self,ident):
        """Returns pinned context after WORK_STARTED; FRESH never sees historical AI assets.

        Live provider adapter must append only its OWN later step history separately.
        """
        s=self.verify();w=s.work[ident]
        if w.get('input_blob'):return json.loads(self.raw(w['input_blob']))
        return self._context(s,ident)
    def report(self):
        s=self.verify();return {'protocol':PROTOCOL,'root':str(self.root),'events':len(self._events()),
          'program_goal':s.program['problem'],'problems':s.problems,'sources':s.sources,
          'assets':s.assets,'reviews':s.reviews,'work':s.work,'evolution':s.evolution,
          'program_reviews':s.program_reviews,'operational_pauses':s.operational_pauses,
          'scientific_certification':False,'paid_calls':sum(1 for c in s.model_calls.values() if c.get('billing_mode')=='EXTERNAL'),'actual_llm_calls':sum(c['state']=='SAVED' and c.get('billing_mode')=='EXTERNAL' for c in s.model_calls.values()),'model_calls':s.model_calls,'tool_results':s.tool_results,'controller_decisions':s.controller_decisions,
          'r5_policy':s.r5_policy,'e3r1_policy':s.e3r1_policy,'objective_assessments':s.objective_assessments,'integration_requests':s.integration_requests}
