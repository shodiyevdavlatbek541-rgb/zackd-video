"""Runs shots one after another. usage: blender -b -P run.py -- BLENDER ROOT MODE [shot=times ...]"""
import subprocess, sys
B, R, MODE, *jobs = sys.argv[sys.argv.index('--') + 1:]
for j in jobs:
    shot, _, times = j.partition('=')
    cmd = [B, '-b', '--factory-startup', '--disable-autoexec', R + '/cast.blend', '-P', R + '/scripts/shots.py', '--', R, shot, MODE]
    if times: cmd.append(times)
    print('##START', shot, flush=True)
    code = subprocess.run(cmd, stdout=open(f'{R}/logs_{MODE}_{shot}.txt', 'w'), stderr=subprocess.STDOUT, creationflags=0x08000000).returncode
    print('##END', shot, code, flush=True)
print('##RUN DONE', flush=True)
