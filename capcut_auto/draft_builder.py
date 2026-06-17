"""Sinh draft CapCut từ kết quả ghép ảnh + voiceover + phụ đề.

Dùng pycapcut. Bố cục draft:
    - 1 track video: các ảnh, mỗi ảnh trải đúng khoảng thời gian đoạn tương ứng.
    - 1 track audio: file voiceover full.
    - 1 track text (tùy chọn): phụ đề từng đoạn.
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

from .config import ProjectConfig
from .transcriber import Segment

SEC = 1_000_000  # 1 giây = 1e6 micro giây (đơn vị thời gian của CapCut)


def _us(seconds: float) -> int:
    """Đổi giây -> micro giây (int)."""
    return int(round(seconds * SEC))


def _video_boundaries(segments: List[Segment], audio_end_us: int) -> List[Tuple[int, int]]:
    """Tính (start_us, end_us) cho từng ảnh trên track video chính.

    Quy tắc:
    - Ảnh ĐẦU TIÊN bắt đầu tại 0 (CapCut buộc clip đầu của track chính phải từ 0s,
      nếu không sẽ tự kéo về 0 làm lệch toàn bộ ảnh phía sau).
    - Các ảnh nối đuôi nhau: ảnh i kết thúc đúng tại điểm bắt đầu ảnh i+1
      => không hở, không chồng (tránh lỗi SegmentOverlap).
    - Ảnh CUỐI kéo tới hết audio (nếu audio dài hơn) để không để khoảng đen.
    """
    n = len(segments)
    starts: List[int] = []
    for i, seg in enumerate(segments):
        starts.append(0 if i == 0 else _us(seg.start))
    # Đảm bảo mốc bắt đầu tăng ngặt để mỗi clip có thời lượng > 0.
    for i in range(1, n):
        if starts[i] <= starts[i - 1]:
            starts[i] = starts[i - 1] + 1

    bounds: List[Tuple[int, int]] = []
    for i in range(n):
        start_us = starts[i]
        if i + 1 < n:
            end_us = starts[i + 1]
        else:
            # Clip cuối: phủ tới hết audio (hoặc hết đoạn), tối thiểu 0.5s.
            end_us = max(_us(segments[i].end), audio_end_us, start_us + _us(0.5))
        bounds.append((start_us, end_us))
    return bounds


def build_draft(
    config: ProjectConfig,
    segments: List[Segment],
    assignment: List[Tuple[int, float]],
    image_paths: List[str],
) -> str:
    """Dựng và lưu draft. Trả về đường dẫn thư mục draft (hoặc file json)."""
    from pycapcut import (
        DraftFolder,
        ScriptFile,
        VideoMaterial,
        AudioMaterial,
        VideoSegment,
        AudioSegment,
        TextSegment,
        TextStyle,
        TextBorder,
        Timerange,
        TrackType,
        ClipSettings,
        TransitionType,
    )
    from pycapcut.metadata.font_meta import FontType

    # Quyết định nơi lưu: thư mục CapCut (qua DraftFolder) hay output_dir (test).
    use_output_dir = config.output_dir is not None

    if use_output_dir:
        os.makedirs(config.output_dir, exist_ok=True)
        script = ScriptFile(config.width, config.height, config.fps)
        save_target = os.path.join(config.output_dir, "draft_content.json")
        script.save_path = save_target
    else:
        draft_root = config.draft_root
        if draft_root is None:
            from .config import find_capcut_draft_folder
            draft_root = find_capcut_draft_folder()
        if draft_root is None:
            raise RuntimeError(
                "Không tìm được thư mục draft CapCut. Hãy truyền draft_root hoặc dùng output_dir."
            )
        folder = DraftFolder(draft_root)
        script = folder.create_draft(
            config.draft_name, config.width, config.height, config.fps, allow_replace=True
        )

    # Tải material audio trước để biết tổng thời lượng voiceover (dùng kéo ảnh cuối).
    audio_material = AudioMaterial(config.voiceover_path)

    # --- Track video (ảnh) ---
    script.add_track(TrackType.video, "main_video")

    bounds = _video_boundaries(segments, audio_material.duration)

    # Tạo trước toàn bộ clip, gắn transition, rồi mới add vào script.
    # (pycapcut thu thập material transition NGAY tại add_segment, nên transition
    #  phải được gắn vào clip TRƯỚC khi add, nếu không reference sẽ hỏng.)
    video_segs = []
    for i, seg in enumerate(segments):
        img_idx, _score = assignment[i]
        img_path = image_paths[img_idx]

        start_us, end_us = bounds[i]
        duration_us = end_us - start_us

        material = VideoMaterial(img_path)
        clip = _build_image_clip_settings(
            material.width, material.height, config.width, config.height, ClipSettings
        )
        vseg = VideoSegment(
            material,
            Timerange(start_us, duration_us),
            clip_settings=clip,
        )
        video_segs.append(vseg)

    # Transition đặt trên clip ĐỨNG TRƯỚC (không đặt ở clip cuối).
    if config.transition:
        for i in range(len(video_segs) - 1):
            _try_add_transition(video_segs[i], config.transition, TransitionType)

    for vseg in video_segs:
        script.add_segment(vseg, "main_video")

    # --- Track audio (voiceover) ---
    script.add_track(TrackType.audio, "voiceover")
    aseg = AudioSegment(
        audio_material,
        Timerange(0, audio_material.duration),
    )
    script.add_segment(aseg, "voiceover")

    # --- Track phụ đề (tùy chọn) ---
    if config.add_subtitles:
        script.add_track(TrackType.text, "subtitles", relative_index=999)
        style = TextStyle(
            size=7.0,
            bold=True,
            color=(1.0, 0.92, 0.38),
            align=1,
            auto_wrapping=True,
            max_line_width=0.76,
        )
        border = TextBorder(alpha=1.0, color=(0.0, 0.0, 0.0), width=42.0)
        sub_clip = ClipSettings(transform_y=-0.76)
        prev_end_us = 0
        for i, seg in enumerate(segments):
            start_us = _us(seg.start)
            end_us = _us(seg.end)
            # Tránh chồng phụ đề khi Whisper trả đoạn sát/đè nhau.
            if start_us < prev_end_us:
                start_us = prev_end_us
            dur = max(_us(0.3), end_us - start_us)
            if not seg.text.strip():
                prev_end_us = start_us + dur
                continue
            tseg = TextSegment(
                seg.text,
                Timerange(start_us, dur),
                font=FontType.BebasNeue,
                style=style,
                clip_settings=sub_clip,
                border=border,
            )
            script.add_segment(tseg, "subtitles")
            prev_end_us = start_us + dur

    # --- Lưu ---
    if use_output_dir:
        script.dump(save_target)
        return config.output_dir
    else:
        script.save()
        # Đăng ký draft để CapCut bản mới (7.x/8.x) nhận diện, nếu không
        # CapCut sẽ coi folder là rác và tự xóa khi khởi động.
        from .draft_registry import register_draft
        try:
            register_draft(draft_root, config.draft_name)
        except Exception as exc:  # không chặn pipeline nếu đăng ký lỗi
            print(f"  (Cảnh báo) Không đăng ký được draft vào index CapCut: {exc}")
        return os.path.join(draft_root, config.draft_name)


def _build_image_clip_settings(img_w, img_h, canvas_w, canvas_h, ClipSettings):
    """Scale ảnh để phủ kín canvas (cover), giữ tỉ lệ, canh giữa."""
    if img_w <= 0 or img_h <= 0:
        return ClipSettings()
    img_ratio = img_w / img_h
    canvas_ratio = canvas_w / canvas_h
    # pycapcut fit ảnh theo chiều rộng canvas mặc định (scale 1.0 = vừa khung theo 1 chiều).
    # Để cover, scale lên cho chiều còn lại lấp đầy.
    if img_ratio > canvas_ratio:
        # Ảnh rộng hơn khung -> cao khớp, dư bề ngang: scale theo chiều cao.
        scale = img_ratio / canvas_ratio
    else:
        # Ảnh cao/hẹp hơn -> scale theo chiều rộng.
        scale = canvas_ratio / img_ratio
    return ClipSettings(scale_x=scale, scale_y=scale)


def _try_add_transition(video_seg, transition_name: str, TransitionType) -> None:
    """Thêm transition theo tên (không phân biệt hoa thường), bỏ qua nếu không có."""
    name = transition_name.strip()
    member = None
    if hasattr(TransitionType, name):
        member = getattr(TransitionType, name)
    else:
        for t in TransitionType:
            if t.name.lower() == name.lower():
                member = t
                break
    if member is not None:
        try:
            video_seg.add_transition(member, duration="0.5s")
        except Exception:
            pass
