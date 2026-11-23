import subprocess, sys, re, wave
import numpy as np
R=sys.argv[1]; V=R+'/Insult_case_v3.mp4'
raw=subprocess.run(['ffmpeg','-v','error','-i',V,'-vf','scale=54:96','-f','rawvideo','-pix_fmt','gray','-'],capture_output=True).stdout
f=np.frombuffer(raw,np.uint8).reshape(-1,96,54).astype(float); d=np.abs(np.diff(f,axis=0)).mean((1,2))
print('frames',len(f))
for c in (53,100,172,213,234,303,359,455,494,533):
    a=max(0,c-5); print('cut plan',c,'found',a+int(np.argmax(d[a:c+5]))+1,'t=%.3f'%(c/30))
out=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',V,'-vn','-ac','2','-ar','48000','-f','f32le','-'],capture_output=True).stdout,np.float32).reshape(-1,2).astype(float)
def rd(n):
    w=wave.open(f'{R}/{n}.wav','rb'); return np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,2)/32768
v,b=rd('voice'),rd('bed'); n=min(len(out),len(v)); e=(out[:n]-b[:n]).mean(1); r=v[:n].mean(1); best=[]
for lag in range(-96,97,4):
    x=e[max(0,lag):len(e)+min(0,lag)]; y=r[max(0,-lag):len(r)+min(0,-lag)]
    best.append((np.corrcoef(x,y)[0,1],lag/48))
c,l=max(best); print('voice correlation %.4f offset %.2f ms'%(c,l))
