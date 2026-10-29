"""Deterministic, unit-explicit arithmetic and locally pinned source evidence.
No Python eval, no guessed sources, no scientific certification.
"""
import ast, hashlib, json, math, pathlib, re

class ScienceInputError(ValueError): pass
FUNCS={'sqrt':math.sqrt,'exp':math.exp,'log':math.log,'log10':math.log10,'sin':math.sin,'cos':math.cos,'abs':abs,'min':min,'max':max}
CONSTANTS={'pi':math.pi,'e':math.e,'k_B_J_K':1.380649e-23,'k_B_eV_K':8.617333262145e-5}

def finite(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(float(v)) or abs(v)>1e100:raise ScienceInputError('NONFINITE_OR_UNSAFE_NUMBER')
    return float(v)

def evaluate(expr,variables):
    if not isinstance(expr,str) or not 1<=len(expr)<=240:raise ScienceInputError('INVALID_EXPRESSION_LENGTH')
    if not isinstance(variables,dict) or len(variables)>24:raise ScienceInputError('INVALID_VARIABLES')
    names=dict(CONSTANTS)
    for k,v in variables.items():
        if not isinstance(k,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,45}',k) or k in FUNCS or k in CONSTANTS:
            raise ScienceInputError('INVALID_VARIABLE_NAME')
        names[k]=finite(v)
    try:node=ast.parse(expr,mode='eval')
    except SyntaxError:raise ScienceInputError('INVALID_EXPRESSION_SYNTAX')
    if sum(1 for _ in ast.walk(node))>65:raise ScienceInputError('EXPRESSION_TOO_COMPLEX')
    def calc(n,depth=0):
        if depth>16:raise ScienceInputError('TOO_DEEP')
        if isinstance(n,ast.Expression):return calc(n.body,depth+1)
        if isinstance(n,ast.Constant):return finite(n.value)
        if isinstance(n,ast.Name):
            if n.id not in names:raise ScienceInputError('UNKNOWN_VARIABLE:'+n.id)
            return names[n.id]
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            x=calc(n.operand,depth+1);return finite(x if isinstance(n.op,ast.UAdd) else -x)
        if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow)):
            a,b=calc(n.left,depth+1),calc(n.right,depth+1)
            if isinstance(n.op,ast.Pow):
                if abs(b)>24 or (abs(a)>1e25 and abs(b)>4):raise ScienceInputError('UNSAFE_EXPONENT')
                val=a**b
            elif isinstance(n.op,ast.Add):val=a+b
            elif isinstance(n.op,ast.Sub):val=a-b
            elif isinstance(n.op,ast.Mult):val=a*b
            else:val=a/b
            return finite(val)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in FUNCS and not n.keywords and 1<=len(n.args)<=4:
            return finite(FUNCS[n.func.id](*(calc(arg,depth+1) for arg in n.args)))
        raise ScienceInputError('DISALLOWED_SYNTAX')
    try:return calc(node)
    except (ArithmeticError,OverflowError,TypeError,ValueError) as exc:
        if isinstance(exc,ScienceInputError):raise
        raise ScienceInputError('UNDEFINED_NUMERIC_OPERATION')

