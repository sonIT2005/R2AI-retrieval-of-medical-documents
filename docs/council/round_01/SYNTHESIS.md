# SYNTHESIS — council round_01 (2026-10-22)
Hội đồng: DeepSeek V4 Pro (root_cause), Grok 4.7 (red_team), MiMo v2.6 (data_detective), Qwen 3.8 Max (competition_veteran).
2 vòng, 4/4 model trả lời. ~277k token vào / ~103k token ra, 41 nguồn trích.

> **Đính chính sau họp (22/10):** README mới của đội ghi bài 0,1606 = **40 Việt + 50 Trung + 10 Anh** (không phải 60/40/0
> như brief giả định). Chỉ 40% tài liệu là tiếng Việt và 10% là tiếng Anh (P = 0) → càng củng cố giả thuyết "quota làm loãng".

## Cảnh báo cần biết NGAY
1. **BM25 của BTC (P_doc 0,88) gần như chắc là nguồn sinh nhãn.** Cả 4 model đồng ý. Pipeline đang trộn RRF với dense
   + giữ cứng 40 suất Trung → ở 100 tài liệu chỉ trúng ~18, trong khi BM25 của BTC trúng ~27 chỉ với ~30 tài liệu.
2. **Chunk 1.000 ký tự là lỗ hổng lớn nhất**: overlap chia cho |g| → chunk dài không bị phạt; R_chunk/R_doc chỉ 0,34.
3. Không có bug leakage. Không có bug chấm local (vì chưa có eval local).

## Bảng đề xuất (đã kiểm chứng)
| Đề xuất | Ủng hộ (điểm Borda) | Nhãn code | Bằng chứng | (Kỳ vọng × tự tin)/chi phí |
|---|---|---|---|---|
| **1 chunk dài/tài liệu (L=2k–4k ký tự), giữ nguyên tập tài liệu** (M3-A, M1-B, M4-B) | 8+3, cả 4 đồng ý | **hợp lệ** — chỉ cần thêm cờ độ dài chunk (`MAX_CHARS` cứng ở make_submission.py:29, chọn 1 chunk ở :154) | LCS(c,g)/|g| không giảm khi c dài ra; đội #1 P_chunk 0,993 ≈ P_doc 0,995; #3–#5 F2_chunk ≈ F2_doc | +0,05…+0,10 · tự tin cao · S |
| **bm25_vi thuần, N = 30/60/100** (M1-A, M4-A, M2-C) | 6, cả 4 đồng ý | **hợp lệ, KHÔNG cần sửa code**: `--only-fuse --quota N,0,0 --weights dense_vi_vi=0` (lượt trọng số 0 bị bỏ ở search_docs.py:216) | H≈18@100 (đội) vs H≈27@30 (BTC) | +0,08…+0,25 · vừa · S |
| **Bỏ quota, xếp hạng toàn cục, chọn N theo precision biên ≥ F2/5** (M3-B) | 5 | hợp lệ; cần chuẩn hoá điểm vi/zh (code mới nhỏ) | Toán: F2 = 5H/(4G+N) → thêm tài liệu có lợi khi p > F2/5 (kiểm lại trên LB: BTC 0,561 vs 0,559) | +0,05…+0,15 · vừa · S–M |
| BM25 full text (bỏ cắt 10k ký tự), BM25 cấp chunk → max về tài liệu, tách từ tiếng Việt (M4-C, M1-C) | chỉ làm nếu P@30 < 0,6 | hợp lệ (search_docs.py:38 `BM25_MAX_CHARS=10000`, :122) | — | ? · thấp–vừa · M |
| Mở rộng cụm gần trùng lặp (M3-C) | 0 phiếu | chưa kiểm; đếm offline trước (MinHash top-40) | |G| trung vị 60 lớn bất thường | +0,05…+0,15 · vừa · M |

## Đề xuất bị loại / sai giả định
- **"HashingVectorizer không có IDF → không phải BM25" (Grok)**: SAI. Code tự tính IDF Okapi (search_docs.py:143) và độ bão hoà
  k1/b (:147), `norm=None` (:55). 2^23 bucket → va chạm không đáng kể với từ vựng âm tiết. BM25 hiện tại là BM25 thật.
- **Dùng doc_id vàng từng câu trong file chấm chi tiết để đo recall@300 offline (MiMo-A)**: LOẠI — là dò đáp án, vi phạm luật
  (Grok và Qwen cũng phản đối). Chỉ được dùng thống kê tổng quát.
- **"Nộp lại đúng file 0,1606 để đo nhiễu" (MiMo, DeepSeek, Qwen)**: LÃNG PHÍ SLOT — bộ chấm tất định trên cùng 600 câu public,
  nộp lại cho đúng số cũ. Nhiễu thật là chênh public↔private; chỉ ước được bằng bootstrap trên điểm TỪNG CÂU (nếu file chấm có).
- **Nộp nguyên văn bản làm chunk (DeepSeek vòng 1)**: hội đồng tự rút lại. Đo local: LCS Python thuần ~0,24 s/cặp ở 2.000 token
  → ~1 giờ cho 600 câu × 25 cặp; 750 token → ~20 phút. Kích thước file: 1.200 câu × 100 tài liệu × 2.000 ký tự ≈ 300 MB JSON.

## Bất đồng đáng chú ý
- **Giữ tiếng Trung?** Qwen: P_zh 0,16 > ngưỡng F2/5 ≈ 0,05–0,11 → giữ, nhưng ở ĐUÔI danh sách toàn cục, không quota. MiMo/Grok:
  bỏ trong bài chẩn đoán, chỉ thêm lại nếu tăng H ≥ 5% ở cùng N. → Thống nhất: chẩn đoán bằng Việt thuần trước, thử Trung sau.
- **Bao nhiêu tài liệu?** Qwen: đang nộp quá ÍT (ngưỡng thấp). Grok: chỉ đúng khi ranker đã có P cao. → Quét N trên ranker mới.
- **Rủi ro "lách luật" khi chunk dài**: luật cho tự thiết kế phân đoạn; Qwen khuyên giữ span liên tục ≤ 4.000 ký tự + giữ 1 cấu hình
  bảo thủ (L ≈ 2.000) cho private, và hỏi BTC bằng văn bản về trần độ dài / thời gian chấm.

## Đề xuất cho PLAN (chưa triển khai)
1. P1 — bm25_vi thuần N=30/60/100 (3 bài, chunk như cũ) → đọc P@N và precision biên.
2. P2 — thêm cờ `--chunk-chars`; 1 chunk/tài liệu L=2.000 và 4.000 trên tập tài liệu tốt nhất (2 bài).
3. P3 — ghép ranker + L tốt nhất; quét N tiếp (150/200) theo precision biên; thử Trung ở đuôi danh sách toàn cục.
4. P4 — nếu P@30 < 0,6: BM25 full text / cấp chunk / tách từ.
5. P5 — đếm cụm gần trùng lặp offline; reranker/LLM chỉ khi F2_doc ≥ 0,45.
