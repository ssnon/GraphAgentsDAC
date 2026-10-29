"""Fail-closed Linux namespace sandbox for model-authored science Python.

Threat model: model text is untrusted. Never execute it in this process or on the
host filesystem. Uses bubblewrap or Linux user+mount+network+PID namespace with
an independent mount tree and no host data mounts. Relies on kernel isolation;
not a defense against kernel privilege-escalation vulnerabilities.
"""
from __future__ import annotations
import hashlib, json, os, resource, shutil, subprocess, sys, tempfile, textwrap
from pathlib import Path

MAX_CODE_BYTES = 24000
MAX_DATA_BYTES = 100000
MAX_STDOUT_BYTES = 50000
MAX_RESULT_BYTES = 30000
MAX_WALL_SECONDS = 22
MAX_CPU_SECONDS = 18
MAX_MEMORY_BYTES = 3 * 1024**3

# Trusted bootstrap, not model-authored. stdout is a single framed JSON object.
BOOTSTRAP = r"""
import sys, json, io, contextlib, traceback, hashlib, resource
try:
    # Applied only after bwrap/unshare has established the sandbox.
    # Do NOT cap RLIMIT_NPROC in the host-side child before namespace creation:
    # on WSL, other processes/threads belonging to the host UID may already
    # exceed the sandbox budget and cause clone(2) to fail with EAGAIN.
    resource.setrlimit(resource.RLIMIT_NPROC, (48, 48))
    payload=json.loads(sys.stdin.read())
    code=payload['code']
    input_data=payload.get('data',{})
    ns={'__name__':'__science__','data':input_data}
    captured=io.StringIO()
    with contextlib.redirect_stdout(captured):
        exec(compile(code,'<model_scientific_code>','exec'),ns,ns)
    if 'result' not in ns:
        raise ValueError('Code must assign a JSON-serializable dictionary to result')
    if not isinstance(ns['result'],dict):
        raise TypeError('result must be a dict')
    result=json.dumps(ns['result'],allow_nan=False,ensure_ascii=False)
    if len(result.encode())>30000:
        raise ValueError('RESULT_TOO_LARGE')
    print(json.dumps({'status':'EXECUTED','result':ns['result'],
        'stdout_excerpt':captured.getvalue()[:4000],
        'code_sha256':hashlib.sha256(code.encode()).hexdigest()},allow_nan=False))
except BaseException as e:
    print(json.dumps({'status':'EXECUTION_FAILED','error_code':type(e).__name__,
        'detail':str(e)[:450]},ensure_ascii=False))
"""

UNSHARE_SCRIPT=r"""
set -euo pipefail
root="$1"; python_bin="$2"; bootstrap="$3"; shift 3
mount -t tmpfs -o size=96m,nosuid,nodev tmpfs "$root"
for path in "$@"; do
  [ -e "$path" ] || continue
  mkdir -p "$root$path"
  mount --rbind "$path" "$root$path"
  mount -o remount,bind,ro "$root$path"
done
# A fresh procfs is required by some NumPy/Intel oneMKL loaders.
# This mount occurs INSIDE the new user/mount/PID namespaces, never as a host bind.
mkdir -p "$root/proc" "$root/dev" "$root/tmp" "$root/work"
mount -t proc -o nosuid,nodev,noexec proc "$root/proc"
for device in null urandom; do
  touch "$root/dev/$device"
  mount --bind "/dev/$device" "$root/dev/$device"
  mount -o remount,bind,ro "$root/dev/$device"
done
cd /
exec chroot "$root" "$python_bin" -I -c "$bootstrap"
"""

