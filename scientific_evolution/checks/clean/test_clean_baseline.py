import os,sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bootstrap  # noqa: F401 (test-only E2 optional dependencies)
from e2core.core import EvolutionJournal, EvidenceError, canon, sha
import scientific_v4_clean_baseline as clean


def root_with_staged_call(path):
    j=EvolutionJournal(path)
    j.init('P0 checkpoint originality preserved')
    for lock in ('.scientific_feedback_autorun.lock','.e2run.lock'):
        (path/lock).touch()
    wire={'model':'openai/gpt-5.6-luna','temperature':.7,
          'max_tokens':16000,'response_format':{'type':'json_object'},'messages':[]}
    blob=j.blob(wire)
    j.append('MODEL_CALL_INTENT',{'id':'NVT_TEST_001','actor':'CONTROLLER','work_id':None,
                                 'request_blob':blob,'model':'openai/gpt-5.6-luna','billing_mode':'EXTERNAL'})
    j.append('MODEL_CALL_UNCERTAIN',{'id':'NVT_TEST_001','reason':'KeyboardInterrupt'})
    j.append('MODEL_CALL_INTENT',{'id':'NVT_REISSUE_TEST_001','actor':'CONTROLLER','work_id':None,
                                 'request_blob':blob,'model':'openai/gpt-5.6-luna','billing_mode':'EXTERNAL'})
    j.append('MODEL_CALL_SAVED',{'id':'NVT_REISSUE_TEST_001',
              'response_blob':j.blob({'choices':[{'message':{'content':'{}'}}]}),'usage':None})
    j.append('OPERATIONAL_PAUSE',{'reason':clean.v3.RECEIPT,
              'original_call_id':'NVT_TEST_001','reissue_call_id':'NVT_REISSUE_TEST_001',
              'original_request_blob':blob,
              'original_unknown_outcome':True,
              'potential_duplicate_provider_charge_ack':True})
    j.append('OPERATIONAL_PAUSE',{'reason':clean.v4.V4_FORK_RECEIPT})
    j.append('MODEL_CALL_INTENT',{'id':'CTRL_D00077','actor':'CONTROLLER','work_id':None,
            'request_blob':j.blob({'messages':[{'role':'system','content':'test'},
                                            {'role':'user','content':'{}'}]}),
            'model':'openai/gpt-5.6-luna','billing_mode':'MOCK'})
    j.append('MODEL_CALL_SAVED',{'id':'CTRL_D00077','response_blob':j.blob({'choices':[{'message':{'content':'{}'}}]}),'usage':None})
    j.append('CONTROLLER_DECISION',{'id':'D00077','call_id':'CTRL_D00077',
            'parsed_blob':j.blob({'actions':[],'disposition':'ONGOING'}),'rationale':'continue'})
    j.append('MODEL_CALL_INTENT',{'id':'OPP_D00078','actor':'CONTROLLER','work_id':None,
            'request_blob':j.blob({'messages':[]}),
            'model':'openai/gpt-5.6-luna','billing_mode':'EXTERNAL'})
    j.append('MODEL_CALL_SAVED',{'id':'OPP_D00078',
            'response_blob':j.blob({'choices':[{'message':{'content':'{}'}}]}),'usage':None})
    j.append('OPERATIONAL_PAUSE',{'reason':'OPERATIONAL_CALL_BUDGET_REACHED'})
    return j


