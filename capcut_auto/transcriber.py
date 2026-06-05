"""Tách timing từng đoạn voiceover bằng faster-whisper.

Whisper hỗ trợ đa ngôn ngữ và xuất ra timestamp cho từng đoạn (segment).
Mỗi `Segment` gồm: text, start, end (đơn vị giây).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class Segment:
    """Một đoạn voiceover với mốc thời gian (giây)."""

    text: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def _cache_path(cache_dir: str, audio_path: str, model: str) -> str:
    base = os.path.splitext(os.path.basename(audio_path))[0]
    return os.path.join(cache_dir, f"transcript_{base}_{model}.json")


def transcribe(
    audio_path: str,
    *,
    model_size: str = "base",
    language: Optional[str] = None,
    cache_dir: Optional[str] = None,
    model_cache_dir: Optional[str] = None,
) -> List[Segment]:
    """Nhận diện voiceover và trả về danh sách Segment theo thời gian.

    Args:
        audio_path: đường dẫn file audio.
        model_size: tiny/base/small/medium/large-v3.
        language: mã ngôn ngữ; None để tự nhận diện.
        cache_dir: nếu set, cache kết quả để lần sau khỏi chạy lại.
        model_cache_dir: thư mục lưu model tải về (đặt sang ổ nhiều dung lượng).
    """
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = _cache_path(cache_dir, audio_path, model_size)
        if os.path.isfile(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [Segment(**d) for d in data]

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Thiếu faster-whisper. Cài bằng: pip install faster-whisper"
        ) from exc

    # CPU mặc định int8 cho nhẹ; nếu có GPU NVIDIA đổi device='cuda'
    model = WhisperModel(
        model_size, device="cpu", compute_type="int8", download_root=model_cache_dir
    )
    seg_iter, info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=True,
        word_timestamps=False,
    )

    segments: List[Segment] = []
    for s in seg_iter:
        text = s.text.strip()
        if not text:
            continue
        segments.append(Segment(text=text, start=float(s.start), end=float(s.end)))

    if not segments:
        raise RuntimeError("Whisper không nhận diện được đoạn nào từ voiceover.")

    if cache_dir:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in segments], f, ensure_ascii=False, indent=2)

    return segments


def detected_language(audio_path: str, model_size: str = "base") -> str:
    """Trả về mã ngôn ngữ Whisper nhận diện được (tiện cho log)."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    _, info = model.transcribe(audio_path, language=None)
    return info.language
