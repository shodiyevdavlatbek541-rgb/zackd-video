import subprocess,sys
import numpy as np
x=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',sys.argv[1],'-vn','-ac','1','-ar','16000','-f','f32le','-'],capture_output=True).stdout,np.float32)
h=160;db=np.array([10*np.log10(np.mean(x[i:i+400]**2)+1e-9) for i in range(0,len(x)-400,h)])
print('percentiles',[round(float(np.percentile(db,p)),1) for p in (2,10,25,50,90)])
for a,b in ((0,.6),(2.9,3.6),(5.1,5.9),(7.3,8.1),(9.6,10.3),(11.4,12.2),(14.6,15.7),(17.3,18.2)):
    s=db[int(a*100):int(b*100)];i=int(np.argmin(s))
    q=np.where(s<s[i]+6)[0]
    print(a,b,'min',round(float(s[i]),1),'at',round(a+i/100,2),'quiet',round(a+q[0]/100,2),round(a+q[-1]/100,2))
