# CapCut Auto — Ghép ảnh theo anchor khớp voiceover

Tool tự động đặt ảnh vào đúng thời điểm trên timeline theo lời thoại, rồi sinh ra
một **draft CapCut** để chỉnh sửa/export tiếp. Hỗ trợ voiceover **đa ngôn ngữ**.

Bạn cung cấp sẵn mapping `ảnh ↔ cụm từ` (`anchor_phrase`). Tool dùng Whisper lấy
mốc thời gian **từng từ**, căn cụm từ đó vào đúng thời điểm nó được đọc, rồi đặt
ảnh tương ứng. Mỗi ảnh hiển thị từ lúc anchor của nó bắt đầu, kéo dài tới khi
anchor kế tiếp bắt đầu (ảnh cuối kéo tới hết voiceover).

```
voiceover ──► [1] Whisper: word-timestamps (mốc từng từ)
mapping   ──► [2] forced-align từng anchor_phrase vào timeline
ảnh       ──► [3] đặt ảnh theo vị trí anchor, kéo dài tới anchor kế tiếp
                         │
                         ▼
              [4] pycapcut: sinh draft (ảnh + audio + phụ đề)
```

## Cấu trúc input một tập

```
episode_01/
├── mapping.jsonl     # cặp ảnh <-> anchor_phrase
├── voiceover.wav     # file voiceover (mp3/wav/m4a/...)
└── images/           # thư mục ảnh (hoặc để ảnh thẳng trong tập)
    ├── 01.png
    ├── 02.png
    └── ...
```

File `mapping.jsonl` — mỗi dòng một object (cũng chấp nhận JSON array hoặc nhiều
object dính liền nhau):

```json
{"image_file":"1.png","anchor_phrase":"What if you fell into a black hole?"}
{"image_file":"2.png","anchor_phrase":"you'd be crushed to a dot in a heartbeat"}
{"image_file":"3.png","anchor_phrase":"Screaming. Gone."}
{"image_file":"4.png","anchor_phrase":"It's terrifying. It's dramatic."}
{"image_file":"5.png","anchor_phrase":"And it's wrong."}
```

- `anchor_phrase` chỉ cần là một **cụm từ thật** xuất hiện trong lời thoại — không
  cần trùng 100%, tool fuzzy-match nên chịu được sai khác chính tả/nhận diện.
- Các anchor phải theo đúng **thứ tự thời gian** chúng được đọc.
- `image_file` khớp theo **số ở đầu tên file**: mapping ghi `01.png` vẫn khớp đúng
  với ảnh thật tên dài như `01_black_hole_intro.png` (đuôi file không cần trùng).

## Cài đặt

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Lần chạy đầu sẽ tự tải model Whisper về máy (vài chục–vài trăm MB tùy model).

## Sử dụng

Tạo draft thẳng vào thư mục CapCut (tự dò vị trí):

```powershell
.venv\Scripts\python.exe -m capcut_auto --input-dir "episodes\episode_01" --draft-name "video_moi"
```

Hoặc xuất ra thư mục riêng để xem trước (không đụng CapCut):

```powershell
.venv\Scripts\python.exe -m capcut_auto --input-dir "episodes\episode_01" --output-dir ".\out_draft"
```

Sau khi chạy xong, mở CapCut → draft mới sẽ xuất hiện trong danh sách dự án.

Tạo nhanh khung một tập mới:

```powershell
.venv\Scripts\python.exe new_episode.py "episodes\episode_06_xxx" --slots 18
```

Quy trình sản xuất chi tiết: xem `episodes\README.md`.

## Tham số

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `--input-dir` | (bắt buộc) | Thư mục một tập (mapping + voiceover + ảnh) |
| `--anchor-min-score` | 0.45 | Ngưỡng fuzzy-match coi như tìm thấy anchor (0..1) |
| `--draft-name` | auto_capcut_project | Tên draft CapCut |
| `--draft-root` | tự dò | Thư mục draft CapCut |
| `--output-dir` | none | Ghi ra đây thay vì thư mục CapCut |
| `--width/--height` | 1920 / 1080 | Khung hình (mặc định ngang 16:9) |
| `--fps` | 30 | Khung hình/giây |
| `--whisper-model` | base | tiny/base/small/medium/large-v3 |
| `--language` | tự nhận diện | Mã ngôn ngữ vd `en`, `vi` |
| `--model-cache-dir` | mặc định HF | Thư mục lưu model tải về |
| `--no-subtitles` | tắt | Bỏ phụ đề |
| `--transition` | none | Transition giữa ảnh, vd `dissolve` |

Kiểm tra thư mục draft CapCut dò được:

```powershell
.venv\Scripts\python.exe -m capcut_auto --list-draft-folder
```

## Giới hạn

- Độ chính xác phụ thuộc word-timestamp của Whisper. Anchor quá ngắn và lặp lại
  nhiều nơi có thể neo nhầm; chọn cụm từ đặc trưng, dài 3–8 từ.
- Anchor không tìm thấy trong lời thoại sẽ được nội suy thời gian và in cảnh báo.
- CapCut không có API chính thức; format draft phụ thuộc phiên bản CapCut.
- Lần chạy đầu chậm do tải model; các lần sau dùng cache trong `.capcut_auto_cache`.

## Kiểm thử

Test phần logic không cần model nặng (parse mapping + forced-align + dựng segment):

```powershell
.venv\Scripts\python.exe tests\test_offline.py
```
