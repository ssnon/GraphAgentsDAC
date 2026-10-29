"""R3: no-paid replay of the already-saved CTRL_D00003 in an immutable fork.

Original E2-R2 source is read-only. Only a revalidated, *model-authored* plan
may be committed; the operator makes no scientific choice and changes no
model-authored statements. A failed validation aborts without publishing ROOT.
"""
from __future__ import annotations
import json, os, pathlib, shutil, tempfile, fcntl
from .core import EvolutionJournal, EvidenceError, guard, canon, sha
from .provider import content_from_wire, strict_envelope
from .engine import controller_plan

CASE_ROOT='E2_R2_RECOVERED_20261027_130434'
CASE_RESPONSE_SHA='d15da6267d8a27cb627ff4f36fa69503714533af050a97bad8a45d5746f3be6d'
CASE_CALL_ID='CTRL_D00003'
CASE_DECISION_ID='D00003'
EXPECTED_ACTION_IDS=('EV_REPAIR_LAG_QUANT_01','EV_MIXED_STATE_IDENTIFIABILITY_01','EV_FACTORIAL_DECISION_RULES_01')
EXPECTED_REVIEW_IDS=('A_SHARED_LAG','A_SHARED_INDEPENDENT_LAG','A_COVARIANCE_NONIDENTIFIABILITY','A_MINIMAL_MATRIX','A_THERMO','A_P2_CONFOUNDED_SIGNATURES','A_PORTFOLIO_HOLD')


def _read_saved(j, *, expected_sha=None):
    s=j.verify()
    guard(CASE_CALL_ID in s.model_calls and s.model_calls[CASE_CALL_ID]['state']=='SAVED', 'R3_SAVED_CONTROLLER_NOT_FOUND')
    digest=s.model_calls[CASE_CALL_ID]['response_blob']
    if expected_sha is not None: guard(digest==expected_sha, 'R3_CONTROLLER_RESPONSE_HASH_MISMATCH')
    text=content_from_wire(j.raw(digest))
    obj=strict_envelope(text)
    guard(isinstance(obj,dict) and isinstance(obj.get('actions'),list) and isinstance(obj.get('reviews'),list), 'R3_UNPARSEABLE_OR_MISSING_FIELDS')
    return digest,obj


def commit_saved_controller(j, *, expected_sha=None):
    """Testable transaction preparation + append to a FORK, not source.

    Each event is simulated as a whole by controller_plan before mutation.
    Accepted labels are reviewer opinions, never automatic certifications.
    """
    s=j.verify()
    guard(not any(d['id']==CASE_DECISION_ID for d in s.controller_decisions),'R3_CONTROLLER_ALREADY_COMMITTED')
    digest,obj=_read_saved(j,expected_sha=expected_sha)
    guard([a.get('id') for a in obj['actions']]==list(EXPECTED_ACTION_IDS),'R3_UNEXPECTED_SAVED_ACTIONS')
    guard([r.get('id') for r in obj['reviews']]==list(EXPECTED_REVIEW_IDS),'R3_UNEXPECTED_REVIEW_SET')
    guard(obj.get('disposition')=='ONGOING','R3_UNEXPECTED_DISPOSITION')
    guard([r.get('decision') for r in obj['reviews'] if r.get('id') in {'A_COVARIANCE_NONIDENTIFIABILITY','A_P2_CONFOUNDED_SIGNATURES'}]==['RETAINED_WITH_LIMITS','RETAINED'],'R3_ORIGINAL_REVIEW_WORDS_CHANGED')
    planned=controller_plan(j,obj,CASE_CALL_ID,CASE_DECISION_ID)
    # Before the first mutation, all plan events have already been simulated.
    j.append('CONTROLLER_DECISION',{
        'id':CASE_DECISION_ID,'call_id':CASE_CALL_ID,
        'parsed_blob':j.blob(obj),'rationale':obj['rationale'],
        'commit_origin':'R3_REVALIDATED_PREVIOUSLY_SAVED_MODEL_DECISION',
        'original_response_blob_sha256':digest,
        'operator_reworded_model_text':False,
        'science_certification':False})
    for kind,p in planned:j.append(kind,p)
    j.append('OPERATIONAL_PAUSE',{
        'reason':'R3_REVALIDATED_SAVED_CONTROLLER_IN_FORK_NO_NEW_MODEL_CALL_NOT_NEW_SCIENCE',
        'call_id':CASE_CALL_ID,'response_blob_sha256':digest})
    return {'status':'SAVED_MODEL_DECISION_REVALIDATED_IN_FORK','controller_call_id':CASE_CALL_ID,
        'decision_id':CASE_DECISION_ID,'raw_response_sha256':digest,
        'reviews_committed':len(obj['reviews']),'works_queued':[a['work']['id'] for a in obj['actions']],
        'scientific_disposition':obj['disposition'],'science_certification':False,'new_model_calls':0}


