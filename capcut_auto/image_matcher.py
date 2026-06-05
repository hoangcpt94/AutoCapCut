"""Ghép ảnh khớp với từng đoạn voiceover theo ngữ nghĩa.

Dùng sentence-transformers với model CLIP đa ngôn ngữ
('clip-ViT-B-32-multilingual-v1') để mã hóa ảnh và text vào cùng không gian
vector, rồi so khớp bằng cosine similarity.

Thuật toán gán mặc định: tối ưu toàn cục (Hungarian) nếu số ảnh >= số đoạn,
nếu không thì greedy có/không cho phép tái sử dụng ảnh.
"""

from __future__ import annotations

import hashlib
import os
from typing import List, Optional, Tuple

import numpy as np

from .transcriber import Segment


class ImageMatcher:
    """Bọc model CLIP đa ngôn ngữ để mã hóa ảnh và text."""

    def __init__(self, model_name: str = "clip-ViT-B-32-multilingual-v1", cache_dir: Optional[str] = None,
                 model_cache_dir: Optional[str] = None):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.model_cache_dir = model_cache_dir
        self._text_model = None
        self._img_model = None

    def _load(self) -> None:
        if self._text_model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "Thiếu sentence-transformers. Cài bằng: pip install sentence-transformers"
            ) from exc

        # Model text đa ngôn ngữ map vào không gian CLIP.
        self._text_model = SentenceTransformer(self.model_name, cache_folder=self.model_cache_dir)
        # Model ảnh CLIP gốc (cùng không gian vector với text model trên).
        self._img_model = SentenceTransformer("clip-ViT-B-32", cache_folder=self.model_cache_dir)

    # ---- Encode ----
    def encode_texts(self, texts: List[str]) -> np.ndarray:
        self._load()
        emb = self._text_model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return emb

    def encode_images(self, image_paths: List[str]) -> np.ndarray:
        self._load()
        from PIL import Image

        cached: dict = {}
        cache_file = None
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
            key = hashlib.md5(("|".join(sorted(image_paths))).encode("utf-8")).hexdigest()
            cache_file = os.path.join(self.cache_dir, f"img_emb_{key}.npz")
            if os.path.isfile(cache_file):
                data = np.load(cache_file, allow_pickle=True)
                stored = list(data["paths"])
                if stored == image_paths:
                    return data["emb"]

        images = []
        for p in image_paths:
            img = Image.open(p).convert("RGB")
            images.append(img)
        emb = self._img_model.encode(images, convert_to_numpy=True, normalize_embeddings=True)
        for img in images:
            img.close()

        if cache_file is not None:
            np.savez(cache_file, paths=np.array(image_paths, dtype=object), emb=emb)
        return emb


def _similarity_matrix(seg_emb: np.ndarray, img_emb: np.ndarray) -> np.ndarray:
    """Ma trận cosine similarity [n_segments x n_images] (vector đã chuẩn hóa)."""
    return seg_emb @ img_emb.T


def assign_images(
    segments: List[Segment],
    image_paths: List[str],
    matcher: ImageMatcher,
    *,
    allow_reuse: bool = False,
) -> List[Tuple[int, float]]:
    """Gán mỗi đoạn một ảnh.

    Returns:
        Danh sách (image_index, score) theo thứ tự đoạn.
    """
    if not image_paths:
        raise ValueError("Không có ảnh nào trong thư mục.")

    seg_texts = [s.text for s in segments]
    seg_emb = matcher.encode_texts(seg_texts)
    img_emb = matcher.encode_images(image_paths)
    sim = _similarity_matrix(seg_emb, img_emb)  # [n_seg, n_img]

    n_seg, n_img = sim.shape

    if allow_reuse or n_img < n_seg:
        # Greedy: mỗi đoạn lấy ảnh điểm cao nhất (có thể trùng).
        return [(int(np.argmax(sim[i])), float(np.max(sim[i]))) for i in range(n_seg)]

    # Đủ ảnh và không tái sử dụng -> gán tối ưu toàn cục, không trùng ảnh.
    return _optimal_assignment(sim)


def _optimal_assignment(sim: np.ndarray) -> List[Tuple[int, float]]:
    """Gán 1-1 tối ưu (cực đại tổng similarity). Dùng Hungarian nếu có scipy."""
    n_seg = sim.shape[0]
    try:
        from scipy.optimize import linear_sum_assignment

        # Hungarian tối thiểu hóa cost -> dùng cost = -sim
        rows, cols = linear_sum_assignment(-sim)
        assignment = [(0, 0.0)] * n_seg
        for r, c in zip(rows, cols):
            assignment[r] = (int(c), float(sim[r, c]))
        return assignment
    except ImportError:
        # Fallback greedy không trùng ảnh.
        return _greedy_unique(sim)


def _greedy_unique(sim: np.ndarray) -> List[Tuple[int, float]]:
    """Greedy gán không trùng ảnh: chọn cặp điểm cao nhất lần lượt."""
    n_seg, n_img = sim.shape
    assignment: List[Optional[Tuple[int, float]]] = [None] * n_seg
    used_imgs: set = set()
    # Tạo danh sách (score, seg, img) sắp xếp giảm dần
    triples = [
        (sim[i, j], i, j)
        for i in range(n_seg)
        for j in range(n_img)
    ]
    triples.sort(reverse=True)
    assigned_segs: set = set()
    for score, i, j in triples:
        if i in assigned_segs or j in used_imgs:
            continue
        assignment[i] = (int(j), float(score))
        assigned_segs.add(i)
        used_imgs.add(j)
        if len(assigned_segs) == n_seg:
            break
    # Đoạn nào còn sót (do hết ảnh) thì lấy ảnh điểm cao nhất bất kỳ
    for i in range(n_seg):
        if assignment[i] is None:
            assignment[i] = (int(np.argmax(sim[i])), float(np.max(sim[i])))
    return [a for a in assignment]  # type: ignore