def _paths():
    # Mount the interpreter environment itself READ-ONLY, never whole /home,
    # never the project repository. Handles conda on WSL, where sys.prefix is
    # typically /home/<user>/miniconda3/envs/<env>.
    base=['/usr','/bin','/lib','/lib64']
    prefix=str(Path(sys.prefix).resolve())
    if prefix not in ('/', '/home', '/root', '/mnt', '/opt', '/usr'):
        if prefix.startswith('/opt/') or prefix.startswith('/home/') or prefix.startswith('/mnt/'):
            # Refuse broad homes, e.g. /home/user as a Python prefix.
            parts=Path(prefix).parts
            if not (len(parts)<=3 and parts[1]=='home'):
                base.append(prefix)
    for path in sys.path:
        if not isinstance(path,str) or not path.startswith('/'):continue
        p=Path(path)
        if not p.exists() or not p.is_dir():continue
        if str(p).startswith('/opt/'):
            base.append(str(p))
        # Non-prefix user-home imports are intentionally not mounted.
    paths=sorted(set(p for p in base if os.path.exists(p)),key=len)
    return [p for i,p in enumerate(paths)
            if not any(p.startswith(other.rstrip('/')+'/') for other in paths[:i])]

def sandbox_backend():
    if os.name!='posix' or sys.platform!='linux':return None
    if shutil.which('bwrap'):return 'bubblewrap'
    if shutil.which('unshare') and shutil.which('mount') and shutil.which('chroot'):
        return 'linux-user-namespace'
    return None

def _limits(cpu_seconds=MAX_CPU_SECONDS):
    resource.setrlimit(resource.RLIMIT_CPU,(cpu_seconds,cpu_seconds+2))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024*1024,2*1024*1024))
    resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
    # NPROC is deliberately set inside BOOTSTRAP, after namespace setup.
    resource.setrlimit(resource.RLIMIT_AS,(MAX_MEMORY_BYTES,MAX_MEMORY_BYTES))

def _command(root,backend):
    paths=_paths()
    if backend=='linux-user-namespace':
        return ['unshare','--user','--map-root-user','--mount','--pid','--net','--ipc','--uts',
           '--fork','bash','-c',UNSHARE_SCRIPT,'--',str(root),sys.executable,BOOTSTRAP,*paths]
    if backend=='bubblewrap':
        args=['bwrap','--unshare-all','--die-with-parent','--new-session','--clearenv']
        for key,val in _environment().items():args+=['--setenv',key,val]
        dirs={'/dev','/tmp'}
        for path in paths:
            for par in Path(path).parents:
                if str(par)!='/':dirs.add(str(par))
        for d in sorted(dirs,key=lambda x:(x.count('/'),x)):
            args+=['--dir',d]
        for path in paths:args+=['--ro-bind',path,path]
        args+=['--dev-bind','/dev/null','/dev/null','--dev-bind','/dev/urandom','/dev/urandom']
        # --unshare-all includes a PID namespace. Create new procfs for THAT
        # namespace, NOT a bind of the host's /proc. Required by Intel oneMKL
        # on the user's WSL / Conda setup (diagnosed by differential probe).
        args+=['--proc','/proc']
        args+=['--tmpfs','/tmp','--chdir','/tmp','--',sys.executable,'-I','-c',BOOTSTRAP]
        return args
    raise RuntimeError('NO_OS_SANDBOX_AVAILABLE')

def _loader_dirs():
    # Do NOT import LD_LIBRARY_PATH from the parent: it may contain paths that
    # are not isolated/read-only. Only interpreter-prefix libraries are allowed.
    # Conda MKL can dlopen additional libmkl_*.so after NumPy's extension loads;
    # DT_RUNPATH is not inherited by dlopen dependencies on all setups.
    mounted=_paths()
    result=[]
    for prefix in (sys.prefix,sys.exec_prefix):
        if not isinstance(prefix,str) or not prefix.startswith('/'):
            continue
        lib=Path(prefix)/'lib'
        if not lib.is_dir():continue
        path=str(lib.resolve())
        if any(path==m or path.startswith(m.rstrip('/')+'/') for m in mounted):
            if path not in result:result.append(path)
    return result

def _environment():
    env={'PATH':'/usr/sbin:/usr/bin:/bin','HOME':'/tmp','TMPDIR':'/tmp','PYTHONNOUSERSITE':'1',
      'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
      'NUMEXPR_NUM_THREADS':'1','MPLCONFIGDIR':'/tmp/matplotlib'}
    dirs=_loader_dirs()
    if dirs:
        env['LD_LIBRARY_PATH']=':'.join(dirs)
    return env

