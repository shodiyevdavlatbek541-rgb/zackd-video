import sys
p=sys.argv[1]+'/scripts/audio.py';s=open(p,encoding='utf8').read()
s=s.replace("np.where(hot > .89, np.maximum(0, (.89 - ","np.where(hot > .80, np.maximum(0, (.80 - ")
s=s.replace("bed *= np.convolve(over, np.ones(96) / 96, 'same')[:, None]","over = np.lib.stride_tricks.sliding_window_view(np.pad(over, 120, mode='edge'), 241).min(1)\nbed *= np.convolve(over, np.ones(120) / 120, 'same')[:, None]")
open(p,'w',encoding='utf8').write(s)
