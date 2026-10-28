# EXPERIMENTS — nhật ký thí nghiệm
Quy ước: 1 thí nghiệm = 1 thay đổi. Ghi cả thất bại. Kết luận phải trả lời "VÌ SAO".
Local = không có (không có nhãn dev). LB = public 600 câu, bộ chấm tất định (nộp lại cùng file → cùng điểm).

| ID | Ngày | Giả thuyết → thay đổi | Local | Δ vs best | LB (điểm · F2 doc · F2 chunk) | Kết luận | Commit |
|---|---|---|---|---|---|---|---|
| exp-000 | 15/10 | Baseline đội: RRF 8 lượt, quota 40 Việt + 50 Trung + 10 Anh | — | — | 0,1606 · 0,2375 · 0,0837 | best hiện tại | d6d10b7 |
| exp-001 | 22/10 | P1: bm25_vi thuần N=30, chunk ~1.000 ký tự (id 6567) | — | −0,106 | 0,0549 · 0,0975 · 0,0122 | BÁC BỎ "BM25 thuần tốt hơn": P_doc 0,156 | chưa |
| exp-002 | 22/10 | P1: bm25_vi thuần N=60 (id 6568) | — | −0,091 | 0,0701 · 0,1240 · 0,0163 | P_doc 0,125, R_doc 0,153 | chưa |
| exp-003 | 22/10 | P1: bm25_vi thuần N=100 (id 6569) | — | −0,081 | 0,0793 · 0,1392 · 0,0193 | P_doc 0,102, R_doc 0,194 | chưa |
| exp-004 | 22/10 | P2: như exp-002, chunk L=2.000 (id 6570) | — | +0,031 vs exp-002 | 0,1007 · 0,1240 · 0,0775 | XÁC NHẬN: P_chunk/P_doc 0,13 → 0,65 | chưa |
| exp-005 | 22/10 | P2: như exp-002, chunk L=4.000 (id 6571, ZIP 95 MB chấm OK) | — | +0,047 vs exp-002 | 0,1171 · 0,1240 · 0,1101 | XÁC NHẬN: P_chunk/P_doc 0,89, R_chunk/R_doc 0,88 | chưa |
| exp-006 | 23/10 | P7: bài trộn 40/50/10 dựng lại trên máy này + L=4.000, ZIP bzip2 80 MB (id 6585) | — | +0,060 vs exp-000 | 0,2207 · 0,2309 · 0,2104 | chunk dài áp lên bài trộn; bzip2 được chấp nhận | chưa |
| exp-007 | 23/10 | P8a: 40/60/0 (bỏ Anh) + L=4.000 (id 6588) | — | +0,007 vs exp-006 | **0,2280** · 0,2384 · 0,2176 | bỏ Anh có lợi nhẹ — BEST | chưa |
| — | 23/10 | P7 bản deflate 125 MB | — | — | lỗi 413 (Cloudflare chặn > 100 MB), không tính lượt | ràng buộc dung lượng | — |
| exp-008 | 23/10 | council-r02: 200 tài liệu (80/120/0), chunk = đúng 100 chunk của exp-007 (id 6590) | — | +0,017 | 0,2447 · 0,2718 · 0,2176 | P 0,140 R 0,468; precision biên 101–200 ≈ 0,10 | chưa |
| exp-009 | 23/10 | 300 tài liệu (120/180/0), chunk như exp-007 (id 6591) | — | +0,018 | **0,2456** · 0,2736 · 0,2176 | P 0,116 R 0,555; biên 201–300 ≈ 0,068 → gần bão hoà — BEST | chưa |
| exp-010 | 23/10 | S1: như exp-009 nhưng trọng số bm25_vi 1 → 0,33 trong RRF nhóm Việt (id 6594) | — | **+0,028** | **0,2736** · 0,3038 · 0,2434 | P 0,131 R 0,601 — dense tốt hơn BM25 rõ rệt; BEST | chưa |
| — | 24/10 | embed_tail.py: 831.619 cửa sổ phần sau của 537.869 tài liệu Việt (2 giờ 6 phút); dense_vi_vimax trùng top-40 với dense_vi_vi chỉ 47% | — | — | — | — | — |
| exp-011 | 24/10 | T1: như exp-010, nhóm Việt dùng dense_vi_vimax THAY dense_vi_vi (id 6744) | — | −0,042 | 0,2312 · 0,2725 · 0,1900 | BÁC BỎ: điểm max cửa sổ phần sau kéo tài liệu sai lên | chưa |
| exp-012 | 24/10 | T2: dense_vi_vi + dense_vi_vimax cùng trọng số 1 (id 6745) | — | −0,013 | 0,2609 · 0,3022 · 0,2197 | doc ngang, chunk tụt → bỏ vector phần sau | chưa |
| exp-013 | 24/10 | T3: bm25_vi 0,33 → 0,1 (id 6746) | — | −0,013 | 0,2607 · 0,3024 · 0,2190 | doc ngang, chunk tụt: BM25 giúp chọn top-100 có chunk trúng | chưa |
| exp-014 | 24/10 | T4: như exp-010 nhưng hạn mức 150 Việt / 150 Trung (id 6747) | — | +0,004 | 0,2779 · 0,3161 · 0,2398 | nghiêng Việt có lợi cho doc | chưa |
| exp-015 | 24/10 | T5: 180 Việt / 120 Trung (id 6753) | — | +0,010 | 0,2880 · 0,3221 · 0,2539 | doc và chunk cùng tăng | chưa |
| exp-016 | 24/10 | T6: 210 Việt / 90 Trung (id 6754) | — | +0,005 | 0,2934 · 0,3228 · 0,2641 | doc bão hoà, chunk vẫn tăng | chưa |
| exp-017 | 24/10 | T7: 240 Việt / 60 Trung (id 6755) | — | +0,001 | 0,2947 · 0,3188 · 0,2706 | doc giảm nhẹ, chunk tăng → tập doc tối ưu ~210/90 | chưa |
| exp-018 | 24/10 | R1: tập T6, thứ tự trong ngôn ngữ = bge-reranker-v2-m3 (đầu bài 1.500 ký tự) (id 6759) | — | −0,012 vs T6 | 0,2811 · 0,3228 · 0,2393 | BÁC BỎ: reranker chọn top-100 cho chunk kém hơn RRF hiện tại | chưa |
| exp-019 | 24/10 | tập T6, top-100 nhận chunk = 85 Việt + 15 Trung (chunk_quota.py) (id 6760) | — | +0,003 vs T7 | **0,2968** · 0,3228 · 0,2709 | tách hạn mức chunk khỏi hạn mức doc — BEST | chưa |
| exp-020 | 24/10 | R2: tập T6, RRF(thứ tự cũ, reranker) (id 6761) | — | +0,0004 vs T6 | 0,2938 · 0,3228 · 0,2647 | reranker gần như không thêm gì → bỏ | chưa |

