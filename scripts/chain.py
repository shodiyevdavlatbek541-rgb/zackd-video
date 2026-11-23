"""Run several blender jobs one after another. usage: blender -b -P chain.py -- BLENDER LOG1 'args1' LOG2 'args2' ..."""
import subprocess, sys, shlex
A = sys.argv[sys.argv.index('--') + 1:]
B = A[0]
for log, args in zip(A[1::2], A[2::2]):
    code = subprocess.run([B, '-b', '--factory-startup', *shlex.split(args)], stdout=open(log, 'w'), stderr=subprocess.STDOUT,
                          creationflags=0x08000000).returncode
    print('##JOB', log, code, flush=True)
    if code: break
print('##CHAIN DONE', flush=True)
