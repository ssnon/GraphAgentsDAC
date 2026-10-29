"""Provider boundary with durable call intents and fail-closed network approvals."""
from __future__ import annotations
import os, json, urllib.request, threading
from .core import EvolutionJournal, EvidenceError, canon, guard, sha

API_URL='https://openrouter.ai/api/v1/chat/completions'
MAX_PROVIDER_RESPONSE=4_000_000

def openrouter(wire:bytes,timeout=180):
    key=os.environ.get('OPENROUTER_API_KEY')
    guard(bool(key),'OPENROUTER_API_KEY_REQUIRED')
    req=urllib.request.Request(API_URL,data=wire,method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        raw=response.read(MAX_PROVIDER_RESPONSE+1)
    guard(len(raw)<=MAX_PROVIDER_RESPONSE,'MODEL_HTTP_RESPONSE_TOO_LARGE')
    return raw

def content_from_wire(raw):
    outer=json.loads(raw)
    msg=outer['choices'][0]['message']['content']
    if isinstance(msg,dict):return json.dumps(msg,ensure_ascii=False)
    guard(isinstance(msg,str),'PROVIDER_CONTENT_NOT_TEXT')
    return msg

def strict_envelope(text):
    """A single valid JSON document or one unambiguous JSON envelope; never repair broken JSON."""
    decoder=json.JSONDecoder();candidates=[]
    try:
        o=json.loads(text)
        if isinstance(o,dict):return o
    except (ValueError,TypeError):pass
    # Allow a preamble only if the JSON envelope is unique, and preamble has no additional JSON object.
    for ix,ch in enumerate(text):
        if ch!='{':continue
        try:o,end=decoder.raw_decode(text,ix)
        except (ValueError,TypeError):continue
        if isinstance(o,dict) and ('scientific_text' in o or 'actions' in o):candidates.append(o)
        if len(candidates)>1:return None
    return candidates[0] if len(candidates)==1 else None

class DurableModel:
    def __init__(self,j:EvolutionJournal,provider=openrouter,approved=False,max_new_calls=0,model='openai/gpt-5.6-luna',max_tokens=7000,timeout=180,mode='EXTERNAL'):
        self.j=j;self.provider=provider;self.approved=approved;self.max_new_calls=max_new_calls
        self.model=model;self.max_tokens=max_tokens;self.timeout=timeout;self.mode=mode;self.new_calls=0;self.lock=threading.Lock()
        guard(mode in {'EXTERNAL','MOCK'},'INVALID_MODEL_GATEWAY_MODE')
    def call(self,ident,actor,work_id,system,payload):
        wire=canon({'model':self.model,'temperature':0.7,'max_tokens':self.max_tokens,
            'response_format':{'type':'json_object'},'messages':[{'role':'system','content':system},
              {'role':'user','content':json.dumps(payload,ensure_ascii=False,sort_keys=True,allow_nan=False)}]})
        with self.lock:
            previous=self.j.verify().model_calls.get(ident)
            if previous:
                guard(previous['request_blob']==sha(wire),'MODEL_REPLAY_INPUT_CHANGED')
                guard(previous['state']=='SAVED','UNCERTAIN_MODEL_CALL_NO_AUTOMATIC_RETRY')
                return content_from_wire(self.j.raw(previous['response_blob']))
            guard(self.approved and os.environ.get('FAKG_RESEARCH_ALLOW_PAID')=='YES','PAID_EXECUTION_NOT_EXPLICITLY_APPROVED')
            guard(self.max_new_calls is None or self.new_calls<self.max_new_calls,'OPERATIONAL_CALL_BUDGET_REACHED')
            self.new_calls+=1
            self.j.append('MODEL_CALL_INTENT',{'id':ident,'actor':actor,'work_id':work_id,'request_blob':self.j.blob(wire),
                'model':self.model,'billing_mode':self.mode})
        try:
            raw=self.provider(wire,timeout=self.timeout)
            guard(isinstance(raw,bytes) and len(raw)<=MAX_PROVIDER_RESPONSE,'INVALID_PROVIDER_RAW')
        except BaseException as exc:
            self.j.append('MODEL_CALL_UNCERTAIN',{'id':ident,'reason':type(exc).__name__})
            raise EvidenceError('PROVIDER_UNKNOWN_OUTCOME_NO_AUTOMATIC_RETRY') from None
        # Response bytes saved before interpreting payload: if parse fails, no re-billing.
        try:
            usage=json.loads(raw).get('usage')
        except (ValueError,TypeError,AttributeError):usage=None
        self.j.append('MODEL_CALL_SAVED',{'id':ident,'response_blob':self.j.blob(raw),'usage':usage})
        return content_from_wire(raw)