| exp-021 | 24/10 | A1: exp-019 nén LZMA (83 MB) (id 6801) | — | 0 | 0,2968 · 0,3228 · 0,2709 | LZMA được chấp nhận, nhỏ hơn bzip2 ~6% | chưa |
| exp-022 | 24/10 | A2: hạn mức chunk 95/5 (id 6802) | — | −0,0012 | 0,2956 · 0,3228 · 0,2684 | đỉnh ở 85/15 | chưa |
| exp-023 | 24/10 | A3: hạn mức chunk 100/0 (id 6803) | — | −0,0043 | 0,2925 · 0,3228 · 0,2622 | | chưa |
| exp-024 | 24/10 | A4: 350 tài liệu 245/105 (id 6806) | — | −0,005 | 0,2917 · 0,3126 · 0,2709 | biên 301–350 ≈ 0,044 < F2/5 → 300 đã thừa | chưa |
| exp-025 | 24/10 | A5: 400 tài liệu 280/120 (id 6808) | — | −0,011 | 0,2863 · 0,3017 · 0,2709 | | chưa |
| exp-026 | 24/10 | A6: bỏ bm25_zh (id 6809) | — | +0,0002 | **0,2970** · 0,3224 · 0,2716 | ngang (trong nhiễu) — BEST về số | chưa |
| exp-027 | 24/10 | A7: bm25_vi 0,5 (id 6810) | — | −0,004 | 0,2926 · 0,3185 · 0,2667 | 0,33 gần tối ưu (0,1 và 0,5 đều tệ hơn) | chưa |
| exp-028 | 24/10 | A8: RRF k=30 (id 6811) | — | −0,003 | 0,2942 · 0,3201 · 0,2684 | | chưa |
| exp-029 | 24/10 | A9: 250 tài liệu 175/75 (id 6812) | — | **+0,005** | **0,3018** · 0,3328 · 0,2709 | ít tài liệu hơn tốt hơn: P 0,157 R 0,599 — BEST | chưa |
| exp-030 | 24/10 | A10: RRF k=100 (id 6815) | — | +0,0009 | 0,2977 · 0,3251 · 0,2704 | k=100 > 60 > 30 (nhẹ) | chưa |

