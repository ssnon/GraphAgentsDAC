import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import bootstrap

from e2core.core import EvolutionJournal, EvidenceError, canon, sha
import scientific_closed_loop_v3 as v3

class V3ContractTests(unittest.TestCase):
 def new_journal(self,root):
  j=EvolutionJournal(root);j.init('P0 original hypothesis research')
  (root/'.scientific_feedback_autorun.lock').touch()
  (root/'.e2run.lock').touch()
  req={'model':'openai/gpt-5.6-luna','max_tokens':16000,'messages':[]}
  old='NVT_TEST_001';new='NVT_REISSUE_TEST_001'
  j.append('MODEL_CALL_INTENT',{'id':old,'actor':'CONTROLLER','work_id':None,
     'request_blob':j.blob(req),'model':req['model'],'billing_mode':'EXTERNAL'})
  j.append('MODEL_CALL_UNCERTAIN',{'id':old,'reason':'KeyboardInterrupt'})
  j.append('MODEL_CALL_INTENT',{'id':new,'actor':'CONTROLLER','work_id':None,
     'request_blob':j.blob(req),'model':req['model'],'billing_mode':'EXTERNAL'})
  resp={'choices':[{'message':{'content':'{}'}}]}
  j.append('MODEL_CALL_SAVED',{'id':new,'response_blob':j.blob(resp),'usage':None})
  j.append('OPERATIONAL_PAUSE',{'reason':v3.RECEIPT,'original_call_id':old,
     'reissue_call_id':new,'original_request_blob':sha(canon(req)),
     'original_unknown_outcome':True,'potential_duplicate_provider_charge_ack':True})
  return j
 def test_fork_immutable_and_reissue_preserved(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp)/'before'; b=Path(tmp)/'after';old=self.new_journal(a)
   oldbytes=[sha(canon(x)) for x in old._events()]
   out=v3.fork(a,b)
   self.assertEqual(out['status'],'V3_FORK_PREPARED_NO_PAID')
   new=EvolutionJournal(b)
   self.assertEqual(oldbytes,[sha(canon(x)) for x in old._events()])
   self.assertEqual(oldbytes,[sha(canon(x)) for x in new._events()[:-1]])
   self.assertEqual(len(new.verify().model_calls),2)
   self.assertEqual(v3.status(b)['historical_unknown_status'],'UNCERTAIN')
   self.assertEqual(v3.status(b)['replacement_status'],'SAVED')
   self.assertEqual(new.verify().program,old.verify().program)
 def test_fork_cannot_overwrite_existing(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp)/'before';b=Path(tmp)/'exists';self.new_journal(a);b.mkdir()
   with self.assertRaises(EvidenceError):v3.fork(a,b)
 def test_unresolved_additional_call_fails_closed(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp)/'before';j=self.new_journal(a)
   j.append('MODEL_CALL_INTENT',{'id':'NVT_ANOTHER_UNKNOWN','actor':'CONTROLLER',
       'work_id':None,'request_blob':j.blob({'a':'b'}),
       'model':'openai/gpt-5.6-luna','billing_mode':'EXTERNAL'})
   with self.assertRaises(EvidenceError):v3.status(a)
 def test_trigger_skips_metadata_and_preserves_direct_source_science(self):
  class F:
   def __init__(self,events,source):
    self.rows=events
    self.s=type('State',(),{
     'r5_policy':False,'integration_requests':[],
     'controller_decisions':[{'id':'D00001'}], 'e3r1_policy':True,
     'work':{'w':{'status':'ACTIVE'}},
     'sources':{'SRC1':{'kind':'TOOL_RESULT','blob':'SRCBLOB'}}})()
    self.source=source
   def verify(self):return self.s
   def _events(self):return self.rows
   def raw(self,_):return json.dumps(self.source).encode()
  ctl={'kind':'CONTROLLER_DECISION','payload':{}}
  claim={'kind':'ASSET_PUBLISHED','payload':{'kind':'LITERATURE_CLAIM','source_ids':['SRC1']}}
  x=type('Runner',(),{'serial_fair':False})()
  x.j=F([ctl,claim],{'evidence_class':'BIBLIOGRAPHIC_METADATA'})
  self.assertFalse(v3.should_controller_run(x))
  x.j=F([ctl,claim],{'evidence_class':'OA_PDF_TEXT'})
  self.assertTrue(v3.should_controller_run(x))
  x.j=F([ctl,{'kind':'ASSET_PUBLISHED','payload':{'kind':'HYPOTHESIS','source_ids':[]}}],{})
  self.assertTrue(v3.should_controller_run(x))
 def test_exact_science_fingerprint_excludes_only_metadata(self):
  b={'program':{'problem':'P0'},'problems':[]}; claims=[{'id':'A','claim':'P'}]
  a=[{'evidence_id':'S1','inspection_class':'BIBLIOGRAPHIC_METADATA','returned_content':'x'}]
  c=[{'evidence_id':'S2','inspection_class':'BIBLIOGRAPHIC_METADATA','returned_content':'different'}]
  self.assertEqual(v3._science_fingerprint(b,claims,a),v3._science_fingerprint(b,claims,c))
  d=[{'evidence_id':'S3','inspection_class':'OA_PDF_TEXT','returned_content':'direct'}]
  self.assertNotEqual(v3._science_fingerprint(b,claims,a),v3._science_fingerprint(b,claims,a+d))
  self.assertNotEqual(v3._science_fingerprint(b,claims,a),v3._science_fingerprint(b,claims+[{'id':'B','claim':'new'}],a))
 def test_fresh_input_still_unmodified_by_v3(self):
  from scientific_problem_evolution import feedback_worker_input
  import e2core.engine as e
  self.assertIsNotNone(e._worker_input)
  self.assertNotIn('worker_input',v3.__dict__) # V3 does not replace FRESH worker prompt
 def test_reuse_of_prior_validated_assessments_only_on_identical_science(self):
  from unittest.mock import patch
  from e2core.provider import DurableModel
  from e2core.engine import Engine
  with tempfile.TemporaryDirectory() as tmp:
   j=EvolutionJournal(Path(tmp)/'test');j.init('P0 pre-experiment physical discovery')
   responses=[]
   def provider(request,timeout=180):
    data=json.loads(request)
    prompt=data['messages'][0]['content']
    if prompt==v3.spe.NOVELTY_PROMPT:
     ans={'claim_assessments':[],'research_gaps':[]}
    elif prompt==v3.spe.IMPACT_PROMPT:
     ans={'claim_to_problem':[],'problem_impact':{'state':'UNCHANGED','reason':'No evidence',
             'affected_requirements':[],'still_unresolved_requirements':['new mechanism'],
             'original_problem_still_open':True}}
    elif prompt==v3.spe.OPPORTUNITY_PROMPT:
     ans={'opportunities':[]}
    else:
     ans={'rationale':'Independent work selection in dry-run is unrestricted',
          'actions':[],'new_problems':[],'reviews':[],
          'disposition':'ONGOING','unresolved_opportunities':['Research P0']}
    responses.append(prompt)
    return json.dumps({'choices':[{'message':{'content':json.dumps(ans)}}]}).encode()
   m=DurableModel(j,provider=provider,approved=True,max_new_calls=20,mode='MOCK')
   e=Engine(j,m)
   with patch.object(v3,'controller_plan',return_value=[]),patch.dict(os.environ,FAKG_RESEARCH_ALLOW_PAID='YES'):
    r1=v3.controller_v3(e,'D00001')
    self.assertEqual(r1['status'],'CONTROLLER_COMMITTED')
    self.assertFalse(r1['v3_reused_novelty_impact'])
    self.assertEqual(len(responses),4)
    r2=v3.controller_v3(e,'D00002')
    self.assertTrue(r2['v3_reused_novelty_impact'])
    self.assertTrue(r2['v3_reused_opportunity'])
    self.assertEqual(len(responses),5)
    # New primary passage is a material change and reopens both evaluations.
    j.add_source('S_DIRECT','TOOL_RESULT',
        {'evidence_class':'OA_PDF_TEXT','result':{'text':'New, directly inspected temporal SERS paper passage.'}},
        'Literature research result with directly inspected content')
    r3=v3.controller_v3(e,'D00003')
    self.assertFalse(r3['v3_reused_novelty_impact'])
    self.assertEqual(len(responses),9)
    self.assertEqual(len(j.verify().controller_decisions),3)
    self.assertEqual(j.verify().program['problem'],'P0 pre-experiment physical discovery')

 def test_runtime_is_restored(self):
  import scientific_problem_evolution as spe
  old=spe.feedback_controller;oldg=spe.feedback_should_controller_run
  with v3.v3_runtime():
   self.assertIs(spe.feedback_controller,v3.controller_v3)
   self.assertIs(spe.feedback_should_controller_run,v3.should_controller_run)
  self.assertIs(spe.feedback_controller,old)
  self.assertIs(spe.feedback_should_controller_run,oldg)

if __name__=='__main__':unittest.main()
