"""Approved compact-header layout over static AI backgrounds; reads only this report's data."""
from pathlib import Path
from functools import lru_cache
import argparse,json,math,re
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps,ImageFilter,ImageEnhance
W,H=1080,1920
GOLD=(242,204,137,255);WHITE=(248,248,244,255);MUTED=(235,241,248,255);UP=(255,155,145,255);DOWN=(135,242,198,255)
@lru_cache(None)
def F(n):return ImageFont.truetype(FONT,n)
def fit_text(d,xy,value,size,width,color=WHITE):
 while size>22 and F(size).getlength(value)>width:size-=1
 if F(size).getlength(value)>width:raise ValueError('Text too long for card: '+value)
 text(d,xy,value,size,color)
def summary_rows(sl):
 visual=sl.get('visual',{})
 if 'rows' in visual:
  rows=visual['rows']
  if len(rows)>3 or any(len(r)!=3 for r in rows):raise ValueError('visual.rows must contain at most 3 [label,value,note] rows')
  return rows
 if sl['type']=='macro':
  groups=sl.get('groups',[]);rows=[]
  for title,gid,values in groups:
   if not values:continue
   v=values[0]
   rows.append((v[0],v[1],v[2] if len(v)>2 else title))
  return rows[:3]
 if sl['type']=='sentiment':
  verdict=sl.get('verdict',['','']);rows=[('市场判断',verdict[0],verdict[1])]
  for title,gid,values in sl.get('cols',[]):
   if values:rows.append((title,str(values[0][0])+' '+str(values[0][1]),str(values[0][2])))
  return rows[:3]
 if sl['type']=='outlook':
  return [(market,tag,'；'.join(notes)) for market,gid,tag,notes in sl.get('cards',[])[:3]]
 raise ValueError('Unsupported slide type: '+sl['type'])
def wrap(text,font,width):
 lines=[];line=''
 for c in text:
  if font.getlength(line+c)>width and line:lines.append(line);line=c
  else:line+=c
 if line:lines.append(line)
 return lines

def subtitle_lines(value,font,width):
 tokens=re.findall(r'标普500|沪深300|科创50|同步|创业板|恒指|恒科|美股|港股|[A-Za-z0-9.%+:/—-]+|.',value)
 total=font.getlength(value);count=max(1,math.ceil(total/width));target=total/count
 @lru_cache(None)
 def solve(start,left):
  if left==0:return (0,[]) if start==len(tokens) else (float('inf'),[])
  best=(float('inf'),[])
  for end in range(start+1,len(tokens)+1):
   line=''.join(tokens[start:end]);w=font.getlength(line)
   if w>width:break
   cost,rest=solve(end,left-1)
   candidate=cost+(w-target)**2
   if candidate<best[0]:best=(candidate,[line]+rest)
  return best
 cost,lines=solve(0,count)
 return lines if lines else wrap(value,font,width)

def text(d,xy,s,size,color=WHITE):d.text(xy,s,font=F(size),fill=color,stroke_width=1,stroke_fill=color)

def panel(d,box,active=False):
 d.rounded_rectangle(box,22,fill=(5,12,22,250),outline=GOLD if active else (194,213,226,125),width=3)