| exp-031 | 26/10 | S1: tập A9, nén `--compress lzma-xl` (từ điển cỡ file: 88 → 54 MB cho cùng bài A9) → dư chỗ kèm chunk cho cả 75 bài Trung (chunk 85 Việt + 75 Trung) (id 7049, 75 MB) | — | +0,0004 | 0,3022 · 0,3328 · 0,2717 | bộ chấm đọc được LZMA-XL; R_chunk 0,349 → 0,406 nhưng P_chunk 0,221 → 0,166: chunk Trung hạng 16–75 chỉ đúng 4,4/60 = 0,073 (ngưỡng F2/5 = 0,057 → lợi rất nhỏ) | chưa |
| exp-032 | 26/10 | S2: như S1 + chunk cho bài Việt hạng 86–135 (135 Việt + 75 Trung, 4000:210) (id 7050, 93,5 MB) | — | **+0,0066** | **0,3084** · 0,3328 · 0,2840 | chunk Việt hạng 86–135 đúng 5,1/50 = 0,102 ≫ 0,057 — BEST. Chunk cho cả 175 Việt = 106 MB (quá 100 MB) | chưa |
| exp-033 | 26/10 | S3: như S1 nhưng `--window head` (4.000 ký tự ĐẦU bài thay vì quanh đoạn khớp nhất) (id 7074) | — | −0,0006 vs S1 | 0,3016 · 0,3328 · 0,2704 | BÁC BỎ "chunk tham chiếu nằm ở đầu bài"; chọn theo đoạn khớp nhất tốt hơn một chút. Head chỉ nhỏ hơn 3% khi nén | chưa |
| exp-034 | 26/10 | B1: 200 tài liệu (140/60), chunk top-100 bzip2 (id 7077) | — | F2doc +0,0059 vs A9 | 0,3048 · **0,3387** · 0,2709 | P 0,180 R 0,558; lát 201–250 đúng 3,41/50 = 0,068 (≈ ngưỡng) nhưng F2 macro vẫn tăng | chưa |
| exp-035 | 26/10 | H1: S2 nhưng tập có HyDE (Qwen3-8B viết đoạn trả lời Việt/Trung; dense_hyde_vi=1, dense_hyde_zh=1) (id 7080) | — | −0,0029 vs S2 | 0,3055 · 0,3307 · 0,2804 | BÁC BỎ: đổi 18–22% tập nhưng trúng 38,98 < 39,33/câu — đoạn giả định kéo bài sai lên | chưa |
| exp-036 | 26/10 | B2: 150 tài liệu (105/45) (id 7081) | — | F2doc −0,0023 vs B1 | 0,3036 · 0,3364 · 0,2709 | P 0,208 R 0,502; lát 151–200 đúng 0,094 → đỉnh số tài liệu ≈ 200 | chưa |
| exp-037 | 26/10 | C1: tập B1 (200: 140/60) + chunk cho CẢ 200 tài liệu, lzma-xl (id 7084, 90,4 MB) | — | **+0,0037** vs S2 | **0,3121** · 0,3387 · 0,2855 | 200 tài liệu vừa đủ chỗ để mọi tài liệu có chunk | chưa |
| exp-038 | 26/10 | D1: số tài liệu THEO TỪNG CÂU (dyn_cut.py trên D_wide: giữ bài có điểm RRF ≥ tau·top-1, tau dò để TB 200, 70% Việt, kẹp 80–400) + chunk cho tất cả (id 7088, 90,6 MB) | — | **+0,0061** vs C1 | **0,3182** · 0,3455 · 0,2909 | P 0,182 R 0,564: câu có điểm tụt nhanh lấy ít bài, câu phẳng lấy nhiều | chưa |
| exp-039 | 26/10 | E1: C1 nhưng cửa sổ 6.000 ký tự cho 30 tài liệu đầu (`--chunk-chars 6000:30,4000:200`) (id 7093, 92,6 MB) | — | +0,0002 vs C1 | 0,3123 · 0,3387 · 0,2860 | cửa sổ dài hơn gần như không bắt thêm chunk → không đáng dung lượng | chưa |
| exp-040 | 26/10 | D2: như D1 nhưng dyn_cut TB 180 (126 Việt/54 Trung, kẹp 80–400) (id 7095, 83,8 MB) | — | **+0,0011** vs D1 | **0,3193** · 0,3467 · 0,2919 | P 0,193 R 0,545 — BEST; còn ~11 MB trống | chưa |
| exp-041 | 26/10 | Mentor 22/10 slide 9 (máy Sơn): rerank THEO ĐOẠN — Qwen3-Reranker-0.6B đọc tiêu đề + đoạn khớp nhất (chọn như make_submission) thay vì đầu bài; pool 250 Việt + 100 Trung trên D_wide_son (`--quota 300,130,0`, mặc định mới). Giả thuyết: exp-018 thất bại vì reranker chỉ thấy 800–1.500 ký tự đầu, trong khi 36,6% bài Việt có đoạn khớp sau ký tự 2.000. Bác bỏ nếu cả `prr` lẫn `prrf` (qua dyn_cut TB 180) không hơn baseline D_wide_son cùng pipeline | — | +0,0004 vs baseline cùng tập | `prrf` (id 7160): **0,3369** · `prr` (id 7159): 0,3345 · **baseline D_wide_son không rerank (id 7238): 0,3365** | **BÁC BỎ** (sửa 27/10 — kết luận 26/10 "+0,0176" là SAI vì so với tập ứng viên khác): trên cùng tập, rerank theo đoạn chỉ +0,0004 (nhiễu), reranker thuần −0,0020. Cả bước nhảy 0,3193 → 0,3365 là do **D_wide_son** (máy Sơn: 1.205.706 tài liệu / 729K Việt so với ~714K Việt máy Nguyen; hoặc khác trọng số/k) — chưa tách được nguyên nhân. Bài học: luôn nộp baseline cùng tập trước khi kết luận | 19bab0c, eaab660 |
| exp-042 | 27/10 | Nền mới D_wide_son (0,3365), dyn_cut TB **160** (`sub_son_m160`, 78 MB) | — | −0,0019 | id 7266: 0,3346 | BÁC BỎ: TB 180 vẫn tốt nhất trên nền mới | 30076e7 |
| exp-043 | 27/10 | dyn_cut TB **200** (`sub_son_m200`, 92 MB) | — | −0,0009 | id 7267: 0,3356 | BÁC BỎ: 200 cũng kém 180 → đỉnh ở 180 | 30076e7 |
| exp-044 | 27/10 | dyn_cut vi-share **0,65** (`sub_son_vs65`) | — | −0,0032 | id 7268: 0,3333 | BÁC BỎ: ít Việt hơn thì tệ | 30076e7 |
| exp-045 | 27/10 | dyn_cut vi-share **0,75** (`sub_son_vs75`) | — | +0,0011 | id 7269: 0,3376 | XÁC NHẬN nhẹ: nhiều Việt hơn có lợi → thử 0,80 | 30076e7 |
| exp-046 | 27/10 | RRF **k=100** khi gộp (D_wide_son_k100 → dyn_cut TB 180) (`sub_son_k100`) | — | **+0,0035** | id 7270: **0,3400** | XÁC NHẬN: k=100 làm phẳng RRF, bài có hạng khá ở NHIỀU lượt được đẩy lên — BEST; thử k=150/200 + vs 0,75 | 30076e7 |
| exp-047 | 27/10 | Mục B: thêm **Qwen3-Embedding-0.6B** (Apache-2.0, 06/2025) vào NHÓM TRUNG: `dense_q3e_vi_zh=1, dense_q3e_zh_zh=1` (`sub_son_q3zh`, 85 MB). Mã hoá 236.518 bài Trung 1h16 (40 bài/giây, chậm hơn BGE 2,6×). Top-10 trùng BGE chỉ 12% (vi→zh) / 35% (zh→zh); 37% bài Trung nộp thay đổi. Bác bỏ nếu ≤ nền 0,3365 | — | −0,0011 | id 7271: 0,3354 | BÁC BỎ: Qwen3-Embedding đổi 37% bài Trung nhưng kém BGE-M3 → không mã hoá nhóm Việt | 30076e7 |
| exp-048 | 27/10 | Gộp 2 thay đổi tốt: RRF k=100 + vi-share 0,75 (TB 180) (`sub_son_k100vs75`; 3,6% tài liệu khác vs75). Giả thuyết: hai lợi ích cộng được (≈ 0,341). Bác bỏ nếu ≤ k100 0,3400 | — | — | đã nộp, chưa ghi điểm | hỏi điểm 28/10 | a9d6c7f |
| exp-049 | 27/10 | k=150 + vs 0,75 (`sub_son_k150vs75`). k=30 < 60 < 100 → k còn tăng được? | — | **+0,0027** vs k100 | id 7280: **0,3427** · 0,373 · 0,3125 (P 0,206 R 0,587) | XÁC NHẬN: k=150 > 100 — BEST (nền mới) | a9d6c7f |
| exp-050 | 27/10 | k=200 + vs 0,75 (`sub_son_k200vs75`) — tìm đỉnh của k | — | +0,0027 vs k100 | id 7281: **0,3427** · 0,373 · 0,3126 | bằng k=150 → k đã bão hoà ở 150–200, không thử lớn hơn | a9d6c7f |
| exp-051 | 27/10 | k=100 + vs **0,80** (`sub_son_k100vs80`) — 0,65 < 0,70 < 0,75 → tiếp tục tăng phần Việt? | — | — | đã nộp, chưa ghi điểm | hỏi điểm 28/10 | a9d6c7f |
| exp-052 | 28/10 | Nền k150vs75 (0,3427), vi-share **0,80** (`DC_son_k150vs80`, chưa nén) | — | −0,0008 | id 7447: 0,3419 | BÁC BỎ: đỉnh tỷ lệ Việt ở 0,75 (0,65 < 0,70 < 0,75 > 0,80) | 40f00ab |
| exp-053 | 28/10 | Nền k150vs75, **bm25_vi 0,5** (0,33 chọn ở k=60; k lớn làm phẳng hạng → cân bằng BM25/vector có thể dịch) (`DC_son_k150bm05`, chưa nén) | — | −0,0013 | id 7450: 0,3414 | BÁC BỎ: bm25_vi 0,33 vẫn tốt nhất cả ở k=150 | 40f00ab |
| exp-054 | 28/10 | Lượt mới **bm25bi_vi** (BM25 trên cặp âm tiết liền nhau, 2^24 chiều) THÊM vào nhóm Việt, trọng số 0,33 như bm25_vi, trên nền k150 vs 0,75. Giả thuyết: tiếng Việt là từ ghép nhiều âm tiết, BM25 từ đơn khớp lẫn ("huyết" + "áp" ở hai chỗ khác nhau); cặp âm tiết khớp đúng cụm → một phiếu RRF độc lập, chính xác hơn. Bác bỏ nếu ≤ 0,3427 | — | **+0,0010** | id 7478: **0,3437** | XÁC NHẬN nhẹ: cặp âm tiết là phiếu RRF mới có ích (top-10 trùng BM25 từ đơn chỉ 18%) — BEST | a85c85c |
| exp-055 | 28/10 | bm25bi_vi trọng số **1** (ngang dense) | — | −0,0431 | id 7481: 0,2996 | BÁC BỎ mạnh: BM25 (từ vựng) nặng ngang dense → đổi 31% tài liệu, kéo bài trùng cụm từ nhưng lệch ý (giống exp-010: bm25_vi 1 → 0,33 được +0,028) | a85c85c |
| exp-056 | 28/10 | bm25bi_vi 0,33 **THAY** bm25_vi (bm25_vi=0) | — | — | chưa nộp | | chưa |
| exp-057 | 28/10 | bm25bi_vi **0,2** (+ bm25_vi 0,33) — đỉnh trọng số ở dưới 0,33? | — | — | chưa nộp | | chưa |
| exp-058 | 28/10 | bm25bi_vi **0,5** (+ bm25_vi 0,33) — 0,33 → 1 tụt mạnh, đỉnh có thể nằm giữa | — | — | chưa nộp | | chưa |

