import subprocess,sys
B,R,*jobs=sys.argv[sys.argv.index('--')+1:]
if jobs[0]=='cast':
    subprocess.run([B,'-b','-P',R+'/scripts/cast.py','--',R],stdout=open(R+'/cast3.log','w'),stderr=subprocess.STDOUT)
    jobs=jobs[1:]
subprocess.run([B,'-b','--factory-startup','-P',R+'/scripts/run.py','--',B,R,'still',*jobs])
print('##FIRST DONE',flush=True)