def run_science_python(args,backend=None,*,cpu_seconds=MAX_CPU_SECONDS,wall_seconds=MAX_WALL_SECONDS):
    # Bounded operator-selected limits; never accept timing from model-authored code.
    # Keep original behavior unless explicitly overridden from trusted CLI.
    if type(cpu_seconds) is not int or type(wall_seconds) is not int or not (1<=cpu_seconds<=240 and cpu_seconds+4<=wall_seconds<=300):
        return {'status':'REJECTED','error_code':'INVALID_SANDBOX_TIME_LIMITS'}
    if not isinstance(args,dict):return {'status':'REJECTED','error_code':'INVALID_ARGUMENTS'}
    code=args.get('code')
    if not isinstance(code,str) or not code.strip():
        return {'status':'REJECTED','error_code':'PYTHON_CODE_REQUIRED'}
    if len(code.encode('utf-8'))>MAX_CODE_BYTES:
        return {'status':'REJECTED','error_code':'CODE_SIZE_LIMIT'}
    data=args.get('data',{})
    try:encoded=json.dumps(data,allow_nan=False)
    except (TypeError,ValueError):return {'status':'REJECTED','error_code':'INVALID_INPUT_DATA'}
    if len(encoded.encode())>MAX_DATA_BYTES:
        return {'status':'REJECTED','error_code':'INPUT_DATA_SIZE_LIMIT'}
    chosen=backend if backend is not None else sandbox_backend()
    if chosen not in ('bubblewrap','linux-user-namespace'):
        return {'status':'REJECTED','error_code':'NO_STRONG_LINUX_SANDBOX',
          'detail':'Install bubblewrap or enable unprivileged Linux user+mount+network namespaces; no unsafe fallback.'}
    payload=json.dumps({'code':code,'data':data},ensure_ascii=False,allow_nan=False).encode()
    with tempfile.TemporaryDirectory(prefix='g5c_namespace_') as directory:
        try:
            p=subprocess.run(_command(Path(directory),chosen),input=payload,
               stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=wall_seconds,
               env=_environment(),preexec_fn=lambda: _limits(cpu_seconds),check=False)
        except subprocess.TimeoutExpired:
            return {'status':'EXECUTION_FAILED','error_code':'SANDBOX_TIMEOUT',
                'sandbox_backend':chosen,'code_sha256':hashlib.sha256(code.encode()).hexdigest()}
        except (OSError,ValueError) as e:
            return {'status':'REJECTED','error_code':'SANDBOX_START_FAILED','detail':str(e)[:200]}
    if len(p.stdout)>MAX_STDOUT_BYTES:
        return {'status':'EXECUTION_FAILED','error_code':'OUTPUT_LIMIT'}
    try:out=json.loads(p.stdout.decode('utf-8'))
    except (ValueError,UnicodeDecodeError):
        # Some bwrap versions relay SIGXCPU from the child as 128+SIGXCPU.
        # This is a probable (not independently confirmed) CPU-limit failure.
        cpu_limit_suspected=(p.returncode==152)
        return {'status':'REJECTED','error_code':'CPU_TIME_LIMIT_SUSPECTED' if cpu_limit_suspected else 'SANDBOX_UNAVAILABLE_OR_CRASHED',
            'stderr_excerpt':p.stderr.decode('utf-8','replace')[:450],
            'exit_code':p.returncode,'sandbox_backend':chosen,
            'limits':{'cpu_seconds':cpu_seconds,'wall_seconds':wall_seconds}}
    out['sandbox_backend']=chosen
    out['code_sha256']=hashlib.sha256(code.encode()).hexdigest()
    out['exit_code']=p.returncode
    out['limits']={'wall_seconds':wall_seconds,'cpu_seconds':cpu_seconds,
                   'address_space_bytes':MAX_MEMORY_BYTES,'network':'unshared','filesystem':'chrooted_ro_runtime_tmpfs_fresh_pid_procfs'}
    if p.returncode!=0:out['status']='EXECUTION_FAILED';out['error_code']='SANDBOX_NONZERO_EXIT'
    return out