def _validate_r2_source(j):
    s=j.verify()
    guard(j.root.name==CASE_ROOT,'R3_SOURCE_ROOT_NAME_MISMATCH')
    guard(len(j._events())==81,'R3_EXPECTED_81_EVENTS')
    guard(len(s.assets)==16 and len(s.model_calls)==6 and len(s.controller_decisions)==1 and len(s.work)==5,'R3_SOURCE_STATE_MISMATCH')
    guard(s.controller_decisions[0]['id']=='D00001','R3_EXPECTED_SINGLE_OLD_CONTROLLER')
    guard(s.work['W_CONTROLLED_PERTURBATION_TABLE']['status']=='ACTIVE','R3_EXPECTED_ACTIVE_THIRD_WORKER')
    guard(set(('A_P2_FACTORIAL_DISCRIMINATION','A_P2_ORTHOGONAL_NULLS','A_P2_CONFOUNDED_SIGNATURES')).issubset(s.assets),'R3_MISSING_NEW_SCIENCE')
    _read_saved(j, expected_sha=CASE_RESPONSE_SHA)
    return s


def fork_revalidate_r2_controller(source_root,new_root):
    src=pathlib.Path(source_root).resolve();dest=pathlib.Path(new_root).absolute()
    guard(src.is_dir() and src!=dest and not dest.exists() and not dest.is_relative_to(src),
          'R3_SOURCE_OR_NEW_ROOT_INVALID')
    guard(not any(p.is_symlink() for p in src.rglob('*')),'R3_SOURCE_SYMLINK_DENIED')
    lockpath=src/'.e2run.lock'
    guard(lockpath.is_file(),'R3_SOURCE_RUN_LOCK_MISSING')
    with lockpath.open('rb') as lock_handle:
        try:fcntl.flock(lock_handle,fcntl.LOCK_SH|fcntl.LOCK_NB)
        except BlockingIOError:raise EvidenceError('R3_SOURCE_ACTIVE_RUN_DENIED')
        try:return _fork_locked(src,dest)
        finally:fcntl.flock(lock_handle,fcntl.LOCK_UN)

def _fork_locked(src,dest):
    original=EvolutionJournal(src)
    _validate_r2_source(original)
    before=[sha(canon(e)) for e in original._events()]
    dest.parent.mkdir(parents=True, exist_ok=True)
    staging=pathlib.Path(tempfile.mkdtemp(prefix='.e2-r3-stage-',dir=dest.parent))
    try:
        shutil.copytree(src,staging,dirs_exist_ok=True)
        branch=EvolutionJournal(staging)
        # root dirname differs while staged; require all other source conditions.
        state=branch.verify()
        guard(len(branch._events())==81 and len(state.assets)==16 and len(state.model_calls)==6,'R3_FORK_COPY_NOT_IDENTICAL')
        out=commit_saved_controller(branch,expected_sha=CASE_RESPONSE_SHA)
        s=branch.verify()
        guard(len(s.controller_decisions)==2 and len(s.work)==8 and len(s.assets)==16,'R3_REPLAY_POSTCONDITION_FAILED')
        guard(all(s.work[w]['status']=='QUEUED' for w in out['works_queued']),'R3_NEW_WORK_NOT_QUEUED')
        guard(original.verify().controller_decisions[0]['id']=='D00001','R3_SOURCE_CHANGED')
        guard([sha(canon(e)) for e in original._events()]==before,'R3_SOURCE_EVENT_MUTATED')
        os.rename(staging,dest)
        return {**out,'new_root':str(dest),'source_root_unmodified':True,'source_events':81,
            'fork_events':len(branch._events()),
            'assets':len(s.assets),'works':len(s.work),'model_calls_total':len(s.model_calls),
            'controller_commits_total':len(s.controller_decisions)}
    except BaseException:
        shutil.rmtree(staging,ignore_errors=True)
        raise