class CleanBaselineTests(unittest.TestCase):
    def test_audit_reports_excluded_saved_call_without_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            j=root_with_staged_call(Path(t)/'source')
            before=[sha(canon(x)) for x in j._events()]
            a=clean.branch_analysis(j.root)
            self.assertEqual(a['retained_events'], 10)
            self.assertEqual(a['excluded_saved_call_count'],1)
            self.assertEqual(before,[sha(canon(x)) for x in j._events()])

    def test_fork_requires_explicit_ack_when_excluding_saved_external_call(self):
        with tempfile.TemporaryDirectory() as t:
            j=root_with_staged_call(Path(t)/'source')
            with self.assertRaisesRegex(EvidenceError,'PAID_SAVED_CALLS'):
                clean.fork(j.root,Path(t)/'new')
            self.assertFalse((Path(t)/'new').exists())

    def test_fork_creates_verifiable_d77_historical_branch(self):
        with tempfile.TemporaryDirectory() as t:
            j=root_with_staged_call(Path(t)/'source')
            source_before=[sha(canon(x)) for x in j._events()]
            report=clean.fork(j.root,Path(t)/'new',acknowledge_paid_tail=True)
            self.assertEqual(report['event'],'V4_CLEAN_FORK_CREATED_NO_PAID')
            self.assertEqual(source_before,[sha(canon(x)) for x in j._events()])
            new=EvolutionJournal(Path(t)/'new');st=new.verify()
            self.assertEqual(st.controller_decisions[-1]['id'],'D00077')
            self.assertNotIn('OPP_D00078',st.model_calls)
            self.assertEqual(st.model_calls['NVT_TEST_001']['state'],'UNCERTAIN')
            self.assertEqual(st.model_calls['NVT_REISSUE_TEST_001']['state'],'SAVED')
            self.assertEqual(st.program['problem'],j.verify().program['problem'])
            self.assertEqual(clean.inspect(Path(t)/'new')['excluded_tail_saved_calls'],1)
            self.assertEqual([sha(canon(x)) for x in new._events()[:-1]],source_before[:10])

    def test_scientific_tail_requires_separate_acknowledgement(self):
        with tempfile.TemporaryDirectory() as t:
            j=root_with_staged_call(Path(t)/'source')
            j.evolve('EV_STAGED','FRESH',[],{
              'id':'W_STAGED','mode':'FRESH','problem_id':'P0',
              'question':'A new source question','research_rationale':'Inspect evidence',
              'source_ids':[]},'A separate scientific idea after checkpoint')
            with self.assertRaisesRegex(EvidenceError,'SCIENTIFIC_EVENTS_IN_EXCLUDED_TAIL'):
                clean.fork(j.root,Path(t)/'new',acknowledge_paid_tail=True)
            a=clean.branch_analysis(j.root)
            self.assertEqual(a['excluded_scientific_events'][0]['kind'],'EVOLUTION_APPLIED')
            self.assertFalse((Path(t)/'new').exists())

    def test_does_not_silently_skip_new_uncertain_tail(self):
        with tempfile.TemporaryDirectory() as t:
            j=root_with_staged_call(Path(t)/'source')
            j.append('MODEL_CALL_INTENT',{'id':'OPP_UNK','actor':'CONTROLLER','work_id':None,
                'request_blob':j.blob({'a':1}),'model':'test','billing_mode':'EXTERNAL'})
            j.append('MODEL_CALL_UNCERTAIN',{'id':'OPP_UNK','reason':'ProviderError'})
            with self.assertRaises(EvidenceError):clean.branch_analysis(j.root)

    def test_rejects_wrong_checkpoint_no_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            j=root_with_staged_call(Path(t)/'source')
            with self.assertRaises(EvidenceError):clean.branch_analysis(j.root,'D00076')

    def test_preflight_makes_no_provider_call_and_paid_requires_key(self):
        with patch.object(clean,'inspect',return_value={'event':'V4_CLEAN_BASELINE_PREFLIGHT'}),\
             patch.object(clean.v4,'run') as wrapped:
            self.assertEqual(clean.run('/dummy',preflight=True),0)
            wrapped.assert_not_called()
            with patch.dict(os.environ,{'FAKG_RESEARCH_ALLOW_PAID':'YES'},clear=True):
                with self.assertRaisesRegex(EvidenceError,'OPENROUTER_API_KEY_REQUIRED'):
                    clean.run('/dummy',paid=True)
            wrapped.assert_not_called()

    def test_run_delegates_to_pinned_v4_only(self):
        with patch.object(clean,'inspect',return_value={'event':'V4_CLEAN_BASELINE_PREFLIGHT'}),\
             patch.object(clean.v4,'run',return_value=0) as wrapped,\
             patch.dict(os.environ,{'FAKG_RESEARCH_ALLOW_PAID':'YES','OPENROUTER_API_KEY':'test-only'}):
            self.assertEqual(clean.run('/dummy',paid=True),0)
            self.assertTrue(wrapped.called)


if __name__=='__main__':unittest.main()