def overlay(item,index):
 si=item['slide'];sl=R['slides'][si];hi=set(sl['sentences'][item['idx']].get('hi',[]))
 # This is a new transparent editorial overlay; generated source images remain unchanged.
 alpha=np.zeros((H,W,4),dtype=np.uint8)
 for y in range(H):
  a=65 if y<700 else int(65+min(1,(y-700)/730)*170)
  if y<250:a=110
  alpha[y,:,0:3]=[5,13,24];alpha[y,:,3]=a
 im=Image.fromarray(alpha);d=ImageDraw.Draw(im)
 # Compact masthead: reserve the main canvas for market data.
 text(d,(64,52),R.get('title','股市早报'),34,GOLD)
 fit_text(d,(270,57),R.get('date_display',R['date']),30,440)
 d.rounded_rectangle((742,48,1016,98),24,fill=(3,10,20,240),outline=(255,255,255,90))
 fit_text(d,(766,58),R.get('visual',{}).get('badge','AI示意画面'),27,230)
 d.rounded_rectangle((42,130,1038,390),24,fill=(3,10,20,242))
 text(d,(64,152),f'{si+1:02d}  /  {LABELS[si]}',34,GOLD)
 headline=TITLES[si].replace('\n',' · ')
 title_size=70
 while F(title_size).getlength(headline)>926:title_size-=2
 text(d,(62,215),headline,title_size)
 d.rectangle((64,306,130,310),fill=GOLD)
 fit_text(d,(64,329),SUBS[si],34,930)

 if sl['type']=='intro':
  text(d,(64,488),'三大市场 · 收盘速览',42,GOLD)
  for j,(market,name,pct,direction) in enumerate(sl['chips']):
   top=565+j*190;panel(d,(64,top,1016,top+163),'chips' in hi)
   text(d,(90,top+24),market,52);fit_text(d,(244,top+27),name,48,360,MUTED)
   valfont=F(76);x=984-valfont.getlength(pct);text(d,(x,top+25),pct,76,UP if direction=='up' else DOWN)
  for k,(label,note) in enumerate(R.get('data_note',[])[:2]):
   fit_text(d,(68,1170+k*60),label+'：'+note,35,940,MUTED)
 elif sl['type']=='market':
  cards=sl['cards'];top=480;row=194 if len(cards)==4 else 238
  for j,(name,level,pct,direction) in enumerate(cards):
   yy=top+j*row;panel(d,(64,yy,1016,yy+row-22),f'c{j}' in hi)
   text(d,(88,yy+23),name,46,MUTED)
   text(d,(88,yy+88),level,66)
   col=UP if direction=='up' else DOWN
   text(d,(984-F(76).getlength(pct),yy+61),pct,76,col)
  bullet_rows=[''.join(str(p[0]) for p in line) for line in sl.get('bullets',[])]
  note=sl.get('visual',{}).get('note',' · '.join(bullet_rows[:2]))
  if note:fit_text(d,(68,top+len(cards)*row+24),note,36,940,GOLD)
 else:
  rows=summary_rows(sl)
  for j,(name,value,note) in enumerate(rows):
   yy=480+j*252;panel(d,(64,yy,1016,yy+222))
   fit_text(d,(90,yy+21),str(name),37,880,GOLD)
   fit_text(d,(90,yy+80),str(value),55,880)
   fit_text(d,(90,yy+166),str(note),36,880,MUTED)
 # Subtitle region is fixed below all data panels.
 d.rounded_rectangle((42,1500,1038,1775),24,fill=(2,7,14,255),outline=(255,255,255,145),width=2)
 lines=subtitle_lines(item['sub'],F(64),920)
 assert len(lines)<=3,(item['sub'],lines)
 yy=1523+(3-len(lines))*40
 for line in lines:
  xx=(W-F(64).getlength(line))/2;text(d,(xx,yy),line,64);yy+=81
 source=sl.get('src',R.get('default_src','')).replace('；详见文稿','')
 for j,line in enumerate(wrap(source,F(28),940)[:2]):text(d,(66,1790+j*35),line,28,MUTED)
 text(d,(66,1862),'AI生成示意画面  ·  仅供参考，不构成投资建议',27,MUTED)
 d.rectangle((64,1895,1016,1898),fill=(255,255,255,50))
 d.rectangle((64,1895,64+int(952*(index+1)/len(TL['items'])),1898),fill=GOLD)
 path=BUILD/f'overlay-{index:02d}.png';im.save(path)
 return path

def main():
 global R,TL,FONT,BUILD,TITLES,SUBS,LABELS
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('report_dir',type=Path);p.add_argument('--font',required=True);p.add_argument('--backgrounds',type=Path,required=True);a=p.parse_args()
 FONT=a.font;R=json.loads((a.report_dir/'report.json').read_text());TL=json.loads((a.report_dir/'build/timeline.json').read_text());BUILD=a.report_dir/'build/illustrated';BUILD.mkdir(parents=True,exist_ok=True)
 LABELS=[s.get('tab','开场') for s in R['slides']]
 TITLES=[s.get('visual',{}).get('headline',R.get('title','股市早报') if s['type']=='intro' else s.get('tab',s['type'])) for s in R['slides']]
 SUBS=[s.get('visual',{}).get('subtitle',s.get('asof','收盘数据速览')) for s in R['slides']]
 frames=[];fps=12
 for i,it in enumerate(TL['items']):
  sl=R['slides'][it['slide']];scene=sl.get('visual',{}).get('background')
  if not scene:scene={'美股':'us','A股':'china','港股':'hk'}.get(sl.get('tab'),'macro' if sl['type']=='macro' else 'global')
  if scene not in {'global','us','china','hk','macro'}:raise ValueError('Unknown background: '+scene)
  bg=ImageOps.fit(Image.open(a.backgrounds/(scene+'.jpg')).convert('RGB'),(720,1280),method=Image.Resampling.LANCZOS)
  bg=ImageEnhance.Color(bg.filter(ImageFilter.GaussianBlur(1.3))).enhance(.8)
  ov=Image.open(overlay(it,i)).convert('RGBA').resize((720,1280),Image.Resampling.LANCZOS)
  frame=Image.alpha_composite(bg.convert('RGBA'),ov).convert('RGB');path=BUILD/f'frame-{i:02d}.png';frame.save(path)
  start=0 if i==0 else round(it['start']*fps)/fps;end=round(it['show_end']*fps)/fps
  frames.append((path.resolve(),end-start))
 lines=[]
 for path,duration in frames:lines.extend(["file '"+str(path).replace("'", "'\\''")+"'",f'duration {duration:.9f}'])
 lines.append("file '"+str(frames[-1][0]).replace("'", "'\\''")+"'")
 (BUILD/'frames.txt').write_text('\n'.join(lines)+'\n')
 thumbs=[Image.open(frames[next(i for i,it in enumerate(TL['items']) if it['slide']==si)][0]).resize((180,320)) for si in range(len(R['slides']))]
 sheet=Image.new('RGB',(180*len(thumbs),320))
 for i,im in enumerate(thumbs):sheet.paste(im,(i*180,0))
 sheet.save(BUILD/'contact_sheet.jpg');print('Rendered',len(frames),'static frames',flush=True)
if __name__=='__main__':main()
