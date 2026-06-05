"""Đọc script và căn chỉnh nội dung script vào timing của Whisper.

Người dùng đã có sẵn voiceover + script. Whisper cho ta mốc thời gian chính xác,
còn script cho ta văn bản chuẩn (đúng chính tả, dấu câu). Module này ghép hai thứ:
giữ timing từ Whisper, thay nội dung bằng script khi có.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .transcriber import Segment

# Ký tự kết câu cho nhiều ngôn ngữ (Latin + CJK)
_SENTENCE_END = re.compile(r"(?<=[\.\!\?…。！？;；])\s+|\n+")


def read_script(path: str) -> str:
    """Đọc nội dung script, hỗ trợ BOM."""
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read().strip()


def split_sentences(text: str) -> List[str]:
    """Tách văn bản thành các câu. Đa ngôn ngữ, đơn giản và ổn định."""
    text = text.strip()
    if not text:
        return []
    parts = _SENTENCE_END.split(text)
    return [p.strip() for p in parts if p and p.strip()]


def align_script_to_segments(
    whisper_segments: List[Segment],
    script_text: Optional[str],
) -> List[Segment]:
    """Trả về danh sách Segment dùng để ghép ảnh và làm phụ đề.

    - Không có script: trả thẳng kết quả Whisper.
    - Có script: giữ nguyên timing Whisper, nhưng phân bố các câu trong script
      vào đúng số đoạn của Whisper theo tỉ lệ độ dài, để phụ đề đẹp và đúng chính tả.
    """
    if not script_text:
        return whisper_segments

    sentences = split_sentences(script_text)
    if not sentences:
        return whisper_segments

    n_seg = len(whisper_segments)

    # Trường hợp số câu khớp số đoạn: ghép 1-1.
    if len(sentences) == n_seg:
        return [
            Segment(text=sentences[i], start=whisper_segments[i].start, end=whisper_segments[i].end)
            for i in range(n_seg)
        ]

    # Nhiều câu hơn đoạn: gộp câu vào từng đoạn theo tỉ lệ thời lượng đoạn.
    if len(sentences) > n_seg:
        return _distribute_sentences(whisper_segments, sentences)

    # Ít câu hơn đoạn: tách đoạn dài để mỗi câu trải theo timeline.
    return _spread_sentences(whisper_segments, sentences)


def _distribute_sentences(segments: List[Segment], sentences: List[str]) -> List[Segment]:
    """Gộp nhiều câu vào từng đoạn Whisper theo tỉ lệ thời lượng."""
    total_dur = sum(s.duration for s in segments) or 1.0
    result: List[Segment] = []
    idx = 0
    remaining = len(sentences)
    for i, seg in enumerate(segments):
        seg_left = len(segments) - i
        # Số câu phân cho đoạn này, tối thiểu 1, cân theo thời lượng
        share = max(1, round(len(sentences) * seg.duration / total_dur))
        share = min(share, remaining - (seg_left - 1)) if seg_left > 1 else remaining
        share = max(1, share)
        chunk = sentences[idx: idx + share]
        idx += share
        remaining -= share
        text = " ".join(chunk) if chunk else seg.text
        result.append(Segment(text=text, start=seg.start, end=seg.end))
    # Nếu còn câu sót lại, nối vào đoạn cuối
    if idx < len(sentences):
        leftover = " ".join(sentences[idx:])
        result[-1] = Segment(
            text=(result[-1].text + " " + leftover).strip(),
            start=result[-1].start,
            end=result[-1].end,
        )
    return result


def _spread_sentences(segments: List[Segment], sentences: List[str]) -> List[Segment]:
    """Trải các câu (ít hơn số đoạn) theo timeline tổng, chia đều theo thời lượng."""
    start_t = segments[0].start
    end_t = segments[-1].end
    span = (end_t - start_t) or 1.0
    n = len(sentences)
    result: List[Segment] = []
    for i, sent in enumerate(sentences):
        s = start_t + span * i / n
        e = start_t + span * (i + 1) / n
        result.append(Segment(text=sent, start=s, end=e))
    return result
