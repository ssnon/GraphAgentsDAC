"""Deterministic synthetic, non-scientific E1 replay demo (zero network/model calls)."""
from __future__ import annotations
import json, sys
from pathlib import Path
from .core import EvolutionJournal

def work(id,mode,question,rationale,source_ids=None,problem_id='P0'):
    return {'id':id,'mode':mode,'question':question,'research_rationale':rationale,
            'source_ids':source_ids or [],'problem_id':problem_id}

def run(root):
    j=EvolutionJournal(root)
    j.init('DEMONSTRATION ONLY: A synthetic problem with two unverified competing mechanisms.',origin='SYNTHETIC_OFFLINE_DEMO')
    j.add_source('PRIMARY_1','PRIMARY',b'Invented synthetic starting data, not a real publication.','Synthetic mock source; not scientific evidence.')
    j.add_source('HUMAN_HOLDOUT','EXTERNAL_AUDIT',b'Hidden negative example, deliberately withheld from fresh contexts.','Synthetic independent audit holdout')
    # First contemporaneous research group, both FRESH.
    j.evolve('E_FRESH_A','FRESH',[],work('A','FRESH','Generate one causal candidate','Independent exploration',['PRIMARY_1']),'Program initialization chose independent A')
    j.evolve('E_FRESH_B','FRESH',[],work('B','FRESH','Generate a competing explanation','Independent exploration',['PRIMARY_1']),'Program initialization chose independent B')
    j.start('A');j.start('B')
    j.step('A','MODEL_RESPONSE',{'text':'Candidate H: hypothetical nonlinear coupling could affect intensity. This is an unverified fictional example.'})
    j.asset('H1','A','HYPOTHESIS','P0','Candidate H: fictional coupling modifies observed intensity',
            'Assumed synthetic coupling coefficient > 0','Invented simulator only',['intensity depends on coefficient'],
            ['No real data or novelty analysis'],source_ids=['PRIMARY_1'])
    # Launch child while B still ACTIVE: demonstrates non-barrier, event-driven scheduling.
    j.evolve('E_DEVELOP_A','DEVELOP',['H1'],work('A_PRIME','INFORMED','Check H1 under a restrictive regime','Hypothesis needs bounded scope'),'A interim H1 requires a constrained quantitative follow-up')
    j.start('A_PRIME')
    j.step('B','MODEL_RESPONSE',{'text':'Independent null N: same synthetic marginal can arise from additive noise.'})
    j.asset('N1','B','NULL_MODEL','P0','Null N: synthetic additive noise matches one marginal intensity statistic',
            'Synthetic additive noise','Single summary statistic only',['same mean intensity'],
            ['Cannot establish same time series'],source_ids=['PRIMARY_1'])
    j.finish('B','RETURN','Null candidate published; no claim of experimental refutation')
    # FUSE: two parents in a newly scheduled study, inputs explicitly frozen.
    j.evolve('E_FUSE','FUSE',['H1','N1'],work('FUSION','INFORMED','Compare H1 against null N1','Merge contradictory ideas as a testable rival'),'Both models predict identical mean but potentially different variance')
    j.start('FUSION')
    j.step('A_PRIME','MOCK_CALCULATION',{'input':'fixed synthetic constants','result':{'scope':'coefficient > 0.8'},'executed_by':'MOCK','science_verified':False})
    j.asset('H2','A_PRIME','HYPOTHESIS','P0','H holds only for synthetic coupling coefficient > 0.8',
            'Assumed threshold and toy constants','coefficient > 0.8',['above-threshold response'],
            ['Illustrative numbers not actual physics'],parent_ids=['H1'],delta_from_parents='Narrows unrestricted H1 to a conditional claim after synthetic work')
    j.finish('A_PRIME','RETURN','Synthetic claim restricted; awaiting independent review')
    j.step('FUSION','MODEL_RESPONSE',{'text':'Toy contrast proposes a variance discriminator, not verified.'})
    j.asset('F1','FUSION','PREDICTION','P0','Variance could distinguish synthetic H1 from N1 under fixed calibration',
            'Models have matched marginal means','Toy calibrated observation model',['variance response differs'],
            ['No Monte Carlo validation'],parent_ids=['H1','N1'],delta_from_parents='Fuses H1 and N1 into a conditional competing-prediction test')
    j.finish('FUSION','RETURN','Mock proposal, no validated scientific new result')
    j.finish('A','CONTINUE_IN_CHILD','Intermediate asset H1 continued by A_PRIME')
    j.append('ASSET_REVIEWED',{'id':'H1','decision':'CHALLENGED','rationale':'N1 is a competing synthetic explanation; not a disproof','reviewer_id':'DIRECTOR_1','source_ids':[]})
    j.append('PROGRAM_REVIEWED',{'reviewer_id':'DIRECTOR_1','scientific_status':'UNRESOLVED',
         'rationale':'Toy evolution completed, but neither simulation nor external scientific validation occurred',
         'considered_asset_ids':['H1','H2','N1','F1'],
         'unresolved_opportunities':['Validate variance statistic on actual data','Verify physical parameters']})
    return j.report()

def main():
    if len(sys.argv)!=2: raise SystemExit('usage: python -m e1core.demo NEW_DEMO_ROOT')
    output=run(sys.argv[1]); print(json.dumps({'root':output['root'],'status':'STRUCTURAL_MOCK_COMPLETE_NOT_SCIENTIFIC_DISCOVERY',
        'events':output['events'],'assets':list(output['assets']),'evolution':len(output['evolution']),
        'scientific_certification':False,'paid_calls':0},indent=2))
if __name__=='__main__':main()
