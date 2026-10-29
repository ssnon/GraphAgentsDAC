"""Explicit, read-verified operational contract upgrade for old E3R1R1 journals.

Never changes prior science, decisions, saved call IDs, or rejected proposals.
Does not execute a model; the user must explicitly resume a separate campaign.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .core import EvolutionJournal, EvidenceError, guard

VERSION='E3R1R2_FRONTIER_CONTINUATION_V1'


def upgrade(root, *, commit=False):
    journal=EvolutionJournal(root)
    s=journal.verify()
    guard(s.e3r1_policy and s.r5_policy, 'UPGRADE_REQUIRES_E3R1R5_ROOT')
    guard(all(c['state']=='SAVED' for c in s.model_calls.values()),
          'UNRESOLVED_MODEL_CALL_BEFORE_UPGRADE')
    previous=s.runtime_contract_version
    if previous:
        guard(previous==VERSION,'OTHER_RUNTIME_CONTRACT_ALREADY_APPLIED')
        status='ALREADY_UPGRADED'
    elif commit:
        journal.append('RUNTIME_CONTRACT_UPGRADED',{
            'version':VERSION,
            'reason':'Operator-authorized operational schema continuation; earlier schema rejection records preserved, no science decision changed.'})
        journal.verify()
        status='UPGRADED'
    else:
        status='DRY_RUN_NO_MUTATION'
    current=journal.verify()
    return {'status':status,'root':str(journal.root),'version':VERSION,
            'events':len(journal._events()),'model_calls':len(current.model_calls),
            'controller_decisions':len(current.controller_decisions),
            'work_statuses':{wid:w['status'] for wid,w in current.work.items()},
            'last_research_status':(current.objective_assessments[-1].get('research_status')
                                    if current.objective_assessments else None),
            'paid_calls':0,'scientific_certification':False}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',required=True)
    ap.add_argument('--commit',action='store_true',help='Append one checked operational event; dry-run by default')
    ns=ap.parse_args()
    print(json.dumps(upgrade(ns.root,commit=ns.commit),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
