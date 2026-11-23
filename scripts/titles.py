"""Subtitles (ZackD style: short white bold phrases) and the quiz layer, as ASS."""
import sys
ROOT = sys.argv[1]

def ts(t):
    c = round(t * 100)
    return f'0:{c // 6000:02d}:{c // 100 % 60:02d}.{c % 100:02d}'

SUBS = [(0.15, 0.96, '62 yoshli'), (0.96, 1.42, 'erkakni'), (1.42, 1.96, 'tez yordam'), (1.96, 2.72, 'reanimatsiyaga'), (2.72, 3.32, 'olib keldi.'),
        (3.42, 4.10, 'Bir soat oldin'), (4.10, 4.62, 'choy ichib'), (4.62, 5.55, 'o‘tirgan ekan,'),
        (5.76, 6.06, 'birdan'), (6.06, 6.86, 'qo‘lidagi piyola'), (6.86, 7.65, 'tushib ketibdi.'),
        (7.96, 8.94, 'Yuzining o‘ng tomoni'), (8.94, 9.95, 'qiyshayib qolgan,'),
        (10.15, 10.70, 'o‘ng qo‘lini'), (10.70, 11.75, 'ko‘tara olmayapti.'),
        (12.06, 13.06, 'Gapirmoqchi bo‘ladi,'), (13.06, 13.74, 'lekin so‘zlari'), (13.74, 14.85, 'tushunarsiz chiqyapti.'),
        (15.60, 16.42, 'Shifokor sifatida'), (16.42, 17.75, 'eng birinchi nima qilasiz?')]

L = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1080', 'PlayResY: 1920', 'WrapStyle: 2', '',
     '[V4+ Styles]',
     'Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding',
     'Style: Sub,Segoe UI Black,78,&H00FFFFFF,&H00FFFFFF,&H00101010,&H70000000,0,0,0,0,100,100,0,0,1,4,1,5,40,40,0,1',
     'Style: Q,Segoe UI Black,68,&H00FFFFFF,&H00FFFFFF,&H00101010,&H70000000,0,0,0,0,100,100,0,0,1,3,1,5,40,40,0,1',
     'Style: Opt,Segoe UI,56,&H00201810,&H00201810,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,4,0,0,0,1',
     'Style: Letter,Segoe UI Black,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1',
     'Style: Box,Arial,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1',
     '', '[Events]', 'Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text']

def line(layer, a, b, style, tags, body):
    L.append(f'Dialogue: {layer},{ts(a)},{ts(b)},{style},,0,0,0,,' + '{' + tags + '}' + body)

def rounded(w, h, r):
    return (f'm {r} 0 l {w-r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h-r} b {w} {h} {w} {h} {w-r} {h} '
            f'l {r} {h} b 0 {h} 0 {h} 0 {h-r} l 0 {r} b 0 0 0 0 {r} 0')

for a, b, body in SUBS:
    line(2, a, b, 'Sub', r'\pos(540,1500)\fscx92\fscy92\t(0,90,\fscx100\fscy100)', body)

END = 26.0
line(2, 17.82, END, 'Q', r'\pos(540,350)\fad(180,0)', r'Shifokor sifatida\Neng birinchi nima qilasiz?')
OPTS = [('A', 'Darhol aspirin beraman'), ('B', 'Qon bosimini tez tushiraman'),
        ('C', 'Kontrastsiz KT qildiraman'), ('D', r'Darhol trombni eritadigan\Ndori yuboraman')]
W, H, X0 = 960, 180, 60
for i, (letter, body) in enumerate(OPTS):
    y = 520 + i * 218; t = 18.0 + i * .3
    move = rf'\move({X0},{y + 40},{X0},{y},0,160)\fad(120,0)'
    line(0, t, END, 'Box', move + r'\p1\1c&HFFFFFF&\1a&H0C&', rounded(W, H, 38))
    bx, by = X0 + 22, y + 22
    # all four badges share one colour so the layout does not hint at the answer
    line(1, t, END, 'Box', rf'\move({bx},{by + 40},{bx},{by},0,160)\fad(120,0)\p1\1c&HB4641E&', rounded(136, 136, 30))
    line(2, t, END, 'Letter', rf'\move({bx + 68},{by + 106},{bx + 68},{by + 66},0,160)\fad(120,0)', letter)
    line(2, t, END, 'Opt', rf'\move({X0 + 188},{y + H // 2 + 40},{X0 + 188},{y + H // 2},0,160)\fad(120,0)', body)
line(2, 19.35, END, 'Q', r'\pos(540,1530)\fs62\1c&H4DE1FF&\fad(180,0)', r'Javobingizni\Nkommentariyada yozing.')

open(ROOT + '/titles.ass', 'w', encoding='utf-8-sig').write('\n'.join(L) + '\n')
print('titles ok', len(L))