**Đo bằng LB (không cần nhãn):** mỗi bài trả 7 số; số trúng = P × số mục nộp, nên hai bài chỉ khác một lát cho
độ chính xác biên của lát đó. Thêm lát khi độ chính xác biên > F2/5 (doc 0,067 · chunk 0,057).
Doc: hạng 251–300 = 0,052 · 301–350 = 0,044 · 351–400 = 0,037. Chunk: Trung 16–75 = 0,073 · Việt 86–135 = 0,102.
Nén LZMA (lc/lp/pb) chỉ đổi ±0,4% → muốn thêm chunk phải bớt chữ, không ép nén thêm được.

**Cấu hình tốt nhất hiện tại (0,3084, id 7050):** như dưới nhưng `chunk_quota.py --chunk-quota 135,75` và
`make_submission.py --chunk-chars 4000:210 --compress lzma-xl` (ZIP 93,5 MB, nén ~15 phút).

**Cấu hình tốt nhất cũ (0,3018, id 6812):**
`search_docs.py --only-fuse --quota 175,75,0 --weights bm25_vi=0.33,dense_vi_vimax=0,bm25_zh=0.3,bm25_en=0 --out D_A9_n250`
→ `chunk_quota.py --docs results/D_A9_n250.jsonl --chunk-quota 85,15 --out results/C_A9_n250.jsonl`
→ `make_submission.py --docs results/C_A9_n250.jsonl --chunk-chars 4000:100 --compress bzip2` (ZIP 88 MB)
Theo số tài liệu: 400 → 0,3017 · 350 → 0,3126 · 300 → 0,3228 · 250 → 0,3328 (F2 doc) — chưa thấy đỉnh, thử 200/150 tiếp.
| — | 23/10 | Bug: `--chunk-docs` cũ không giới hạn theo từng câu (133 chunk/câu thay vì 100) → đã sửa make_submission.py | — | — | — | — | — |

