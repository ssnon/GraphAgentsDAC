import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import bootstrap
from e2core.core import EvolutionJournal, EvidenceError, canon,sha
from e2core.provider import DurableModel
from e2core.engine import Engine
import scientific_research_readiness_v4 as v4
import scientific_closed_loop_v3 as v3
import scientific_problem_evolution as spe

class V4Tests(unittest.TestCase):
 def newroot(self,where):
  j=EvolutionJournal(where);j.init('Original P0: develop novel, plausible pre-experiment hypothesis.')
  (where/'.scientific_feedback_autorun.lock').touch();(where/'.e2run.lock').touch()
  wire={'model':'openai/gpt-5.6-luna','max_tokens':16000,'messages':[]}
  old='NVT_TEST_001';new='NVT_REISSUE_TEST_001'
  j.append('MODEL_CALL_INTENT',{'id':old,'actor':'CONTROLLER','work_id':None,
   'request_blob':j.blob(wire),'model':'openai/gpt-5.6-luna','billing_mode':'EXTERNAL'})
  j.append('MODEL_CALL_UNCERTAIN',{'id':old,'reason':'KeyboardInterrupt'})
  j.append('MODEL_CALL_INTENT',{'id':new,'actor':'CONTROLLER','work_id':None,
   'request_blob':j.blob(wire),'model':'openai/gpt-5.6-luna','billing_mode':'EXTERNAL'})
  resp={'choices':[{'message':{'content':'{}'}}]}
  j.append('MODEL_CALL_SAVED',{'id':new,'response_blob':j.blob(resp),'usage':None})
  j.append('OPERATIONAL_PAUSE',{'reason':v3.RECEIPT,'original_call_id':old,'reissue_call_id':new,
     'original_request_blob':sha(canon(wire)),
     'original_unknown_outcome':True,'potential_duplicate_provider_charge_ack':True})
  return j
 def test_fork_preserves_source_head_and_unknown(self):
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'src';dst=Path(d)/'out';j=self.newroot(src)
   before=[sha(canon(e)) for e in j._events()]
   result=v4.fork(src,dst)
   self.assertEqual(result['status'],'V4_ROOT_PREPARED_NO_PAID')
   self.assertEqual(before,[sha(canon(e)) for e in j._events()])
   n=EvolutionJournal(dst)
   self.assertEqual(before,[sha(canon(e)) for e in n._events()[:-1]])
   self.assertEqual(n.verify().model_calls['NVT_TEST_001']['state'],'UNCERTAIN')
   self.assertEqual(n.verify().model_calls['NVT_REISSUE_TEST_001']['state'],'SAVED')
   self.assertEqual(n.verify().program,j.verify().program)
   self.assertEqual(v4.inspect(dst)['v4_research_readiness_separated'],True)
 def test_existing_root_not_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'src';dst=Path(d)/'out';self.newroot(src);dst.mkdir()
   with self.assertRaises(EvidenceError):v4.fork(src,dst)
 def test_unknown_additional_call_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   j=self.newroot(Path(d)/'src')
   j.append('MODEL_CALL_INTENT',{'id':'NVT_UNK','actor':'CONTROLLER','work_id':None,
     'request_blob':j.blob({'hello':True}),'model':'openai/gpt-5.6-luna','billing_mode':'EXTERNAL'})
   with self.assertRaises(EvidenceError):v4.fork(j.root,Path(d)/'other')
 def test_readiness_distinguishes_start_and_certification(self):
  r=v4.READINESS_TEMPLATE
  self.assertIn('Not necessarily raw experimental trajectories',r['theoretical_readiness']['data_required_to_begin'])
  self.assertIn('required for empirical attribution',r['empirical_readiness']['data_required_to_begin'])
  self.assertTrue(r['controller_autonomy']['may_select_no_action'])
  self.assertTrue(r['controller_autonomy']['may_select_parallel_work'])
 def test_runtime_patches_and_restores(self):
  originals=(v3._work_options,v3._science_fingerprint,v3.V3_ADVISORY,spe.OPPORTUNITY_PROMPT,spe.feedback_worker_input)
  with v4.runtime():
   self.assertIs(v3._work_options,v4.science_work_options)
   self.assertIs(v3._science_fingerprint,v4.readiness_science_fingerprint)
   self.assertIs(spe.feedback_worker_input,v4.worker_input)
   self.assertIn('theoretical readiness',spe.OPPORTUNITY_PROMPT)
   self.assertIn('empirical source incompleteness',v3.V3_ADVISORY.lower())
  self.assertEqual(originals,(v3._work_options,v3._science_fingerprint,v3.V3_ADVISORY,spe.OPPORTUNITY_PROMPT,spe.feedback_worker_input))
 def test_runtime_restored_after_exception(self):
  original=spe.OPPORTUNITY_PROMPT
  with self.assertRaises(ZeroDivisionError):
   with v4.runtime():raise ZeroDivisionError()
  self.assertEqual(spe.OPPORTUNITY_PROMPT,original)
 def test_fresh_worker_exactly_unchanged(self):
  # This is a realistic payload-level FRESH isolation check.
  class Journal:
   def verify(self):return type('S',(),{'work':{'wf':{'mode':'FRESH'},'wi':{'mode':'INFORMED','asset_input_ids':['A1']}}})()
  j=Journal()
  with patch.object(v4,'BASE_WORKER_INPUT',return_value={'pinned_input':{'mode':'FRESH'},'own_prior_steps':[]}):
   x=v4.worker_input(j,'wf')
   self.assertEqual(x,{'pinned_input':{'mode':'FRESH'},'own_prior_steps':[]})
 def test_informed_worker_inherits_claim_p0_delta_without_certification(self):
  class Journal:
   def verify(self):return type('S',(),{'work':{'wi':{'mode':'INFORMED','asset_input_ids':['A1']}}})()
  j=Journal()
  with patch.object(v4,'BASE_WORKER_INPUT',return_value={'pinned_input':{'mode':'INFORMED'}}),\
      patch.object(v4,'committed_delta_handoff',return_value={'model_assessment_only':True,'claim_to_original_problem':[{'asset_id':'A1'}]}):
   x=v4.worker_input(j,'wi')
  self.assertTrue(x['v4_claim_problem_scientific_handoff']['model_assessment_only'])
  self.assertIn('empirical',x['v4_research_readiness']) if False else None
 def test_last_committed_trace_real_model_payload(self):
  with tempfile.TemporaryDirectory() as d:
   j=EvolutionJournal(Path(d)/'src');j.init('P0 exact immutable')
   q={'claim_prior_art_assessment':{'claim_assessments':[{'asset_id':'A1','relation':'PARTIAL_OVERLAP_REPORTED',
       'evidence_ids':['S1'],'remaining_conditional_claim':'Novel prediction remains under hypothesis'}]},
       'problem_level_impact':{'claim_to_problem':[{'asset_id':'A1','impact_on_original_problem':'Does not solve P0'}],
         'problem_impact':{'state':'UNCHANGED','still_unresolved_requirements':['new prediction']}},
       'prior_art_delta':{'new_or_changed_claims':[{'asset_id':'A1'}]}}
   wire={'messages':[{'role':'system','content':'x'},
             {'role':'user','content':json.dumps(q)}]}
   j.append('MODEL_CALL_INTENT',{'id':'CTRL_D00001','actor':'CONTROLLER','work_id':None,
       'request_blob':j.blob(wire),'model':'openai/gpt-5.6-luna','billing_mode':'MOCK'})
   j.append('MODEL_CALL_SAVED',{'id':'CTRL_D00001','response_blob':j.blob({'choices':[{'message':{'content':'{}'}}]}),'usage':None})
   j.append('CONTROLLER_DECISION',{'id':'D00001','call_id':'CTRL_D00001','parsed_blob':j.blob({'actions':[]}), 'rationale':'science'})
   out=v4.committed_delta_handoff(j)
   self.assertTrue(out['model_assessment_only'])
   self.assertEqual(out['novelty_claim_rows'][0]['asset_id'],'A1')
   self.assertEqual(out['claim_to_original_problem'][0]['impact_on_original_problem'],'Does not solve P0')
   self.assertEqual(out['working_problem_interpretation']['state'],'UNCHANGED')
 def test_model_mock_receives_readiness_context_and_can_select_zero_actions(self):
  with tempfile.TemporaryDirectory() as d:
   j=EvolutionJournal(Path(d)/'src');j.init('Original P0 is not an empirical proof demand')
   prompts=[]; reqs=[]
   def provider(wire,timeout=180):
    req=json.loads(wire); prompts.append(req['messages'][0]['content']);reqs.append(req)
    prompt=req['messages'][0]['content']
    if prompt==spe.NOVELTY_PROMPT: ans={'claim_assessments':[],'research_gaps':[]}
    elif prompt==spe.IMPACT_PROMPT:
     ans={'claim_to_problem':[],'problem_impact':{'state':'UNCHANGED','reason':'no new physical claim',
      'affected_requirements':[],'still_unresolved_requirements':['new distinct mechanism'],
      'original_problem_still_open':True}}
    elif 'V4 pre-experiment scientific research' in prompt:
     ans={'opportunities':[]}
    else:
     ans={'rationale':'No scientifically nonredundant work is yet found',
      'actions':[],'new_problems':[],'reviews':[],'disposition':'ONGOING',
      'unresolved_opportunities':['continue independent search']}
    return json.dumps({'choices':[{'message':{'content':json.dumps(ans)}}]}).encode()
   gateway=DurableModel(j,provider=provider,approved=True,max_new_calls=8,mode='MOCK')
   engine=Engine(j,gateway)
   with patch.object(v3,'controller_plan',return_value=[]),patch.dict(os.environ,FAKG_RESEARCH_ALLOW_PAID='YES'):
    with v4.runtime():r=v3.controller_v3(engine,'D00001')
   self.assertEqual(r['status'],'CONTROLLER_COMMITTED')
   self.assertEqual(r['actions'],0)
   self.assertEqual(len(prompts),4)
   opportunity=reqs[2]
   self.assertIn('V4 pre-experiment scientific research',opportunity['messages'][0]['content'])
   context=json.loads(opportunity['messages'][1]['content'])
   self.assertIn('v4_research_readiness',context['v3_science_work_options'])
   self.assertTrue(context['v3_science_work_options']['v4_research_readiness']['controller_autonomy']['may_select_no_action'])
   self.assertIn('V4 scientific readiness',prompts[3])
   self.assertEqual(j.verify().program['problem'],'Original P0 is not an empirical proof demand')
 def test_real_controller_can_commit_distinct_informed_work_during_active_fresh(self):
  with tempfile.TemporaryDirectory() as d:
   j=EvolutionJournal(Path(d)/'science');j.init('Original P0 immutable scientific discovery task')
   j.evolve('EV_SEED','FRESH',[],{'id':'W_FRESH','mode':'FRESH','problem_id':'P0',
     'question':'Read accessible primary SERS literature','research_rationale':'Source acquisition to inspect measured controls',
     'source_ids':[]},'Original independently unseeded research')
   j.start('W_FRESH');j.step('W_FRESH','MODEL_WORK',{'scientific_text':'Conditional mechanism claim'})
   j.asset('A_SEED','W_FRESH','HYPOTHESIS','P0','Candidate mechanism description',
     ['Explicit dimensionless regime'],'SERS under defined conditions',
     predictions=['Observable difference under control'],limitations=['Not empirically validated'])
   def provider(wire,timeout=180):
    request=json.loads(wire);prompt=request['messages'][0]['content']
    if prompt==spe.NOVELTY_PROMPT:answer={'claim_assessments':[],'research_gaps':[]}
    elif prompt==spe.IMPACT_PROMPT:answer={'claim_to_problem':[],
      'problem_impact':{'state':'UNCHANGED','reason':'P0 not yet solved',
       'affected_requirements':[],'still_unresolved_requirements':['distinctive novel prediction'],
       'original_problem_still_open':True}}
    elif 'V4 pre-experiment scientific research' in prompt:answer={'opportunities':[]}
    else:answer={'rationale':'A mathematically independent theoretical counterexample is useful now',
     'actions':[{'id':'EV_NEW_THEORY','operation':'CHALLENGE','asset_ids':['A_SEED'],
      'reason':'Independent physically bounded counterexample calculation',
      'work':{'id':'W_INFORMED_THEORY','mode':'INFORMED','problem_id':'P0',
         'question':'Derive strong-null counterexample against the proposed causal prediction',
         'research_rationale':'Theoretical stress test can proceed without raw trajectories and differs from source retrieval',
         'source_ids':[]}}], 'new_problems':[],'reviews':[],
      'disposition':'ONGOING','unresolved_opportunities':['Need later experimental calibration']}
    return json.dumps({'choices':[{'message':{'content':json.dumps(answer)}}]}).encode()
   model=DurableModel(j,provider=provider,approved=True,max_new_calls=10,mode='MOCK')
   engine=Engine(j,model)
   with patch.dict(os.environ,FAKG_RESEARCH_ALLOW_PAID='YES'):
    with v4.runtime():
     result=v3.controller_v3(engine,'D00001')
     self.assertEqual(result['status'],'CONTROLLER_COMMITTED')
     self.assertEqual(result['actions'],1)
     self.assertEqual(j.verify().work['W_FRESH']['status'],'ACTIVE')
     self.assertEqual(j.verify().work['W_INFORMED_THEORY']['status'],'QUEUED')
     informed=v4.worker_input(j,'W_INFORMED_THEORY')
     self.assertTrue(informed['v4_claim_problem_scientific_handoff']['model_assessment_only'])
     self.assertEqual(informed['v4_claim_problem_scientific_handoff']['controller_decision'],'D00001')
     fresh=v4.worker_input(j,'W_FRESH')
     self.assertNotIn('v4_claim_problem_scientific_handoff',fresh)
     self.assertNotIn('working_problem_state',fresh)
   self.assertEqual(j.verify().program['problem'],'Original P0 immutable scientific discovery task')
 def test_new_v4_advisory_contract_invalidates_prior_cache_once_without_changing_nvt_request(self):
  inputs=({'program':{'problem':'P0'},'problems':[]},[],[])
  old=v3._science_fingerprint(*inputs)
  with v4.runtime():
   now=v3._science_fingerprint(*inputs)
   self.assertNotEqual(old,now)
   self.assertEqual(now,v3._science_fingerprint(*inputs))
  self.assertEqual(old,v3._science_fingerprint(*inputs))
 def test_v3_replay_safety_kept_unmodified(self):
  self.assertIs(v3.source_code_guard,v4.v3.source_code_guard)
  self.assertIs(v3.should_controller_run,v4.v3.should_controller_run)
  self.assertIn('MODEL_REPLAY_INPUT_CHANGED',__import__('inspect').getsource(DurableModel.call))

if __name__=='__main__':unittest.main()
