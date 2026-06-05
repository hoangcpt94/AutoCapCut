# CapCut Auto — Ghép ảnh khớp voiceover

Tool tự động ghép ảnh trong một thư mục với từng đoạn voiceover theo **ngữ nghĩa**,
rồi sinh ra một **draft CapCut** (mở lên chỉnh sửa/export tiếp). Hỗ trợ voiceover
**đa ngôn ngữ** (Anh, Việt, hoặc bất kỳ).

## Cách hoạt động

```
voiceover.mp3 ─┐
               ├─► [1] Whisper: tách timing từng đoạn
script.txt   ──┘         │
                         ▼
folder ảnh ──► [2] CLIP đa ngôn ngữ: phân tích nội dung ảnh
                         │
                         ▼
              [3] Ghép ảnh ↔ đoạn theo ngữ nghĩa (cosine similarity)
                         │
                         ▼
              [4] pycapcut: sinh draft (ảnh + audio + phụ đề)
```

1. **Whisper** (`faster-whisper`): nhận diện voiceover, lấy mốc thời gian từng đoạn.
2. **Script** (tùy chọn): nếu có file script, dùng làm nội dung phụ đề chuẩn,
   timing vẫn lấy từ Whisper.
3. **CLIP đa ngôn ngữ** (`sentence-transformers`): mã hóa ảnh và text vào cùng
   không gian vector, ghép ảnh khớp nhất cho từng đoạn. Khi đủ ảnh, dùng thuật
   toán gán tối ưu toàn cục (Hungarian) để không lặp ảnh.
4. **pycapcut**: dựng `draft_content.json` với track ảnh, track voiceover, track phụ đề.

## Cài đặt

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Lần chạy đầu sẽ tự tải model Whisper và CLIP về máy (vài trăm MB).

## Sử dụng

Tạo draft thẳng vào thư mục CapCut (tự dò vị trí):

```powershell
.venv\Scripts\python.exe -m capcut_auto `
  --images "D:\project\images" `
  --voiceover "D:\project\vo.mp3" `
  --script "D:\project\script.txt" `
  --draft-name "video_moi"
```

Hoặc xuất ra thư mục riêng để kiểm tra trước (không đụng CapCut):

```powershell
.venv\Scripts\python.exe -m capcut_auto `
  --images "D:\project\images" `
  --voiceover "D:\project\vo.mp3" `
  --output-dir ".\out_draft"
```

Sau khi chạy xong, mở CapCut → draft mới sẽ xuất hiện trong danh sách dự án.

## Tham số chính

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `--images` | (bắt buộc) | Thư mục chứa ảnh |
| `--voiceover` | (bắt buộc) | File audio voiceover |
| `--script` | none | File script .txt (tùy chọn) |
| `--draft-name` | auto_capcut_project | Tên draft CapCut |
| `--draft-root` | tự dò | Thư mục draft CapCut |
| `--output-dir` | none | Ghi ra đây thay vì thư mục CapCut |
| `--width/--height` | 1080 / 1920 | Khung hình (mặc định dọc) |
| `--fps` | 30 | Khung hình/giây |
| `--whisper-model` | base | tiny/base/small/medium/large-v3 |
| `--language` | tự nhận diện | Mã ngôn ngữ vd `en`, `vi` |
| `--clip-model` | clip-ViT-B-32-multilingual-v1 | Model ghép ảnh-text |
| `--no-subtitles` | tắt | Bỏ phụ đề |
| `--allow-image-reuse` | tắt | Cho phép dùng lại ảnh |
| `--transition` | none | Transition giữa ảnh, vd `dissolve` |

Kiểm tra thư mục draft CapCut dò được:

```powershell
.venv\Scripts\python.exe -m capcut_auto --list-draft-folder
```

## Giới hạn

- CLIP ghép tốt với nội dung **cụ thể** (biển, người, vật...), kém với nội dung
  trừu tượng/ẩn dụ. Tool sinh draft để bạn tinh chỉnh tay, không phải bản cuối 100%.
- CapCut không có API chính thức; format draft phụ thuộc phiên bản CapCut.
- Lần chạy đầu chậm do tải model; các lần sau dùng cache trong `.capcut_auto_cache`.

## Kiểm thử

Test phần không cần model nặng (logic + dựng draft):

```powershell
.venv\Scripts\python.exe tests\test_offline.py
```