## Chi tiết
### exp-001…003 — P1: BM25 Việt thuần (council-r01/M1-A, M4-A)
- Lệnh: `python search_docs.py --only-fuse --quota N,0,0 --weights dense_vi_vi=0,... --out bm25vi_N`
  rồi `python make_submission.py --docs results/bm25vi_N.jsonl` → `submissions/sub_bm25vi_N.zip`
- Giả thuyết: nhãn sinh từ pool BM25 của BTC; RRF + quota làm loãng. Bác bỏ nếu N=30 có P_doc < 0,35.
- Đọc kết quả: H = P_doc·N; precision biên giữa hai mốc = ΔH/ΔN; tiếp tục tăng N khi precision biên > F2_doc/5.

### exp-004…005 — P2: chunk dài (council-r01/M3-A)
- Lệnh: `python make_submission.py --docs results/bm25vi_60.jsonl --chunk-chars L` → `sub_bm25vi_60_L{L}.zip`
- Độ dài thực tế: L2000 trung vị 1.995 ký tự (ZIP 51 MB); L4000 trung vị 3.995 ký tự (ZIP 95 MB).
- So với exp-002 (cùng tập tài liệu). Bác bỏ "độ dài là thủ phạm" nếu R_chunk/R_doc ≤ 0,45 ở cả hai.
- Rủi ro: bộ chấm quá thời gian / giới hạn dung lượng tải lên với L4000. → Không xảy ra: ZIP 95 MB chấm xong trong ~10 phút.

### Kết luận 22/10 — vì sao
- **P1 sai**: BM25 Việt thuần chỉ đúng 15,6% ở top-30 (phần Việt của bài trộn cũ ~38%). Dense + tiếng Trung đang GIÚP.
  "BM25 Baseline" (P 0,88) cũng là TÊN TÀI KHOẢN BTC → nhiều khả năng là bài thử bộ chấm, không phải hệ BM25 thật.
  Hội đồng round_01 suy luận sai từ con số này.
- **P2 đúng**: chunk dài kéo F2_chunk gần bằng F2_doc (×0,89 ở L=4.000). Lợi 1:1 cho mọi cải thiện tài liệu về sau.
- Precision biên của BM25 Việt: 30→60 ≈ 0,093; 60→100 ≈ 0,068 → vẫn > F2/5 → nhiều tài liệu hơn vẫn có lợi.
