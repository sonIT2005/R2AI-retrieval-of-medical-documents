# SYNTHESIS — council round_03 (2026-10-24)
8 model vòng 1 (6 trả lời), vòng 2 chỉ DeepSeek — **OpenRouter hết tín dụng (HTTP 402)**: cần nạp thêm trước lần họp sau.

## Đo kiểm của phiên chính (trước khi tin hội đồng)
- ViHealthQA test (2.013 câu, hỏi đáp y khoa Việt) — chỉ để chọn model: BGE-M3 R@10 0,824 > e5-large-instruct 0,793 >
  Qwen3-Embedding-0.6B 0,788. Qwen3-0.6B còn chậm gấp 4 (13 giờ cho corpus) → KHÔNG đổi embedding.
- Trùng lặp: 6.182 nhóm (13.499 tài liệu, 1,2% corpus); bài 0,3018 chỉ thiếu TB 0,9 bản sao/câu → lợi rất nhỏ.

## Đề xuất (đã kiểm chứng)
| Đề xuất | Của | Nhãn | Việc |
|---|---|---|---|
| Thêm tiêu đề vào index | Grok-A | ĐÃ LÀM (embed_corpus.doc_input ghép title; BM25 dùng title+text) | — |
| Bản sao URL nằm ngoài danh sách | Grok-B, MiMo-B | hợp lệ nhưng nhỏ (0,9/câu) | ghép vào bài tổng hợp sau |
| PRF Rocchio trên vector | Kimi-A | hợp lệ — prf.py; top-50 đổi 28% (Việt) / 44% (Trung) | B3 (thay), B4 (thêm) |
| Số tài liệu theo từng câu (khuỷu điểm RRF) | MiMo-A, GPT-A | hợp lệ — dyn_cut.py, ngưỡng tương đối so với top-1 | B6 |
| Quét N 200/150 | DeepSeek-B | hợp lệ | B1, B2 |
| BGE-M3 sparse; doc2query; fine-tune nhãn giả | GPT-B, Kimi-B/C | tốn kém, để sau | — |
| Mở rộng pool 300 → 1.000 | DeepSeek-A | hợp lệ, nhỏ | — |

## Hàng đợi nộp 25/10 (đã dựng sẵn trong submissions/)
B1 200 tài liệu · B2 150 · B3 PRF thay dense · B4 PRF thêm · B5 k=100 + bỏ bm25_zh · B6 số tài liệu theo câu (TB 250).
Sau khi có điểm: ghép các yếu tố thắng (4 lượt còn lại).
