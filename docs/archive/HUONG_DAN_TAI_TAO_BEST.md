# Hướng dẫn cho Nguyen: làm cho bài 0,3193 tái tạo được từ repo

> Người giao: Sơn · Ngày: 26/10/2026 · Ước tính: 30–60 phút
> Làm xong việc này trước khi thử thí nghiệm mới. Đây là "bảo hiểm" cho vòng private.

## 1. Vì sao cần làm

Bài tốt nhất hiện tại (**exp-040, id 7095, LB 0,3193**) được tạo từ chuỗi:

```
results/D_wide.jsonl  →  dyn_cut.py --mean 180 --vi-share 0.7 --lo 80 --hi 400  →  make_submission.py --chunk-chars 4000:400 --compress lzma-xl
```

Khi review repo thì phát hiện:

- **Không có chỗ nào ghi lệnh tạo `results/D_wide.jsonl`.** Chỉ biết đó là "300 Việt + 130 Trung" (docstring `qwen_rerank.py`), còn trọng số (`--weights`) và `--rrf-k` thì không rõ.
- Lệnh trong `docs/PROGRESS.md` **thiếu tham số**: `dyn_cut.py` thiếu `--out`, `make_submission.py` thiếu `--docs` và `--name`.
- `D_wide.jsonl` và file đầu ra của `dyn_cut` **chỉ nằm trên máy của Nguyen** (`E:\project_r2ai\results\`), không có trong repo và không có trên máy Sơn.

**Rủi ro:** vòng private (01–04/11) chỉ có **5 lượt nộp tổng cộng**. Nếu máy Nguyen gặp sự cố, hoặc quên lệnh, thì không ai dựng lại được cấu hình tốt nhất.

**Mục tiêu:** từ repo + dữ liệu (`clean/`, `emb/`, `results/run_*.jsonl`), bất kỳ ai cũng tạo lại được **đúng file JSON** đã nộp ở id 7095.

## 2. Các bước

### Bước 1: tìm lại lệnh đã tạo `D_wide.jsonl`

Thử lần lượt các nguồn sau:

1. **Lịch sử lệnh PowerShell:**
   ```powershell
   Select-String -Path (Get-PSReadLineOption).HistorySavePath -Pattern "D_wide"
   ```
2. **Lịch sử Git Bash** (nếu dùng): `grep -n "D_wide" ~/.bash_history`
3. **Thư mục `logs/`** và **phiên Claude Code** đã tạo ra file này: tìm chuỗi `--out D_wide`.
4. **Ngày giờ tạo file** `results\D_wide.jsonl`, đối chiếu với nhật ký trong `docs/EXPERIMENTS.md` (exp-038, 26/10).

Nếu không tìm được thì **suy ra rồi kiểm chứng** ở Bước 2. Ứng viên khả dĩ nhất là cấu hình của exp-029/030 với hạn mức rộng:

```powershell
python search_docs.py --only-fuse --quota 300,130,0 --weights bm25_vi=0.33,dense_vi_vimax=0,dense_vi_viprf=0,dense_vi_zhprf=0,dense_hyde_vi=0,dense_hyde_zh=0,bm25_zh=0.3,bm25_en=0 --rrf-k 60 --out D_wide_check
```

Các biến thể cần thử nếu không khớp: `bm25_zh=0` (exp-026), `--rrf-k 100` (exp-030).

> ⚠️ Nhớ đặt **`=0` cho mọi lượt không dùng** (vimax, prf, hyde). `fuse()` gộp **mọi** file `results/run_*.jsonl` đang có trên máy với trọng số mặc định 1.

### Bước 2: kiểm chứng lệnh vừa tìm được

So file vừa tạo với file gốc. **Phải giống hệt** cả tài liệu lẫn thứ tự:

```powershell
python -c "import json; a=[json.loads(l)['doc_ids'] for l in open('results/D_wide.jsonl',encoding='utf-8')]; b=[json.loads(l)['doc_ids'] for l in open('results/D_wide_check.jsonl',encoding='utf-8')]; print('KHOP' if a==b else f'KHAC: {sum(x!=y for x,y in zip(a,b))}/{len(a)} cau')"
```

Chỉ khi in ra `KHOP` mới sang bước sau.

### Bước 3: tái tạo file nộp và so với bản đã nộp

1. Tải lại bản đã nộp: trên leaderboard → My Submissions → **id 7095** → tải `prediction_result.zip`. Trong đó có đúng file JSON đã nộp.
2. Chạy đủ chuỗi lệnh, **ghi rõ mọi tham số**:
   ```powershell
   python dyn_cut.py --docs results/D_wide.jsonl --mean 180 --vi-share 0.7 --lo 80 --hi 400 --out results/DC_mean180.jsonl
   python make_submission.py --docs results/DC_mean180.jsonl --chunk-chars 4000:400 --compress lzma-xl --name sub_best_7095
   ```
   (Nếu tên file `--out` hay `--name` lúc đó khác, cứ dùng tên mới, miễn là ghi lại.)
3. So **nội dung JSON**, không so file ZIP, vì ZIP chứa cả ngày giờ nên luôn khác:
   ```powershell
   python -c "import json,zipfile; a=json.load(open('submissions/sub_best_7095.json',encoding='utf-8')); z=zipfile.ZipFile('prediction_result.zip'); b=json.loads(z.read([n for n in z.namelist() if n.endswith('.json')][0])); print('KHOP' if a==b else 'KHAC')"
   ```
   Lưu ý: `make_submission.py` dùng `results/chunk_cache.pkl`. Nếu cache trên máy khác với lúc nộp thì chunk có thể lệch nhẹ. Trường hợp đó vẫn chấp nhận được nếu `relevant_docs` khớp 100%.

### Bước 4: đưa vào repo

1. **Ghi đủ chuỗi lệnh** vào `docs/EXPERIMENTS.md` (dòng exp-038/040) và mục "Điểm tốt nhất" trong `docs/PROGRESS.md`: từ `search_docs.py` → `dyn_cut.py` → `make_submission.py`, đủ mọi tham số.
2. **Commit hai file danh sách** (vài MB, an toàn dưới giới hạn 100MB của GitHub) để không phụ thuộc vào `run_*.jsonl` trên một máy:
   - thêm vào `.gitignore`, ngay dưới dòng `!results/queries_translated.jsonl`:
     ```
     !results/D_wide.jsonl
     !results/DC_mean180.jsonl
     ```
3. Commit và push lên nhánh `nguyen`:
   ```powershell
   git add .gitignore docs/EXPERIMENTS.md docs/PROGRESS.md results/D_wide.jsonl results/DC_mean180.jsonl
   git commit -m "[docs] ghi đủ lệnh tái tạo exp-040 (0,3193) + đưa D_wide/DC_mean180 vào repo"
   git push
   ```

## 3. Xong khi

- [ ] Lệnh tạo `D_wide.jsonl` được ghi lại, và Bước 2 in `KHOP`
- [ ] Chuỗi lệnh đầy đủ có trong `docs/EXPERIMENTS.md` và `docs/PROGRESS.md`
- [ ] Bước 3: `relevant_docs` khớp 100% với bản đã nộp id 7095
- [ ] `results/D_wide.jsonl` và `results/DC_mean180.jsonl` đã có trên GitHub (nhánh `nguyen`)

## 4. Việc sau (không làm trong lượt này)

Sơn đã làm (26/10), xem chi tiết ở mục "Thay đổi 26/10" trong `docs/PROGRESS.md`:

- ✅ **Trọng số mặc định của `search_docs.py`** = cấu hình tốt nhất, các lượt thử nghiệm mặc định tắt. **Lưu ý:** `--weights` giờ ghi đè từng lượt lên mặc định, không còn thay thế toàn bộ.
- ✅ **`build_submission.sh`** chạy được trên cả Windows lẫn Linux, độ dài chunk mặc định `4000:400`.
- **Hướng cải thiện từ buổi mentor 22/10:** rerank theo **đoạn khớp nhất** thay vì đầu bài (36,6% bài Việt có đoạn khớp nằm sau ký tự 2.000), và gộp thêm một mô hình embedding thứ hai.
