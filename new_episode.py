"""Tạo nhanh khung một tập mới để dán input vào.

Dùng:
    .venv\\Scripts\\python.exe new_episode.py "episodes\\episode_06_ten_de_tai"
    .venv\\Scripts\\python.exe new_episode.py "episodes\\episode_06" --slots 18

Sinh ra:
    episode_06_ten_de_tai/
    ├── mapping.jsonl     (khung sẵn N dòng, sửa anchor_phrase theo voiceover)
    └── images/           (bỏ ảnh 01.png, 02.png, ... vào)

Tập chỉ cần voiceover + mapping; không dùng script.
"""

from __future__ import annotations

import argparse
import json
import os


def make_episode(path: str, slots: int) -> None:
    images_dir = os.path.join(path, "images")
    os.makedirs(images_dir, exist_ok=True)

    mapping_path = os.path.join(path, "mapping.jsonl")
    if not os.path.isfile(mapping_path):
        with open(mapping_path, "w", encoding="utf-8") as f:
            for i in range(1, slots + 1):
                obj = {
                    "image_file": f"{i:02d}.png",
                    "anchor_phrase": "<cụm từ thật trong lời thoại>",
                }
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        print("mapping:", mapping_path, f"({slots} dòng khung)")
    else:
        print("mapping: đã tồn tại, giữ nguyên.")

    note = os.path.join(images_dir, "PUT_IMAGES_HERE.txt")
    if not os.path.isfile(note):
        with open(note, "w", encoding="utf-8") as f:
            f.write(
                "Bỏ ảnh vào thư mục này, đặt tên đúng như trong ../mapping.jsonl:\n"
                f"01.png, 02.png, ... {slots:02d}.png\n\n"
                "Có thể dùng .jpg/.jpeg/.png/.webp — nhớ sửa đuôi trong mapping.jsonl.\n"
                "Xóa file này sau khi đã thêm ảnh.\n"
            )

    print("\nXong. Các bước:")
    print("  1. Sửa anchor_phrase trong mapping.jsonl theo lời voiceover")
    print("  2. Thu/đặt voiceover -> lưu voiceover.wav vào tập")
    print("  3. Bỏ ảnh vào images/")
    print("  4. Chạy:")
    print(f'     .venv\\Scripts\\python.exe -m capcut_auto --input-dir "{path}" '
          f'--draft-name "{os.path.basename(path.rstrip(os.sep))}"')


def main() -> None:
    p = argparse.ArgumentParser(description="Tạo khung một tập mới.")
    p.add_argument("path", help="Đường dẫn thư mục tập, vd episodes\\episode_06_xxx")
    p.add_argument("--slots", type=int, default=20, help="Số ảnh khung trong mapping (mặc định 20).")
    args = p.parse_args()
    make_episode(args.path, args.slots)


if __name__ == "__main__":
    main()
