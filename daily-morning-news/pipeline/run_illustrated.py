#!/usr/bin/env python3
"""Build a static illustrated 720p morning-news video, strictly smaller than 3,000,000 bytes."""
import argparse,json,math,os,shutil,subprocess,sys
from pathlib import Path

def run(cmd):subprocess.run([str(x) for x in cmd],check=True)
def probe(path):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,r_frame_rate,bit_rate','-of','json',str(path)]))
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('report_dir',type=Path);p.add_argument('--models',type=Path,required=True);p.add_argument('--font',type=Path,required=True)
 p.add_argument('--backgrounds',type=Path)
 p.add_argument('--skip-intro',action='store_true',help='Illustrated mode already has no separate intro')
 p.add_argument('--skip-bgm',action='store_true')
 a=p.parse_args();here=Path(__file__).resolve().parent;pipe=here;root=here;d=a.report_dir.resolve()
 if list(d.glob('morning_news_*.mp4')):p.error('Existing video: use a separate candidate directory; do not overwrite')
 required=[d/'report.json',d/'script.md',a.font,a.models/'kokoro-multi-lang-v1_1/model.onnx',a.models/'kokoro-multi-lang-v1_1/voices.bin']
 for f in required:
  if not f.is_file():p.error('Missing file: '+str(f))
 for tool in ['ffmpeg','ffprobe']:
  if not shutil.which(tool):p.error('Missing executable: '+tool)
 backgrounds=a.backgrounds or root/'assets/backgrounds'
 for name in ['global','us','china','hk','macro']:
  if not (backgrounds/(name+'.jpg')).is_file():p.error('Missing background: '+name)
 run([sys.executable,here.parents[1]/'.claude/skills/daily-morning-news/scripts/check_report.py',d]);run([sys.executable,pipe/'lint_say.py',d/'report.json',a.models,'--engine=kokoro','--strict'])
 run([sys.executable,pipe/'synth.py',d,a.models,'--engine','kokoro','--sid','3','--speed','1.0']);tl=json.loads((d/'build/timeline.json').read_text());duration=round(tl['total']*12)/12
 if not 0<duration<=190:raise ValueError(f'Video duration {duration:.2f}s outside 0–190s; shorten the script')
 run([sys.executable,pipe/'render_illustrated.py',d,'--font',a.font,'--backgrounds',backgrounds])
 build=d/'build/illustrated';audio=build/'mixed.wav';narr=d/'build/narration.wav';bgm=pipe/'assets/bgm.mp3'
 if a.skip_bgm:shutil.copy2(narr,audio)
 else:
  mix=f'[0:a]aresample=44100,aformat=channel_layouts=mono,asplit[n1][n2];[1:a]aresample=44100,aformat=channel_layouts=mono,atrim=0:{duration},asetpts=PTS-STARTPTS,volume=0.18,afade=t=in:d=1.5,afade=t=out:st={max(0,duration-3)}:d=3[m];[m][n1]sidechaincompress=threshold=0.025:ratio=5:attack=30:release=600[b];[n2][b]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]'
  run(['ffmpeg','-y','-v','error','-i',narr,'-stream_loop','-1','-i',bgm,'-filter_complex',mix,'-map','[a]','-t',duration,audio])
 report=json.loads((d/'report.json').read_text());date=report['date'];out=d/f'morning_news_{date}.mp4';candidate=build/'candidate.mp4'
 # Target 2.8MB including 32kbps audio, plus room for MP4 tables and AAC overhead.
 rate=math.floor(2_800_000*8/duration/1000-32-3)
 if rate<45:raise ValueError('Insufficient bitrate budget; shorten the script')
 attempts=[]
 for attempt in range(3):
  print(f'Encoding attempt {attempt+1}: video {rate}kbps, audio 32kbps',flush=True)
  common=['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',build/'frames.txt']
  codec=['-vf','fps=12,format=yuv420p','-c:v','libx264','-preset','slow','-tune','stillimage','-b:v',f'{rate}k','-g','120','-force_key_frames',','.join(str(round(it['start']*12)/12) for it in tl['items']),'-t',duration,'-passlogfile',build/'pass']
  run(common+codec+['-pass','1','-an','-f','null',os.devnull])
  run(common+['-i',audio]+codec+['-pass','2','-map','0:v:0','-map','1:a:0','-c:a','aac','-b:a','32k','-ac','1','-ar','24000','-movflags','+faststart',candidate])
  size=candidate.stat().st_size;attempts.append({'video_kbps':rate,'bytes':size})
  if size<3_000_000:break
  rate=math.floor(rate*.9)
 else:raise ValueError('Failed 3MB limit after 3 attempts; oversized candidate kept in build, not delivered')
 media=probe(candidate);video=next(s for s in media['streams'] if s['codec_name']=='h264')
 if (video['width'],video['height'],video['r_frame_rate'])!=(720,1280,'12/1'):raise ValueError('Unexpected video format')
 actual=float(media['format']['duration'])
 if abs(actual-duration)>.15 or actual>190:raise ValueError('Unexpected duration')
 run(['ffmpeg','-v','error','-i',candidate,'-f','null','-'])
 shutil.copy2(candidate,out);shutil.copy2(d/'build/subtitles.srt',d/'subtitles.srt')
 run(['ffmpeg','-y','-v','error','-i',narr,'-ac','1','-c:a','libmp3lame','-b:a','64k',d/'narration.mp3'])
 # Review decoded output, including a dense market page rather than only the cover.
 for label,at in [('cover',.5),('data',next((it['start'] for it in tl['items'] if report['slides'][it['slide']]['type']=='market'),duration/2))]:
  run(['ffmpeg','-y','-v','error','-ss',at,'-i',out,'-frames:v','1',d/f'preview-{label}.png'])
 validation={'profile':'illustrated-under3mb','size_bytes':out.stat().st_size,'limit_bytes':3_000_000,'under_limit':True,'full_decode_pass':True,'media':media,'encoding_attempts':attempts,'a_pronunciation':'Kokoro v1.1; A股 → ashareletter股; stressed English /eɪ/; sid=3; speed=1.0; gaps=0.15/0.35','human_listening_confirmed':False,'backgrounds':'AI-generated illustrative stills; reuse bundled assets','intro_seconds':0}
 if 'sentiment_data' in report:validation['sentiment_data']=report['sentiment_data']
 (d/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2));print('COMPLETE',out,out.stat().st_size,'bytes',flush=True)
if __name__=='__main__':main()
