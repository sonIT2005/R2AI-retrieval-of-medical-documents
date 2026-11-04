# Bảng xếp hạng đồng thuận — round_02

| Hạng | ID | Đề xuất | Của | Điểm | Người bầu |
|---|---|---|---|---|---|
| 1 | M4-A | Xoá tiếng Anh + 3 bài nộp chẩn đoán (VI-only, ZH-only, dò độ sâu N=200) | glm | 8 | M2, M3, M1 |
| 2 | M1-A | Tách rời `N_doc` khỏi `N_chunk` + Phá hạn mức 40 Việt + Gộp điểm có trọng số & Phân bổ `L` bậc thang | gemini | 7 | M4, M2, M3 |
| 3 | M2-C | Thêm vector phần sau cho tài liệu dài | openai | 2 | M1 |
| 4 | M3-A | Chấm điểm tài liệu bằng max-sim cấp chunk trên pool ứng viên (không cần re-index toàn corpus) | kimi | 2 | M4 |
| 5 | M4-B | Dùng lại embedding chunk của bước 5 làm tín hiệu xếp hạng tài liệu (max-sim vào RRF) — không build index mới | glm | 2 | M2 |
| 6 | M1-B | Rerank đa ngữ `BAAI/bge-reranker-v2-m3` trên Top-250 + Định tâm Chunk bằng cửa sổ trượt lai + Cắt ngưỡng động | gemini | 1 | M4 |
