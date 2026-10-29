"""E2 CLI; only --paid AND explicit environment approval can access API."""
import argparse,json,pathlib,sys,os,fcntl
from .core import EvolutionJournal, EvidenceError
from .importer import validated_review,make_catalog,seed_e2
from .provider import DurableModel
from .engine import Engine

DEFAULT_REVIEW=pathlib.Path(__file__).resolve().parent.parent/'evidence'/'P6L_PORTFOLIO_REVIEW.json'

def main(argv=None):
    ap=argparse.ArgumentParser(prog='python -m e2core.cli')
    sub=ap.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('catalog');a.add_argument('--review',default=str(DEFAULT_REVIEW));a.add_argument('--out',required=True)
    a=sub.add_parser('init');a.add_argument('--root',required=True);a.add_argument('--review',default=str(DEFAULT_REVIEW));a.add_argument('--no-seeds',action='store_true');a.add_argument('--problem-file')
    a=sub.add_parser('recover-e2-r1');a.add_argument('--source-root',required=True);a.add_argument('--new-root',required=True)
    a=sub.add_parser('revalidate-r2-controller');a.add_argument('--source-root',required=True);a.add_argument('--new-root',required=True)
    a=sub.add_parser('verify');a.add_argument('--root',required=True)
    a=sub.add_parser('science-report');a.add_argument('--root',required=True);a.add_argument('--out',required=True)
    a=sub.add_parser('preflight');a.add_argument('--no-sandbox',action='store_true')
    a=sub.add_parser('run');a.add_argument('--root',required=True);a.add_argument('--paid',action='store_true');a.add_argument('--max-new-calls',type=int,default=6);
    a.add_argument('--max-iterations',type=int,default=6);a.add_argument('--max-parallel',type=int,default=3);a.add_argument('--serial-fair',action='store_true',help='Execute one worker at a time, fair scheduling, return tool feedback before controller');a.add_argument('--science-cpu-seconds',type=int,default=18);a.add_argument('--science-wall-seconds',type=int,default=22);a.add_argument('--model',default='openai/gpt-5.6-luna');a.add_argument('--max-tokens',type=int,default=7000)
    a=sub.add_parser('demo');a.add_argument('--root',required=True)
    ns=ap.parse_args(argv)
    if ns.cmd=='catalog':
        out=pathlib.Path(ns.out);out.parent.mkdir(parents=True,exist_ok=True)
        if out.exists():raise SystemExit('NO_OVERWRITE_CATALOG')
        out.write_text(json.dumps(make_catalog(ns.review),indent=2,ensure_ascii=False))
        print(json.dumps({'status':'ALL_115_CATALOG_VALIDATED','out':str(out),'steps':115}));return
    if ns.cmd=='preflight':
        from .science_sandbox import run_science_python,sandbox_backend
        out={'sandbox_backend':sandbox_backend(),'science_certification':False,'paid_calls':0}
        if not ns.no_sandbox:out['smoke']=run_science_python({'code':'result={"finite_arithmetic":2+3,"validated":True}'})
        print(json.dumps(out,ensure_ascii=False,indent=2));return
    if ns.cmd=='demo':
        from .mock import run_demo
        print(json.dumps(run_demo(ns.root),ensure_ascii=False,indent=2));return
    if ns.cmd=='recover-e2-r1':
        from .recovery import fork_recover
        print(json.dumps(fork_recover(ns.source_root,ns.new_root),ensure_ascii=False,indent=2));return
    if ns.cmd=='revalidate-r2-controller':
        from .r3_revalidation import fork_revalidate_r2_controller
        print(json.dumps(fork_revalidate_r2_controller(ns.source_root,ns.new_root),ensure_ascii=False,indent=2));return
    j=EvolutionJournal(ns.root)
    if ns.cmd=='init':
        if ns.problem_file and not ns.no_seeds:raise SystemExit('GENERIC_NEW_PROBLEM_MUST_USE_NO_SEEDS_TO_AVOID_SERS_LEAK')
        if ns.problem_file:
            goal=pathlib.Path(ns.problem_file).read_text(encoding='utf-8').strip()
            if not goal or len(goal)>12000:raise SystemExit('INVALID_PROBLEM_FILE')
        else:
            goal='Discover and develop evidence-grounded explanations and review-worthy new scientific hypotheses for SERS intermittency, preserving scoped negative results and unresolved questions.'
        source_sha=None if ns.no_seeds else validated_review(ns.review)[1]
        j.init(goal,origin='NEW_GENERIC_PROBLEM' if ns.problem_file else 'HUMAN_REQUESTED_POST_P6L_SCIENTIFIC_HOLD_NEW_E2_ROOT',criteria='Pre-experiment reviewable hypothesis or justified scoped negative result, not automatic experimental proof')
        result={'count':0} if ns.no_seeds else seed_e2(j,ns.review)
        print(json.dumps({'status':'NEW_E2_ROOT_INITIALIZED_NO_PAID','root':ns.root,'review_sha256':source_sha,'seeds':result['count'],'events':j.report()['events'],'original_P6L_root_unchanged':True},indent=2));return
    if ns.cmd=='science-report':
        out=pathlib.Path(ns.out)
        if out.exists():raise SystemExit('NO_OVERWRITE_REPORT')
        r=j.report();out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps({'status':'READ_ONLY_REPORT_CREATED','out':str(out),'events':r['events'],'assets':len(r['assets']),'model_calls':len(r['model_calls'])}));return
    if ns.cmd=='verify':
        r=j.report();print(json.dumps({'status':'E2_JOURNAL_REPLAY_VERIFIED','events':r['events'],'sources':len(r['sources']),'assets':len(r['assets']),
            'works':len(r['work']),'model_calls':len(r['model_calls']),'controller_decisions':len(r['controller_decisions']),
            'science_certification':False,'root':r['root']},indent=2));return
    if ns.cmd=='run':
        if not ns.paid or os.getenv('FAKG_RESEARCH_ALLOW_PAID')!='YES':raise SystemExit('EXPLICIT_PAID_APPROVAL_REQUIRED_BOTH_FLAG_AND_ENV')
        if ns.max_new_calls<1 or ns.max_iterations<1 or ns.max_parallel<1 or ns.max_tokens<500:raise SystemExit('INVALID_RESOURCE_BOUNDS')
        if ns.serial_fair and ns.max_parallel!=1:raise SystemExit('SERIAL_FAIR_REQUIRES_MAX_PARALLEL_ONE')
        if not (1<=ns.science_cpu_seconds<=240 and ns.science_cpu_seconds+4<=ns.science_wall_seconds<=300):raise SystemExit('INVALID_SANDBOX_TIME_LIMITS')
        if (ns.science_cpu_seconds!=18 or ns.science_wall_seconds!=22) and not ns.serial_fair:raise SystemExit('LONG_SCIENCE_COMPUTE_REQUIRES_SERIAL_FAIR')
        # A separate process cannot mutate this root concurrently: lock is advisory for CLI.
        lock=j.root/'.e2run.lock'
        with open(lock,'a+b') as f:
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise SystemExit('ANOTHER_E2_RUN_IS_ACTIVE')
            gateway=DurableModel(j,approved=True,max_new_calls=ns.max_new_calls,model=ns.model,max_tokens=ns.max_tokens)
            engine=Engine(j,gateway,serial_fair=ns.serial_fair,science_cpu_seconds=ns.science_cpu_seconds,science_wall_seconds=ns.science_wall_seconds)
            out=engine.run(max_iterations=ns.max_iterations,max_parallel=ns.max_parallel)
            out['journal_events']=j.report()['events'];print(json.dumps(out,ensure_ascii=False,indent=2))
        return
if __name__=='__main__':main()
