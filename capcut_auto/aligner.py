"""Căn (forced-align) từng `anchor_phrase` vào dãy từ có timestamp của voiceover.

Khác với chế độ CLIP (đoán ngữ nghĩa), chế độ neo dựa trên một sự thật chắc chắn:
mỗi ảnh đã được người dùng gắn sẵn với một CỤM TỪ THẬT trong lời thoại
(`anchor_phrase`). Việc còn lại chỉ là tìm cụm từ đó được đọc ở giây thứ mấy.

Thuật toán:
    1. Chuẩn hóa (lowercase, bỏ dấu câu) cả dãy từ Whisper lẫn từng anchor.
    2. Quét tuần tự (monotonic) theo thứ tự anchor: anchor sau luôn tìm SAU vị trí
       mà anchor trước kết thúc -> bám theo dòng thời gian, không nhảy lung tung.
    3. Với mỗi anchor, trượt cửa sổ quanh độ dài cụm từ, chấm điểm bằng
       SequenceMatcher để chịu được sai số nhận diện của Whisper.
    4. Lấy start = từ đầu cửa sổ, end = từ cuối cửa sổ.

Sau khi có start/end của từng anchor, ảnh được kéo dài từ start của anchor hiện tại
tới start của anchor kế tiếp (xử lý ở pipeline/draft_builder).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional

from .transcriber import Word

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    """Tách thành token chữ-số đã lowercase, bỏ dấu câu. Đa ngôn ngữ (\\w unicode)."""
    return _TOKEN_RE.findall(text.lower())


@dataclass
class AnchorMatch:
    """Kết quả căn một anchor vào timeline."""

    start: float
    end: float
    score: float
    word_start: int
    word_end: int  # exclusive
    found: bool


def _score(a_tokens: List[str], b_tokens: List[str]) -> float:
    """Độ giống giữa hai dãy token (0..1)."""
    if not a_tokens or not b_tokens:
        return 0.0
    return SequenceMatcher(None, a_tokens, b_tokens).ratio()


def _best_window(
    word_tokens: List[str],
    anchor_tokens: List[str],
    search_from: int,
) -> Optional[AnchorMatch]:
    """Tìm cửa sổ [i, j) trong word_tokens khớp nhất với anchor_tokens.

    Chỉ xét các cửa sổ bắt đầu từ `search_from` trở đi (đảm bảo monotonic).
    Thử nhiều độ dài cửa sổ quanh độ dài anchor để chịu được thừa/thiếu từ.
    """
    n = len(word_tokens)
    m = len(anchor_tokens)
    if n == 0 or m == 0 or search_from >= n:
        return None

    # Cho phép cửa sổ co giãn quanh độ dài anchor.
    len_lo = max(1, m - 2)
    len_hi = m + 3

    best: Optional[AnchorMatch] = None
    for i in range(search_from, n):
        # Cắt tỉa: nếu phần còn lại ngắn hơn nhiều so với anchor thì dừng.
        if n - i < len_lo and best is not None:
            break
        for win_len in range(len_lo, len_hi + 1):
            j = i + win_len
            if j > n:
                break
            window = word_tokens[i:j]
            s = _score(anchor_tokens, window)
            if best is None or s > best.score:
                best = AnchorMatch(
                    start=0.0, end=0.0, score=s,
                    word_start=i, word_end=j, found=True,
                )
        # Tối ưu nhỏ: khớp gần như tuyệt đối thì khỏi quét tiếp.
        if best is not None and best.score >= 0.97 and best.word_start == i:
            break
    return best


def align_anchors(
    words: List[Word],
    anchor_phrases: List[str],
    *,
    min_score: float = 0.45,
) -> List[AnchorMatch]:
    """Căn lần lượt các anchor vào dãy từ Whisper.

    Args:
        words: dãy từ kèm timestamp (từ transcribe_words).
        anchor_phrases: danh sách cụm từ neo, theo đúng thứ tự xuất hiện.
        min_score: ngưỡng để coi là tìm thấy. Dưới ngưỡng -> found=False (fallback).

    Returns:
        Danh sách AnchorMatch theo thứ tự anchor đầu vào.
    """
    word_tokens = [t for w in words for t in _tokenize(w.text)] if False else None
    # Xây map token -> chỉ số word (một từ Whisper có thể tách thành nhiều token;
    # ta giữ tương ứng token<->word để quy ngược ra mốc thời gian).
    flat_tokens: List[str] = []
    token_to_word: List[int] = []
    for wi, w in enumerate(words):
        toks = _tokenize(w.text)
        if not toks:
            # từ chỉ gồm dấu câu -> bỏ qua nhưng vẫn cần giữ vị trí; dùng chính text
            toks = [w.text.lower()] if w.text.strip() else []
        for t in toks:
            flat_tokens.append(t)
            token_to_word.append(wi)

    results: List[AnchorMatch] = []
    cursor = 0  # vị trí token bắt đầu tìm cho anchor kế tiếp
    for phrase in anchor_phrases:
        anchor_tokens = _tokenize(phrase)
        match = _best_window(flat_tokens, anchor_tokens, cursor)

        if match is None or match.score < min_score:
            # Không tìm thấy đáng tin: đánh dấu để pipeline xử lý fallback.
            results.append(
                AnchorMatch(
                    start=-1.0, end=-1.0, score=(match.score if match else 0.0),
                    word_start=-1, word_end=-1, found=False,
                )
            )
            continue

        wstart = token_to_word[match.word_start]
        wend = token_to_word[min(match.word_end - 1, len(token_to_word) - 1)]
        results.append(
            AnchorMatch(
                start=words[wstart].start,
                end=words[wend].end,
                score=match.score,
                word_start=match.word_start,
                word_end=match.word_end,
                found=True,
            )
        )
        # Tiến con trỏ để anchor sau tìm phía sau (monotonic).
        cursor = match.word_end

    return results
