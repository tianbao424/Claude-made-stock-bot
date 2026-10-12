"""可选：用离线语音识别把每句配音转回文字，和字幕对照，粗查读错/漏读。

用法: python3 qa_asr.py <report_dir> <models_dir>
需要 setup.sh --with-asr 下载的 paraformer 模型。小模型对专有名词、同音字常有误判，仅作参考。
"""
import json
import os
import sys

import sherpa_onnx
import soundfile as sf


def main():
    rdir, models = sys.argv[1], sys.argv[2]
    a = os.path.join(models, "sherpa-onnx-paraformer-zh-small-2024-03-09")
    rec = sherpa_onnx.OfflineRecognizer.from_paraformer(paraformer=f"{a}/model.int8.onnx", tokens=f"{a}/tokens.txt", num_threads=4)
    tl = json.load(open(os.path.join(rdir, "build", "timeline.json"), encoding="utf8"))
    for e in tl["items"]:
        x, sr = sf.read(e["clip"], dtype="float32")
        s = rec.create_stream(); s.accept_waveform(sr, x); rec.decode_stream(s)
        print(f"字幕：{e['sub']}\n识别：{s.result.text}\n")


if __name__ == "__main__":
    main()
