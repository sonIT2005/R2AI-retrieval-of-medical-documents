# PLAN — backlog đã xếp hạng
Ưu tiên = (Kỳ vọng × Tự tin) / Chi phí. Mục "todo" đầu tiên = việc tiếp theo.
Nguồn: setup | error-analysis | council-rXX/<model> | debate | ý tưởng của tôi | exp-XXX

## Mốc
- M1: vượt 0,2 (hạng ~11) — hạn 23/10
- M2: vượt 0,3 (top 6) — hạn 28/10
- M3: chốt cấu hình private (5 bài tổng) — 31/10; public đóng 31/10 07:00

## Backlog
| ID | Thí nghiệm / việc | Nguồn | Kỳ vọng | Tự tin | Chi phí | Trạng thái |
|---|---|---|---|---|---|---|
| P7 | Dựng lại bài trộn 40/50/10 trên máy này + chunk L=4.000: `search_docs.py --quota 40,50,10` rồi `make_submission.py --docs results/docs_fused_40-50-10.jsonl --chunk-chars 4000` | exp-005 | 0,16 → ~0,22 | cao | S | đang chạy |
| P8 | Bỏ 10 tài liệu Anh (P=0) và tăng N: quét 60/90/0, 80/120/0 với L=4.000; đọc precision biên từng nhóm | exp-001…003, README | +0,02…+0,05 | vừa | S | todo |
| P9 | L lớn hơn (6.000 / 8.000 / nguyên văn) — P_chunk/P_doc đang 0,89 ở L=4.000 | exp-004/005 | +0,005…+0,015 | vừa | S | todo |
| P10 | Trọng số RRF giữa dense và BM25 trong nhóm Việt (dense đang tốt hơn BM25 rõ rệt) | exp-001 | ? | vừa | S (--only-fuse) | todo |
| P5 | Đếm cụm gần trùng lặp (MinHash) | council-r01/M3-C | ? | thấp | M | todo |
| P6 | Reranker bge-reranker-v2-m3 / Qwen3-8B lọc trên top-150 | council-r01 | +0,03…+0,08 | vừa | L | todo |

## Đã loại (và lý do)
- P1 "BM25 Việt thuần" — exp-001…003: P_doc chỉ 0,10–0,16, kém bài trộn. Giả thuyết "nhãn sinh từ BM25 của BTC" dựa
  trên dòng "BM25 Baseline" — đó là TÊN TÀI KHOẢN BTC, nhiều khả năng là bài thử bộ chấm.
- P4 "BM25 full text / tách từ" — chỉ có ý nghĩa nếu P1 đúng.
- Dùng doc_id vàng từng câu từ file chấm để tối ưu offline — dò đáp án, vi phạm luật.
- Nộp lại file cũ để "đo nhiễu" — bộ chấm tất định, phí slot.
