"""Điều phối toàn bộ pipeline: transcribe -> align -> match -> build draft."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .config import ProjectConfig
from .transcriber import Segment, transcribe
from .script_utils import read_script, align_script_to_segments
from .image_matcher import ImageMatcher, assign_images
from .draft_builder import build_draft


@dataclass
class PipelineResult:
    draft_path: str
    segments: List[Segment]
    assignment: List[Tuple[int, float]]
    image_paths: List[str]

    def report(self) -> str:
        lines = [f"Draft đã tạo tại: {self.draft_path}", ""]
        lines.append(f"Số đoạn: {len(self.segments)} | Số ảnh: {len(self.image_paths)}")
        lines.append("-" * 60)
        for i, seg in enumerate(self.segments):
            img_idx, score = self.assignment[i]
            import os
            img_name = os.path.basename(self.image_paths[img_idx])
            preview = seg.text[:50] + ("…" if len(seg.text) > 50 else "")
            lines.append(
                f"[{seg.start:6.2f}-{seg.end:6.2f}s] match={score:.3f} "
                f"-> {img_name}\n    \"{preview}\""
            )
        return "\n".join(lines)


def run(config: ProjectConfig, *, verbose: bool = True) -> PipelineResult:
    config.validate()

    def log(msg: str) -> None:
        if verbose:
            print(msg, flush=True)

    image_paths = config.list_images()
    if not image_paths:
        raise RuntimeError(f"Thư mục {config.images_dir} không có ảnh hợp lệ.")
    log(f"Tìm thấy {len(image_paths)} ảnh.")

    log("Bước 1/4: Nhận diện voiceover (Whisper)...")
    whisper_segments = transcribe(
        config.voiceover_path,
        model_size=config.whisper_model,
        language=config.language,
        cache_dir=config.cache_dir,
        model_cache_dir=config.model_cache_dir,
    )
    log(f"  -> {len(whisper_segments)} đoạn từ voiceover.")

    log("Bước 2/4: Căn chỉnh script...")
    script_text = read_script(config.script_path) if config.script_path else None
    segments = align_script_to_segments(whisper_segments, script_text)
    log(f"  -> {len(segments)} đoạn sau khi căn script.")

    log("Bước 3/4: Phân tích & ghép ảnh (CLIP đa ngôn ngữ)...")
    matcher = ImageMatcher(
        model_name=config.clip_model,
        cache_dir=config.cache_dir,
        model_cache_dir=config.model_cache_dir,
    )
    assignment = assign_images(
        segments, image_paths, matcher, allow_reuse=config.allow_image_reuse
    )
    log("  -> Đã ghép xong.")

    log("Bước 4/4: Dựng draft CapCut...")
    draft_path = build_draft(config, segments, assignment, image_paths)
    log(f"  -> Xong: {draft_path}")

    return PipelineResult(
        draft_path=draft_path,
        segments=segments,
        assignment=assignment,
        image_paths=image_paths,
    )
