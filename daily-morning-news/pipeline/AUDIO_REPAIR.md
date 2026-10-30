# Audio repair — 2026-10-28

Default engine is now sherpa-onnx 2.0.1 / Kokoro v1.1 bilingual, Chinese female
speaker 3. This changes the narrator's timbre. Spoken `A股` uses a scoped `ashareletter` alias with native stressed English
phonemes `ˈ A` (/eɪ/). Subtitles and source text remain `A股`; there is no
Mandarin `诶` substitution or inserted comma. A generated English lexicon
contains the alias, leaving downloaded model assets unchanged. The phoneme `A` maps
to /eɪ/ in the model's Misaki phoneme set. This is not a human-listening verdict.

Sentence/slide gaps: 0.15/0.35 s. Edge-only trimming uses -50 dB relative to
peak plus 40 ms padding; internal punctuation pauses are not cut. Sample-level
boundaries prevent clipping whole frames. Silent/nonfinite audio fails.
Cache SHA256 includes model contents, engine version, voice, speed, text,
lexicon and trim/timeline settings. Old MD5 entries cannot be reused.

Run setup.sh, then make_video.sh on a new staging directory containing the
unchanged report.json. Existing videos are protected from overwrite. Compare
A股 samples and important names/numbers before publishing. The new speaker
requires editorial pronunciation review; old Matcha pinyin lexicon entries
are not automatically compatible with Kokoro phonemes.

Final encoding is 720x1280 at 12 fps, two-pass bitrate budget, AAC 32 kbps;
files >= 3,000,000 bytes fail delivery validation. Full decode is checked.

Focused tests: python -m unittest discover -s pipeline -p test_synth.py -v

Oct28 regeneration additionally retains all 23 illustrated frames from the
original verified MP4, retimed against freshly generated sentence audio.
Factual report.json is unchanged. Original MP4 is not overwritten.

Independent SenseVoice ASR recognized A股 in 4/4 exact report samples
with the stressed alias (2/4 without stress). This does not prove subjective
audio quality or certify all other words; no human listening was performed.
