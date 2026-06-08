"""Điều phối pipeline (chế độ NEO).

Đọc mapping ảnh<->anchor_phrase từ thư mục tập, dùng word-timestamp của Whisper
để căn từng cụm từ vào timeline, rồi kéo dài mỗi ảnh tới khi anchor kế tiếp bắt
đầu (ảnh cuối kéo tới hết voiceover). Cuối cùng dựng draft CapCut.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .config import ProjectConfig
from .transcriber import Word, Segment, transcribe_words
from .aligner import align_anchors
from .anchor_input import load_episode
from .draft_builder import build_draft


@dataclass
class PipelineResult:
    draft_path: str
    segments: List[Segment]
    assignment: List[Tuple[int, float]]
    image_paths: List[str]
    warnings: List[str] = field(default_factory=list)

    def report(self) -> str:
        import os
        lines = [f"Draft đã tạo tại: {self.draft_path}", ""]
        lines.append(f"Số đoạn: {len(self.segments)} | Số ảnh: {len(self.image_paths)}")
        lines.append("-" * 60)
        for i, seg in enumerate(self.segments):
            img_idx, score = self.assignment[i]
            img_name = os.path.basename(self.image_paths[img_idx])
            preview = seg.text[:50] + ("…" if len(seg.text) > 50 else "")
            lines.append(
                f"[{seg.start:6.2f}-{seg.end:6.2f}s] match={score:.3f} "
                f"-> {img_name}\n    \"{preview}\""
            )
        if self.warnings:
            lines.append("-" * 60)
            lines.append("CẢNH BÁO:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        return "\n".join(lines)


def run(config: ProjectConfig, *, verbose: bool = True) -> PipelineResult:
    config.validate()

    def log(msg: str) -> None:
        if verbose:
            print(msg, flush=True)

    log(f"Đọc input tập: {config.input_dir}")
    episode = load_episode(
        config.input_dir,
        images_dir=config.images_dir or None,
        voiceover_path=config.voiceover_path or None,
        skip_missing_images=config.skip_missing_images,
    )
    # Đồng bộ lại config để build_draft dùng đúng voiceover/ảnh đã phân giải.
    config.voiceover_path = episode.voiceover_path
    config.images_dir = episode.images_dir
    for w in episode.warnings:
        log(f"  (Cảnh báo) {w}")

    image_paths = [it.image_path for it in episode.items]
    anchor_phrases = [it.anchor_phrase for it in episode.items]
    log(f"  -> {len(episode.items)} cặp ảnh<->anchor | voiceover: {episode.voiceover_path}")

    log("Bước 1/3: Nhận diện voiceover kèm mốc từng từ (Whisper word-timestamps)...")
    words = transcribe_words(
        config.voiceover_path,
        model_size=config.whisper_model,
        language=config.language,
        cache_dir=config.cache_dir,
        model_cache_dir=config.model_cache_dir,
    )
    log(f"  -> {len(words)} từ.")

    log("Bước 2/3: Căn các anchor_phrase vào timeline...")
    matches = align_anchors(words, anchor_phrases, min_score=config.anchor_min_score)

    segments, assignment, warnings = _build_anchor_segments(matches, anchor_phrases, words)

    log("Bước 3/3: Dựng draft CapCut...")
    draft_path = build_draft(config, segments, assignment, image_paths)
    log(f"  -> Xong: {draft_path}")

    return PipelineResult(
        draft_path=draft_path,
        segments=segments,
        assignment=assignment,
        image_paths=image_paths,
        warnings=episode.warnings + warnings,
    )


def _build_anchor_segments(
    matches, anchor_phrases: List[str], words: List[Word]
) -> Tuple[List[Segment], List[Tuple[int, float]], List[str]]:
    """Từ kết quả căn anchor -> danh sách Segment + assignment + cảnh báo.

    Quy tắc thời lượng: mỗi ảnh kéo dài từ start của anchor hiện tại tới start
    của anchor kế tiếp. Anchor cuối kéo tới hết voiceover.
    """
    n = len(anchor_phrases)
    audio_end = words[-1].end if words else 0.0
    warnings: List[str] = []

    # Bước 1: xác định start của mỗi anchor; đánh dấu anchor không tìm thấy.
    starts: List[Optional[float]] = []
    for i, m in enumerate(matches):
        if m.found:
            starts.append(m.start)
        else:
            starts.append(None)
            warnings.append(
                f"Anchor #{i + 1} không khớp được lời thoại "
                f"(điểm {m.score:.2f}): \"{anchor_phrases[i][:60]}\""
            )

    # Bước 2: nội suy start cho anchor bị thiếu (đặt giữa anchor trước & sau).
    filled = _fill_missing_starts(starts, audio_end)

    # Bước 3: ép thứ tự không lùi (monotonic) để clip luôn dương.
    for i in range(1, n):
        if filled[i] <= filled[i - 1]:
            filled[i] = filled[i - 1] + 0.001

    # Bước 4: dựng segment với end = start anchor kế tiếp (anchor cuối tới hết audio).
    segments: List[Segment] = []
    assignment: List[Tuple[int, float]] = []
    for i in range(n):
        start = filled[i]
        end = filled[i + 1] if i + 1 < n else max(audio_end, start + 0.5)
        if end <= start:
            end = start + 0.5
        segments.append(Segment(text=anchor_phrases[i], start=start, end=end))
        assignment.append((i, matches[i].score if matches[i].found else 0.0))

    return segments, assignment, warnings


def _fill_missing_starts(starts: List[Optional[float]], audio_end: float) -> List[float]:
    """Điền start cho các anchor không khớp bằng nội suy tuyến tính giữa
    các anchor đã biết (hoặc 0.0 / audio_end ở hai đầu)."""
    n = len(starts)
    result: List[float] = [s if s is not None else -1.0 for s in starts]

    i = 0
    while i < n:
        if result[i] >= 0:
            i += 1
            continue
        j = i
        while j < n and result[j] < 0:
            j += 1
        prev_val = result[i - 1] if i > 0 else 0.0
        nxt_val = result[j] if j < n else audio_end
        gap = j - i + 1
        for k in range(i, j):
            frac = (k - i + 1) / gap
            result[k] = prev_val + (nxt_val - prev_val) * frac
        i = j

    return result
