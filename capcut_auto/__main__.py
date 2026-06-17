"""CLI cho capcut_auto (chế độ neo).

Ví dụ:
    python -m capcut_auto --input-dir ./episodes/episode_01 --draft-name my_ep
    python -m capcut_auto --input-dir ./episodes/episode_01 --output-dir ./out
"""

from __future__ import annotations

import argparse
import sys

from .config import ProjectConfig, find_capcut_draft_folder
from .pipeline import run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="capcut_auto",
        description="Ghép ảnh theo anchor_phrase khớp voiceover thành draft CapCut.",
    )
    p.add_argument("--input-dir", default=None,
                   help="Thư mục input một tập: chứa mapping ảnh<->anchor_phrase, voiceover và ảnh.")
    p.add_argument("--anchor-min-score", type=float, default=0.45,
                   help="Ngưỡng fuzzy-match coi như tìm thấy anchor (0..1). Mặc định 0.45.")
    p.add_argument("--skip-missing-images", action="store_true",
                   help="Bỏ qua mục mapping không tìm được ảnh (kèm cảnh báo) thay vì báo lỗi.")

    p.add_argument("--draft-name", default="auto_capcut_project", help="Tên draft CapCut.")
    p.add_argument("--draft-root", default=None, help="Thư mục draft CapCut. Mặc định tự dò.")
    p.add_argument("--output-dir", default=None, help="Ghi draft ra đây thay vì thư mục CapCut (để xem trước).")

    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--fps", type=int, default=30)

    p.add_argument("--whisper-model", default="base", help="tiny/base/small/medium/large-v3")
    p.add_argument("--language", default=None, help="Mã ngôn ngữ vd 'en','vi'. Mặc định tự nhận diện.")
    p.add_argument("--model-cache-dir", default=None,
                   help="Thư mục lưu model tải về (đặt sang ổ nhiều dung lượng nếu ổ C gần đầy).")

    p.add_argument("--no-subtitles", action="store_true", help="Không thêm phụ đề.")
    p.add_argument("--transition", default=None, help="Tên transition giữa ảnh, vd 'dissolve'.")

    p.add_argument("--list-draft-folder", action="store_true", help="In thư mục draft CapCut dò được rồi thoát.")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_draft_folder:
        folder = find_capcut_draft_folder()
        print(folder if folder else "Không tìm thấy thư mục draft CapCut.")
        return 0

    if not args.input_dir:
        print("Thiếu tham số bắt buộc: --input-dir", file=sys.stderr)
        return 2

    config = ProjectConfig(
        input_dir=args.input_dir,
        anchor_min_score=args.anchor_min_score,
        skip_missing_images=args.skip_missing_images,
        draft_name=args.draft_name,
        draft_root=args.draft_root,
        output_dir=args.output_dir,
        width=args.width,
        height=args.height,
        fps=args.fps,
        whisper_model=args.whisper_model,
        language=args.language,
        model_cache_dir=args.model_cache_dir,
        add_subtitles=not args.no_subtitles,
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