def verify_calculation(args):
    """Compare user-supplied candidate/null formulas over explicit parameter scenarios.
    Caller owns assumptions and unit semantics; arithmetic is independently computed.
    """
    if not isinstance(args,dict):raise ScienceInputError('ARGUMENTS_NOT_OBJECT')
    expr=args.get('expressions'); scenarios=args.get('scenarios'); units=args.get('units',{})
    if not isinstance(expr,dict) or not 1<=len(expr)<=8 or not isinstance(scenarios,list) or not 1<=len(scenarios)<=16:
        raise ScienceInputError('EXPRESSIONS_AND_SCENARIOS_REQUIRED')
    if not isinstance(units,dict) or set(units)-set(expr):raise ScienceInputError('INVALID_UNITS')
    for k,s in expr.items():
        if not isinstance(k,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,40}',k):raise ScienceInputError('INVALID_FORMULA_NAME')
        if not isinstance(s,str):raise ScienceInputError('FORMULA_NOT_STRING')
    rows=[]
    for i,scenario in enumerate(scenarios):
        if not isinstance(scenario,dict):raise ScienceInputError('INVALID_SCENARIO')
        # P6L: 'name' is display metadata, not a numerical input. P6 rejected
        # 17/18 C001 calls because natural-language scenario labels were strings.
        label=scenario.get('name')
        if label is not None and (not isinstance(label,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. -]{0,79}',label)):
            raise ScienceInputError('INVALID_SCENARIO_NAME')
        numeric={k:finite(value) for k,value in scenario.items() if k!='name'}
        vals={k:evaluate(s,numeric) for k,s in expr.items()}
        row={'scenario_index':i,'variables':numeric,'computed':vals}
        if label is not None:row['scenario_name']=label
        rows.append(row)
    sig=hashlib.sha256(json.dumps(args,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return {'status':'VERIFIED_NUMERIC_ARITHMETIC','source':'P6_LOCAL_SAFE_AST','model_input_sha256':sig,
            'results':rows,'units':units,'scope':'Only arithmetic under caller-provided formulas/parameters. No physical validity, identifiability, prior-art, or novelty certification.'}

def read_paper(root,args):
    if not isinstance(args,dict) or args.get('doc_id')!='YE_2025_PRB_075428':return {'status':'REJECTED','error_code':'UNKNOWN_PRIMARY_DOCUMENT'}
    p=pathlib.Path(root)/'P6_PRIMARY.json';data=json.loads(p.read_text('utf8'))
    if data['status']!='USER_SUPPLIED_TEXT_UNVERIFIED':
        return {'status':'ABSTRACT_ONLY','doi':'10.1103/4yg7-1f85','url':'https://doi.org/10.1103/4yg7-1f85',
                'coverage':'PUBLIC_ABSTRACT_AND_METADATA_ONLY','full_text_confirmed':False,
                'note':'Do not infer authors\' two proposed mechanisms or experimental controls from abstract.'}
    start=args.get('start_line',1);count=args.get('max_lines',40)
    if type(start)!=int or type(count)!=int or not 1<=count<=100 or start<1:raise ScienceInputError('INVALID_SOURCE_RANGE')
    lines=data['lines'];end=min(len(lines),start+count-1)
    if start>len(lines):raise ScienceInputError('SOURCE_RANGE_OUTSIDE_DOCUMENT')
    out=[{'line':i,'text':lines[i-1]} for i in range(start,end+1)]
    if len(json.dumps(out))>90000:raise ScienceInputError('SOURCE_EXCERPT_TOO_LONG')
    return {'status':'USER_SUPPLIED_DOCUMENT_EXCERPT','doc_id':args['doc_id'],'start_line':start,
            'end_line':end,'total_lines':len(lines),'lines':out,'text_sha256':data['text_sha256'],
            'provenance':'USER_SUPPLIED_TEXT_UNVERIFIED_NOT_INDEPENDENTLY_AUTHENTICATED',
            'scope':'Citation anchors are lines in supplied text, not verified journal page numbers.'}

def read_prior(root,args):
    if not isinstance(args,dict) or not isinstance(args.get('refs'),list) or not 1<=len(args['refs'])<=4:
        raise ScienceInputError('INVALID_PRIOR_REF_LIST')
    record=json.loads((pathlib.Path(root)/'P6_PRIOR.json').read_text('utf8'))
    idx={x['ref']:x for x in record['records']}
    rows=[]
    for ref in args['refs']:
        if ref not in idx:raise ScienceInputError('UNKNOWN_PRIOR_REF')
        d=idx[ref];rows.append({'ref':ref,'science':d['science'],'tool_result':d.get('tool_result'),
            'status':'PRIOR_AI_OUTPUT_NOT_INDEPENDENTLY_CERTIFIED'})
    if len(json.dumps(rows,ensure_ascii=False))>90000:raise ScienceInputError('PRIOR_EXCERPT_TOO_LONG')
    return {'status':'PRIOR_AI_EVIDENCE_DELIVERED','records':rows,'provenance':'P5R_USER_REVIEW_EXPORT_UNCERTIFIED'}
