"""Tách timing voiceover bằng faster-whisper (word-level).

Chế độ neo cần mốc thời gian TỪNG TỪ để căn từng cụm `anchor_phrase` vào đúng
vị trí trên timeline. Mỗi `Word` gồm: text, start, end (đơn vị giây).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class Word:
    """Một từ trong voiceover với mốc thời gian (giây)."""

    text: str
    start: float
    end: float


@dataclass
class Segment:
    """Một đoạn trên timeline (text phụ đề + mốc thời gian giây).

    Trong chế độ neo, mỗi segment ứng với một ảnh: text = anchor_phrase,
    [start, end) = khoảng ảnh hiển thị.
    """

    text: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def _words_cache_path(cache_dir: str, audio_path: str, model: str) -> str:
    base = os.path.splitext(os.path.basename(audio_path))[0]
    return os.path.join(cache_dir, f"words_{base}_{model}.json")


def transcribe_words(
    audio_path: str,
    *,
    model_size: str = "base",
    language: Optional[str] = None,
    cache_dir: Optional[str] = None,
    model_cache_dir: Optional[str] = None,
) -> List[Word]:
    """Nhận diện voiceover và trả về danh sách Word (từng từ kèm mốc thời gian).

    Args:
        audio_path: đường dẫn file audio.
        model_size: tiny/base/small/medium/large-v3.
        language: mã ngôn ngữ; None để tự nhận diện.
        cache_dir: nếu set, cache kết quả để lần sau khỏi chạy lại.
        model_cache_dir: thư mục lưu model tải về (đặt sang ổ nhiều dung lượng).
    """
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = _words_cache_path(cache_dir, audio_path, model_size)
        if os.path.isfile(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [Word(**d) for d in data]

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Thiếu faster-whisper. Cài bằng: pip install faster-whisper"
        ) from exc

    # CPU mặc định int8 cho nhẹ; nếu có GPU NVIDIA đổi device='cuda'.
    model = WhisperModel(
        model_size, device="cpu", compute_type="int8", download_root=model_cache_dir
    )
    seg_iter, _info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=True,
        word_timestamps=True,
    )

    words: List[Word] = []
    for s in seg_iter:
        for w in (s.words or []):
            text = w.word.strip()
            if not text:
                continue
            words.append(Word(text=text, start=float(w.start), end=float(w.end)))

    if not words:
        raise RuntimeError("Whisper không lấy được word-timestamp nào từ voiceover.")

    if cache_dir:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump([asdict(w) for w in words], f, ensure_ascii=False, indent=2)

    return words
