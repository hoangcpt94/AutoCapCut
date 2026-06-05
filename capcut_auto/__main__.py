"""CLI cho capcut_auto.

Ví dụ:
    python -m capcut_auto --images ./images --voiceover ./vo.mp3 --script ./script.txt
    python -m capcut_auto --images ./images --voiceover ./vo.mp3 --output-dir ./out_draft
"""

from __future__ import annotations

import argparse
import sys

from .config import ProjectConfig, find_capcut_draft_folder
from .pipeline import run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="capcut_auto",
        description="Tự động ghép ảnh khớp voiceover thành draft CapCut.",
    )
    p.add_argument("--images", default=None, help="Thư mục chứa ảnh.")
    p.add_argument("--voiceover", default=None, help="File voiceover (mp3/wav/...).")
    p.add_argument("--script", default=None, help="File script (txt). Tùy chọn.")

    p.add_argument("--draft-name", default="auto_capcut_project", help="Tên draft CapCut.")
    p.add_argument("--draft-root", default=None, help="Thư mục draft CapCut. Mặc định tự dò.")
    p.add_argument("--output-dir", default=None, help="Ghi draft ra đây thay vì thư mục CapCut (để test).")

    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--fps", type=int, default=30)

    p.add_argument("--whisper-model", default="base", help="tiny/base/small/medium/large-v3")
    p.add_argument("--language", default=None, help="Mã ngôn ngữ vd 'en','vi'. Mặc định tự nhận diện.")
    p.add_argument("--clip-model", default="clip-ViT-B-32-multilingual-v1")
    p.add_argument("--model-cache-dir", default=None,
                   help="Thư mục lưu model tải về (đặt sang ổ nhiều dung lượng nếu ổ C gần đầy).")

    p.add_argument("--no-subtitles", action="store_true", help="Không thêm phụ đề.")
    p.add_argument("--allow-image-reuse", action="store_true", help="Cho phép dùng lại ảnh.")
    p.add_argument("--transition", default=None, help="Tên transition giữa ảnh, vd 'dissolve'.")

    p.add_argument("--list-draft-folder", action="store_true", help="In thư mục draft CapCut dò được rồi thoát.")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_draft_folder:
        folder = find_capcut_draft_folder()
        print(folder if folder else "Không tìm thấy thư mục draft CapCut.")
        return 0

    missing = [name for name, val in (("--images", args.images), ("--voiceover", args.voiceover)) if not val]
    if missing:
        print(f"Thiếu tham số bắt buộc: {', '.join(missing)}", file=sys.stderr)
        return 2

    config = ProjectConfig(
        images_dir=args.images,
        voiceover_path=args.voiceover,
        script_path=args.script,
        draft_name=args.draft_name,
        draft_root=args.draft_root,
        output_dir=args.output_dir,
        width=args.width,
        height=args.height,
        fps=args.fps,
        whisper_model=args.whisper_model,
        language=args.language,
        clip_model=args.clip_model,
        model_cache_dir=args.model_cache_dir,
        add_subtitles=not args.no_subtitles,
        allow_image_reuse=args.allow_image_reuse,
        transition=args.transition,
    )

    try:
        result = run(config)
    except Exception as exc:
        print(f"\nLỖI: {exc}", file=sys.stderr)
        return 1

    print("\n" + result.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
