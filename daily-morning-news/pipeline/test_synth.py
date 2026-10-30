"""Focused regression checks; no model download or synthesis is required."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np
import synth


class TrimTests(unittest.TestCase):
    def test_only_edges_are_removed(self):
        speech = np.r_[np.ones(100), np.zeros(200), -np.ones(100)].astype(np.float32)
        x = np.r_[np.zeros(200), speech, np.zeros(300)].astype(np.float32)
        y, meta = synth.trim_edges(x, 1000)
        np.testing.assert_array_equal(y, x[160:640])
        self.assertEqual(meta, {"removed_head": .16, "removed_tail": .26})
        np.testing.assert_array_equal(y[140:340], np.zeros(200))

    def test_quiet_consonant_above_threshold_is_preserved(self):
        # -40 dB consonants survive a -50 dB relative threshold.
        x = np.r_[np.zeros(200), np.full(60, .01), np.ones(100),
                  np.full(60, .01), np.zeros(200)].astype(np.float32)
        y, _ = synth.trim_edges(x, 1000)
        np.testing.assert_array_equal(y, x[160:460])

    def test_padding_protects_subthreshold_onset(self):
        x = np.r_[np.zeros(200), np.full(30, .001), np.ones(100),
                  np.full(30, .001), np.zeros(200)].astype(np.float32)
        y, _ = synth.trim_edges(x, 1000)
        np.testing.assert_array_equal(y, x[190:370])

    def test_no_padding_added_when_audio_reaches_edges(self):
        x = np.ones(20, dtype=np.float32)
        y, meta = synth.trim_edges(x, 1000)
        np.testing.assert_array_equal(x, y)
        self.assertEqual(meta, {"removed_head": 0., "removed_tail": 0.})

    def test_invalid_audio_is_rejected(self):
        for x in ([], [0, 0], [[1, 1]], [np.nan], [np.inf], [1e-8]):
            with self.subTest(x=x), self.assertRaises(ValueError):
                synth.trim_edges(x, 1000)


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.config = {"engine": "kokoro", "engine_version": "2.0.1",
                       "models": {"model.onnx": "digest"}, "speed": 1.,
                       "sid": 3, "trim_db": -50., "trim_pad": .04, "version": 2}

    def test_every_audio_setting_invalidates_cache(self):
        original = synth.cache_key("A股", self.config)
        changes = {"engine": "matcha", "engine_version": "new",
                   "models": {"model.onnx": "newdigest"}, "speed": .85,
                   "sid": 4, "trim_db": -45., "trim_pad": .05, "version": 3}
        for setting, value in changes.items():
            changed = copy.deepcopy(self.config)
            changed[setting] = value
            with self.subTest(setting=setting):
                self.assertNotEqual(original, synth.cache_key("A股", changed))

    def test_text_invalidates_cache(self):
        self.assertNotEqual(synth.cache_key("A股", self.config),
                            synth.cache_key("港股", self.config))

    def test_cache_key_is_order_independent(self):
        reverse = dict(reversed(list(self.config.items())))
        self.assertEqual(synth.cache_key("A股", self.config), synth.cache_key("A股", reverse))
        self.assertEqual(len(synth.cache_key("A股", reverse)), 64)

    def test_model_contents_not_filename_invalidate_cache(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root, "model.onnx")
            p.write_bytes(b"one")
            before = synth.model_digest(root)
            p.write_bytes(b"two")
            self.assertNotEqual(before, synth.model_digest(root))


class KokoroLexiconTests(unittest.TestCase):
    def test_merge_is_build_only_and_overrides_alias(self):
        with tempfile.TemporaryDirectory() as root:
            model = Path(root, "models", "kokoro-multi-lang-v1_1")
            model.mkdir(parents=True)
            build = Path(root, "build")
            build.mkdir()
            source = model / "lexicon-us-en.txt"
            original = "alpha a l f a\nashareletter old\nbeta b e t a\n"
            source.write_text(original, encoding="utf8")
            result = Path(synth.kokoro_lexicon(str(model.parent), str(build)))
            self.assertEqual(result.parent, build)
            self.assertEqual(source.read_text(encoding="utf8"), original)
            merged = result.read_text(encoding="utf8")
            self.assertEqual(merged.count("ashareletter"), 1)
            self.assertTrue(merged.startswith("ashareletter ˈ A\n"))
            self.assertIn("alpha a l f a\n", merged)
            self.assertIn("beta b e t a\n", merged)

    def test_manifest_fingerprints_alias_and_does_not_edit_report(self):
        with tempfile.TemporaryDirectory() as root:
            model = Path(root, "models", "kokoro-multi-lang-v1_1")
            model.mkdir(parents=True)
            (model / "lexicon-us-en.txt").write_text("a ə\n", encoding="utf8")
            report = Path(root, "report")
            report.mkdir()
            original = json.dumps({"slides": [{"sentences": [
                {"say": "A股收盘。", "sub": "A股收盘。"}]}]}, ensure_ascii=False)
            (report / "report.json").write_text(original, encoding="utf8")
            generated = []
            def generate(text, **kwargs):
                generated.append(text)
                return SimpleNamespace(samples=np.ones(1000, dtype=np.float32), sample_rate=24000)
            with patch.object(synth, "make_kokoro", return_value=SimpleNamespace(generate=generate)), \
                 patch("sys.argv", ["synth.py", str(report), str(model.parent)]):
                synth.main()
            timeline = json.loads((report / "build" / "timeline.json").read_text())
            self.assertEqual(timeline["config"]["lexicon"], synth.KOKORO_LEXICON)
            self.assertEqual(timeline["items"][0]["sub"], "A股收盘。")
            self.assertEqual(generated, ["ashareletter股收盘。"])
            self.assertEqual((report / "report.json").read_text(encoding="utf8"), original)
            original_key = synth.cache_key(generated[0], timeline["config"])
            changed = copy.deepcopy(timeline["config"])
            changed["lexicon"] = ["ashareletter ə"]
            self.assertNotEqual(original_key, synth.cache_key(generated[0], changed))


class TextAndTimingTests(unittest.TestCase):
    def test_kokoro_uses_stressed_letter_alias_without_inserted_pause(self):
        text = "数据时点，A股和港股收盘。AI板块。"
        self.assertEqual(synth.prepare_say(text, "kokoro"),
                         "数据时点，ashareletter股和港股收盘。AI板块。")
        self.assertEqual(text, "数据时点，A股和港股收盘。AI板块。")
        self.assertEqual(synth.KOKORO_LEXICON, ["ashareletter ˈ A"])

    def test_legacy_matcha_replacements_remain_explicit(self):
        self.assertEqual(synth.prepare_say("A股与AI", "matcha"), "诶股与诶爱")

    def test_timestamp_rounding_carries_to_next_second(self):
        cases = [(0, "00:00:00,000"), (.9996, "00:00:01,000"),
                 (59.9996, "00:01:00,000"), (3599.9996, "01:00:00,000"),
                 (3661.234, "01:01:01,234")]
        for seconds, expected in cases:
            with self.subTest(seconds=seconds):
                self.assertEqual(synth.srt_ts(seconds), expected)

    def test_initial_pause_profile(self):
        self.assertEqual((synth.SENT_GAP, synth.SLIDE_GAP), (.15, .35))
        self.assertEqual((synth.TRIM_DB, synth.TRIM_PAD), (-50., .04))


if __name__ == "__main__":
    unittest.main()
