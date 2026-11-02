"""Prepend two seconds of music-only screen time; preserve the entire narration."""
from pathlib import Path
import json,re,sys
import numpy as np
import soundfile as sf

def add_prelude(report_dir, seconds=2.0):
    build=Path(report_dir)/'build';path=build/'timeline.json';tl=json.loads(path.read_text())
    if tl.get('music_prelude_seconds'):
        raise ValueError('Prelude already applied; regenerate the unshifted timeline first')
    audio,sr=sf.read(build/'narration.wav',dtype='float32',always_2d=True)
    silence=np.zeros((round(seconds*sr),audio.shape[1]),dtype=np.float32)
    sf.write(build/'narration.wav',np.concatenate([silence,audio]),sr,subtype='FLOAT')
    first=dict(tl['items'][0]);first.update(sub='',start=0.0,end=seconds,show_end=seconds,music_prelude=True)
    first.pop('clip',None);first.pop('trim',None)
    for item in tl['items']:
        for key in ['start','end','show_end']:item[key]+=seconds
    tl['items'].insert(0,first);tl['total']+=seconds;tl['music_prelude_seconds']=seconds
    path.write_text(json.dumps(tl,ensure_ascii=False,indent=2))
    def shift(m):
        ms=int(m[1])*3600000+int(m[2])*60000+int(m[3])*1000+int(m[4])+round(seconds*1000)
        return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
    srt=build/'subtitles.srt';srt.write_text(re.sub(r'(\d+):(\d+):(\d+),(\d+)',shift,srt.read_text()))
    print(f'Added {seconds:g}s music-only prelude; narration/subtitles/timeline shifted intact')

if __name__=='__main__':add_prelude(sys.argv[1])
