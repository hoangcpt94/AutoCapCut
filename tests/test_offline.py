"""Test offline cho phần logic KHÔNG cần model nặng (Whisper/CLIP).

Bao gồm:
    - Parse file mapping (JSONL / JSON array / dạng dính liền).
    - Forced-align anchor_phrase vào dãy từ giả lập (có nhiễu nhận diện).
    - Dựng segment chế độ neo: kéo dài ảnh tới anchor kế tiếp.

Chạy:
    .venv\\Scripts\\python.exe tests\\test_offline.py
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capcut_auto.transcriber import Word
from capcut_auto.aligner import align_anchors, _tokenize
from capcut_auto.anchor_input import _decode_concatenated_json, parse_mapping
from capcut_auto.pipeline import _build_anchor_segments, _fill_missing_starts


def _ok(cond, msg):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def _make_words(sentence_starts):
    """Tạo dãy Word giả: mỗi từ 0.4s, liền nhau theo thứ tự."""
    words = []
    t = 0.0
    for sent in sentence_starts:
        for tok in sent.split():
            words.append(Word(text=tok, start=t, end=t + 0.4))
            t += 0.4
    return words


def test_decode_mapping():
    print("[test_decode_mapping]")
    concat = (
        '{"image_file":"1.png","anchor_phrase":"What if you fell into a black hole?"}'
        '{"image_file":"2.png","anchor_phrase":"you would be crushed to a dot"}'
    )
    objs = _decode_concatenated_json(concat)
    _ok(len(objs) == 2, "dạng dính liền tách được 2 object")
    _ok(objs[0]["image_file"] == "1.png", "object đầu đúng image_file")

    arr = '[{"image_file":"a.png","anchor_phrase":"x"},{"image_file":"b.png","anchor_phrase":"y"}]'
    _ok(len(_decode_concatenated_json(arr)) == 2, "JSON array tách được 2 object")

    jsonl = '{"image_file":"a.png","anchor_phrase":"x"}\n{"image_file":"b.png","anchor_phrase":"y"}\n'
    _ok(len(_decode_concatenated_json(jsonl)) == 2, "JSON lines tách được 2 object")


def test_parse_mapping_file():
    print("[test_parse_mapping_file]")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "mapping.jsonl")
        with open(p, "w", encoding="utf-8") as f:
            f.write('{"image_file":"1.png","anchor_phrase":"hello world"}\n')
            f.write('{"image_file":"2.png","anchor_phrase":"second phrase here"}\n')
        objs = parse_mapping(p)
        _ok(len(objs) == 2, "đọc file mapping.jsonl ra 2 mục")


def test_align_basic():
    print("[test_align_basic]")
    # Lời thoại thật (giả lập word-timestamps).
    transcript = [
        "what if you fell into a black hole",
        "right now in the movies you would be crushed to a dot in a heartbeat",
        "screaming gone",
        "it is terrifying it is dramatic",
        "and it is wrong",
    ]
    words = _make_words(transcript)

    anchors = [
        "What if you fell into a black hole?",
        "Right now, in the movies, you'd be crushed to a dot in a heartbeat.",
        "Screaming. Gone.",
        "It's terrifying. It's dramatic.",
        "And it's wrong.",
    ]
    matches = align_anchors(words, anchors, min_score=0.4)

    _ok(all(m.found for m in matches), "tất cả anchor đều được tìm thấy")
    # Thứ tự start phải tăng dần (monotonic).
    starts = [m.start for m in matches]
    _ok(starts == sorted(starts), "start của các anchor tăng dần theo timeline")
    # Anchor đầu phải bắt đầu ~0.
    _ok(matches[0].start < 0.5, "anchor đầu bắt đầu gần 0s")


def test_align_with_noise():
    print("[test_align_with_noise]")
    # Whisper nghe sai vài từ: 'fell' -> 'fall', 'heartbeat' -> 'heart beat'.
    transcript = [
        "what if you fall into a black hole",
        "right now in the movies you would be crushed to a dot in a heart beat",
        "and it is wrong",
    ]
    words = _make_words(transcript)
    anchors = [
        "What if you fell into a black hole?",
        "you'd be crushed to a dot in a heartbeat",
        "And it's wrong.",
    ]
    matches = align_anchors(words, anchors, min_score=0.4)
    _ok(all(m.found for m in matches), "vẫn khớp dù có nhiễu nhận diện")
    _ok(matches[0].start < matches[1].start < matches[2].start, "thứ tự đúng")


def test_build_segments_extends_to_next():
    print("[test_build_segments_extends_to_next]")
    transcript = ["alpha beta gamma", "delta epsilon zeta", "eta theta iota"]
    words = _make_words(transcript)
    anchors = ["alpha beta gamma", "delta epsilon zeta", "eta theta iota"]
    matches = align_anchors(words, anchors, min_score=0.4)
    segments, assignment, warnings = _build_anchor_segments(matches, anchors, words)

    _ok(len(segments) == 3, "3 segment cho 3 anchor")
    _ok(not warnings, "không có cảnh báo")
    # end của ảnh i phải bằng start của ảnh i+1 (kéo dài tới anchor kế tiếp).
    _ok(abs(segments[0].end - segments[1].start) < 1e-6, "ảnh 1 kéo dài tới ảnh 2")
    _ok(abs(segments[1].end - segments[2].start) < 1e-6, "ảnh 2 kéo dài tới ảnh 3")
    # ảnh cuối kéo tới hết audio.
    _ok(segments[2].end >= words[-1].end - 1e-6, "ảnh cuối kéo tới hết voiceover")
    _ok([a[0] for a in assignment] == [0, 1, 2], "assignment ánh xạ đúng index ảnh")


def test_missing_anchor_fallback():
    print("[test_missing_anchor_fallback]")
    transcript = ["alpha beta gamma", "delta epsilon zeta", "eta theta iota"]
    words = _make_words(transcript)
    # Anchor giữa hoàn toàn không có trong lời thoại.
    anchors = ["alpha beta gamma", "completely unrelated nonsense xyzzy", "eta theta iota"]
    matches = align_anchors(words, anchors, min_score=0.6)
    segments, assignment, warnings = _build_anchor_segments(matches, anchors, words)

    _ok(len(warnings) >= 1, "có cảnh báo cho anchor không khớp")
    starts = [s.start for s in segments]
    _ok(starts == sorted(starts), "start vẫn tăng dần sau khi nội suy")
    _ok(all(segments[i].end > segments[i].start for i in range(3)), "mọi clip có thời lượng dương")


def test_fill_missing():
    print("[test_fill_missing]")
    filled = _fill_missing_starts([0.0, None, None, 9.0], audio_end=12.0)
    _ok(filled[1] > 0.0 and filled[2] > filled[1] and filled[2] < 9.0, "nội suy giữa hai mốc đã biết")
    filled2 = _fill_missing_starts([None, 4.0], audio_end=10.0)
    _ok(filled2[0] >= 0.0 and filled2[0] < 4.0, "nội suy mốc đầu thiếu")


def main():
    tests = [
        test_decode_mapping,
        test_parse_mapping_file,
        test_align_basic,
        test_align_with_noise,
        test_build_segments_extends_to_next,
        test_missing_anchor_fallback,
        test_fill_missing,
    ]
    for t in tests:
        t()
    print("\nTẤT CẢ TEST OFFLINE ĐỀU PASS.")


if __name__ == "__main__":
    main()
