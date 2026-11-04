"""
Tạo tài liệu thuyết minh sản phẩm (PDF, tiếng Việt) cho BTC R2AI Stage 3 — mục 1.1–1.5.

    python tools/make_thuyet_minh.py [--drive "<link Google Drive>"]
    → docs/thuyet_minh_loi_cuda.html → docs/thuyet_minh_loi_cuda.pdf (in bằng Chrome headless)
"""
import argparse
import html
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/sonIT2005/R2AI-retrieval-of-medical-documents"

ap = argparse.ArgumentParser()
ap.add_argument("--drive", default="&lt;LINK_GOOGLE_DRIVE&gt;", help="Link thư mục Google Drive chứa dữ liệu")
args = ap.parse_args()


def table(header, rows, widths=None):
    col = "".join(f'<col style="width:{w}">' for w in widths) if widths else ""
    th = "".join(f"<th>{h}</th>" for h in header)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><colgroup>{col}</colgroup><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>"


def box(x, y, w, h, title, sub="", fill="#eef3fb", stroke="#3a5a8c"):
    subs = sub.split("|") if sub else []
    top = y + h / 2 - (14 + 12 * len(subs)) / 2 + 10  # khối chữ (tiêu đề 14 + mỗi dòng phụ 12) căn giữa ô
    lines = [f'<text x="{x + w / 2}" y="{top}" class="t">{title}</text>']
    for i, t in enumerate(subs):
        lines.append(f'<text x="{x + w / 2}" y="{top + 14 + 12 * i}" class="s">{t}</text>')
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'
            + "".join(lines))


def arrow(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#444" stroke-width="1.3" marker-end="url(#a)"/>'


def path(points):  # mũi tên gấp khúc
    d = "M" + " L".join(f"{x},{y}" for x, y in points)
    return f'<path d="{d}" fill="none" stroke="#444" stroke-width="1.3" marker-end="url(#a)"/>'


# ── Sơ đồ luồng xử lý ────────────────────────────────────────────────────
W, H = 760, 360
svg = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg">',
       '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
       '<path d="M0,0 L8,4 L0,8 z" fill="#444"/></marker></defs>',
       '<style>.t{font:bold 11.5px "Liberation Sans",sans-serif;text-anchor:middle;fill:#111}'
       '.s{font:10px "Liberation Sans",sans-serif;text-anchor:middle;fill:#333}'
       '.g{font:italic 11px "Liberation Sans",sans-serif;fill:#555}</style>']
# Ngoại tuyến: dữ liệu → chỉ mục
svg.append('<text x="10" y="14" class="g">Chuẩn bị (chạy một lần)</text>')
svg.append(box(10, 26, 150, 54, "HTML/XML đã crawl", "SQLite: snute/ai_guru-S3|+ crawl bổ sung db_extra", "#f4f4f4", "#777"))
svg.append(box(195, 26, 150, 54, "Làm sạch", "trafilatura, lọc dòng rác|theo website, XML PubMed", "#f4f4f4", "#777"))
svg.append(box(380, 26, 170, 54, "Chỉ mục BM25", "âm tiết · cặp âm tiết (Việt)|jieba (Trung) · từ (Anh)", "#f4f4f4", "#777"))
svg.append(box(585, 26, 165, 54, "Vector BGE-M3", "1 vector/tài liệu|(512 token đầu)", "#f4f4f4", "#777"))
svg += [arrow(160, 53, 195, 53), arrow(345, 53, 380, 53), path([(270, 26), (270, 19), (667, 19), (667, 26)])]
# Theo câu hỏi
svg.append('<text x="10" y="112" class="g">Với mỗi câu hỏi</text>')
svg.append(box(10, 120, 150, 56, "Câu hỏi tiếng Việt", "", "#fff6e5", "#b07d1a"))
svg.append(box(195, 120, 150, 56, "Dịch câu hỏi", "Qwen3-8B (Ollama)|→ Trung, Anh"))
svg.append(box(380, 120, 170, 56, "9 lượt tìm theo nhóm", "BM25 ×4 · dense BGE-M3 ×5|cùng & xuyên ngôn ngữ, 300/lượt"))
svg.append(box(585, 120, 165, 56, "Gộp RRF (k = 150)", "có trọng số trong từng nhóm|→ 300 Việt + 130 Trung"))
svg += [arrow(160, 148, 195, 148), arrow(345, 148, 380, 148), arrow(550, 148, 585, 148),
        arrow(440, 80, 440, 120), path([(667, 80), (667, 100), (520, 100), (520, 120)])]
svg.append(box(585, 214, 165, 74, "Xếp hạng lại", "Qwen3-Reranker-4B (+ 8B)|top 150 Việt + 50 Trung|câu hỏi + đoạn khớp nhất"))
svg.append(box(380, 214, 170, 74, "Cắt theo từng câu", "giữ điểm ≥ τ·điểm cao nhất|TB 140 tài liệu/câu, 75% Việt"))
svg.append(box(195, 214, 150, 74, "Trích đoạn", "đoạn khớp nhất (BGE-M3)|mở rộng 4.000 ký tự|nguyên văn"))
svg.append(box(10, 214, 150, 74, "File nộp", "JSON 1.200 câu|nén LZMA (< 100 MB)", "#fff6e5", "#b07d1a"))
svg += [arrow(667, 176, 667, 214), arrow(585, 251, 550, 251), arrow(380, 251, 345, 251), arrow(195, 251, 160, 251)]
svg.append('<text x="10" y="314" class="g">Kết quả mỗi câu: relevant_docs (TB 140 doc_id) + relevant_chunks (1 đoạn/tài liệu)</text>')
svg.append('<text x="10" y="334" class="g">Điểm public tốt nhất: 0,3606 (F2 tài liệu 0,3938 · F2 đoạn 0,3274)</text>')
svg.append("</svg>")
DIAGRAM = "".join(svg)

TRANSLATE_PROMPT = html.escape(
    "You are a professional medical translator. Translate the Vietnamese medical question into: 1. zh: Simplified "
    "Chinese, phrased naturally like a patient asking on a Chinese medical Q&A website, using standard Chinese "
    "medical terms. 2. en: English, using standard medical terminology as used in PubMed articles. Keep every "
    "number, unit, lab value, drug name and abbreviation exactly as written. Translate faithfully: keep all "
    "details, add nothing, and do not answer the question.")
RERANK_PROMPT = html.escape(
    "<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct "
    "provided. Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n<|im_start|>user\n"
    "<Instruct>: Given a Vietnamese patient's medical question, judge whether the document is relevant to it\n"
    "<Query>: {câu hỏi}\n<Document>: {tiêu đề}\n{đoạn khớp nhất ≤ 1.200 ký tự}<|im_end|>\n"
    "<|im_start|>assistant\n<think>\n\n</think>\n\n")

body = f"""
<h1>Tài liệu thuyết minh sản phẩm<br><span class="sub">R2AI 2026 · Stage 3 · ViBioMIR — đội loi_cuda</span></h1>
<p class="meta">Mã nguồn: <a href="{REPO}">{REPO}</a> · Dữ liệu: {args.drive}</p>

<h2>1.1. Tổng quan hệ thống</h2>
<p><b>Bài toán.</b> Với mỗi câu hỏi y khoa tiếng Việt, trả về danh sách tài liệu liên quan (doc_id trong danh sách
1.220.598 URL của BTC: Việt, Trung, PubMed tiếng Anh) và một đoạn nội dung trích nguyên văn cho mỗi tài liệu. Đánh giá
bằng F2 cấp tài liệu và F2 cấp đoạn.</p>
<p><b>Phương pháp.</b> Hệ thống truy hồi lai hai tầng, chạy hoàn toàn trên một máy (GPU 16 GB):</p>
<ol>
<li><b>Truy hồi tầng một</b> — chín lượt tìm riêng theo từng nhóm ngôn ngữ (xác định theo website): BM25 theo âm tiết
và theo cặp âm tiết liền nhau cho tiếng Việt, BM25 tách từ jieba cho tiếng Trung, BM25 cho tiếng Anh, và năm lượt dense
BGE-M3 (câu Việt → tài liệu Việt / Trung / Anh; câu dịch Trung → tài liệu Trung; câu dịch Anh → tài liệu Anh).</li>
<li><b>Gộp thứ hạng</b> — Reciprocal Rank Fusion có trọng số trong từng nhóm, k = 150; giữ 300 ứng viên Việt và 130
ứng viên Trung mỗi câu (nhóm Anh có hạn mức 0: bài nộp thử chỉ gồm tài liệu PubMed đạt 0 điểm).</li>
<li><b>Xếp hạng lại</b> — Qwen3-Reranker chấm 150 ứng viên Việt và 50 ứng viên Trung đầu tiên; đầu vào là câu hỏi đầy
đủ cùng tiêu đề và đoạn khớp nhất của tài liệu; điểm là xác suất token “yes”. Bài nộp cuối dùng trung bình điểm của
bản 4B và 8B.</li>
<li><b>Chọn kết quả đầu ra</b> — số tài liệu thay đổi theo từng câu: giữ tài liệu có điểm ≥ τ·(điểm cao nhất của câu
đó), τ được dò để trung bình 140 tài liệu/câu (75% Việt); mỗi tài liệu kèm một đoạn 4.000 ký tự (Trung: 2.000) quanh
vị trí khớp nhất.</li>
</ol>
<div class="fig">{DIAGRAM}<p class="cap">Hình 1. Luồng xử lý từ câu hỏi đầu vào đến danh sách tài liệu và đoạn nội dung.</p></div>

<h3>Chi tiết từng thành phần</h3>
{table(["Thành phần", "Cách làm", "Mã nguồn"], [
    ["Chỉ mục BM25", "Vector hoá bằng hashing (2<sup>23</sup> chiều; cặp âm tiết 2<sup>24</sup>), k1 = 1,2, b = 0,75, "
     "10.000 ký tự đầu của tiêu đề + nội dung; ma trận trọng số BM25 lưu sẵn ở <code>index/bm25/</code>", "search_docs.py"],
    ["Chỉ mục dense", "BGE-M3 fp16, 512 token đầu tài liệu, chuẩn hoá L2; tìm bằng tích vô hướng trên GPU", "embed_corpus.py, search_docs.py"],
    ["Gộp RRF", "s(d) = Σ w<sub>lượt</sub> / (150 + hạng); trọng số: BM25 Việt 0,33 · cặp âm tiết 0,2 · BM25 Trung 0,3 · dense 1",
     "search_docs.py"],
    ["Đoạn khớp nhất", "Chia tài liệu thành đoạn ~1.000 ký tự (Trung ~500), giữ tiêu đề mục với đoạn sau; chọn đoạn có "
     "max(cos với câu Việt, cos với bản dịch cùng ngôn ngữ) theo BGE-M3", "make_submission.py"],
    ["Xếp hạng lại", "Qwen3-Reranker-4B fp16 (8B nạp 8-bit), lô 12.000 token; điểm lưu đệm theo (câu, tài liệu)",
     "qwen_rerank.py, ensemble_rerank.py"],
    ["Cắt theo câu", "τ riêng cho Việt và Trung, dò nhị phân; mỗi câu kẹp trong [80, 400] tài liệu", "dyn_cut.py"],
    ["File nộp", "JSON 1.200 câu, tự kiểm tra định dạng và tính nguyên văn của đoạn, nén LZMA (từ điển = cỡ file)", "make_submission.py"],
], ["17%", "61%", "22%"])}

<h3>Kết quả trên bảng xếp hạng public (600 câu)</h3>
{table(["Cấu hình", "F2 tài liệu", "F2 đoạn", "Điểm"], [
    ["RRF 8 lượt, 100 tài liệu/câu, đoạn ~1.000 ký tự (bản đầu)", "0,2375", "0,0837", "0,1606"],
    ["+ đoạn 4.000 ký tự, bỏ nhóm Anh, giảm trọng số BM25 Việt", "0,3038", "0,2434", "0,2736"],
    ["+ cắt số tài liệu theo từng câu, đoạn cho mọi tài liệu", "0,3467", "0,2919", "0,3193"],
    ["+ RRF k = 150, 75% Việt, BM25 cặp âm tiết", "0,3748", "0,3135", "0,3442"],
    ["+ Qwen3-Reranker-4B, cắt theo điểm reranker, TB 140 tài liệu/câu", "0,3938", "0,3274", "<b>0,3606</b>"],
], ["58%", "14%", "14%", "14%"])}

<h2>1.2. Dữ liệu</h2>
<h3>Nguồn và thu thập</h3>
{table(["Dữ liệu", "Nguồn", "Quy mô"], [
    ["Danh sách kho + câu hỏi", "BTC: Hugging Face <code>AIGuruTinix/ViBioMIR</code> (links_corpus_vi_en_zh.parquet, query.parquet)",
     "1.220.598 URL; 1.200 câu"],
    ["Nội dung đã crawl (dùng chung)", "Hugging Face <code>snute/ai_guru-S3</code>: db/ (97 website), db_cc/ (Common Crawl), "
     "db_wayback/ (Wayback Machine), db_alt/ — SQLite, HTML nén zstd", "~58 GB"],
    ["Crawl bổ sung của đội", "<code>vibiomir_s3/db_extra/</code>: các URL còn thiếu, tải bằng curl_cffi, kiểm tra nội dung "
     "(loại trang CAPTCHA trả mã 200) — scripts/crawl/", "38 file SQLite, 6,1 GB"],
    ["Bản dịch câu hỏi", "Qwen3-8B, có trong repo: results/queries_translated.jsonl", "1.200 câu"],
], ["22%", "58%", "20%"])}
<h3>Làm sạch và phân đoạn</h3>
<ul>
<li>Giải mã theo bảng mã khai báo (GBK/GB2312 → gb18030); trích nội dung chính bằng trafilatura (favor_recall, giữ bảng).</li>
<li>Lấy mẫu 1.500 trang mỗi website, coi dòng xuất hiện ở ≥ 3% số trang là rác giao diện và loại bỏ; trang quá ngắn sau
trích xuất dùng toàn bộ chữ trong thân trang (bỏ script, nav, header, footer).</li>
<li>PubMed (XML efetch): tiêu đề, tóm tắt theo mục, từ khoá, MeSH. Chỉ giữ id thuộc danh sách BTC.</li>
<li>Kết quả: 1.205.706 tài liệu (98,8% danh sách): 729.490 Việt, 236.518 Trung, 239.698 PubMed → <code>clean/corpus/*.parquet</code>
(doc_id, url, host, title, text, lang).</li>
<li>Phân đoạn khi tạo file nộp: gom dòng tới ~1.000 ký tự (Trung ~500), mỗi đoạn là lát cắt nguyên văn của văn bản.</li>
</ul>
<h3>Hướng dẫn truy cập</h3>
<p>Google Drive: {args.drive} — giải nén từ thư mục gốc repo bằng <code>tar -xf &lt;file&gt;.tar</code>, kiểm tra bằng
<code>sha256sum -c SHA256SUMS</code>.</p>
{table(["File", "Nội dung", "Bắt buộc?"], [
    ["vibiomir_db_extra.tar", "vibiomir_s3/db_extra/ — crawl bổ sung của đội (6,1 GB)", "Có"],
    ["vibiomir_clean_corpus.tar", "clean/corpus/ — văn bản đã làm sạch (1,5 GB)", "Không (thay bước làm sạch)"],
    ["vibiomir_emb.tar", "emb/ — vector BGE-M3 (2,4 GB)", "Không (thay bước tạo vector)"],
    ["vibiomir_results.tar", "results/: 9 lượt tìm, vector đoạn, điểm Qwen3-Reranker-8B (~3,6 GB)", "Không (thay ~8 giờ GPU)"],
], ["26%", "52%", "22%"])}
<p>Dữ liệu dùng chung tải bằng: <code>hf download snute/ai_guru-S3 --repo-type dataset --local-dir vibiomir_s3</code> và
<code>hf download AIGuruTinix/ViBioMIR links_corpus_vi_en_zh.parquet query.parquet --repo-type dataset --local-dir btc_data_v2</code>.</p>

<h2>1.3. Mô hình sử dụng</h2>
<p>Tất cả là mô hình mã nguồn mở ≤ 15 tỷ tham số, phát hành trước 01/08/2026; không dùng API thương mại. Mô hình
Hugging Face tự tải khi chạy lần đầu (thư mục mặc định <code>~/.cache/huggingface/hub</code>).</p>
{table(["Mô hình", "Vai trò", "Phiên bản", "Đường dẫn tải chính thức"], [
    ["BAAI/bge-m3 (568M)", "Vector tài liệu, câu hỏi; chọn đoạn khớp nhất", "commit 5617a9f", "huggingface.co/BAAI/bge-m3"],
    ["Qwen/Qwen3-Reranker-4B", "Xếp hạng lại (fp16)", "commit 22e6836", "huggingface.co/Qwen/Qwen3-Reranker-4B"],
    ["Qwen/Qwen3-Reranker-8B", "Xếp hạng lại, gộp với 4B (8-bit, bitsandbytes)", "commit 77d193c", "huggingface.co/Qwen/Qwen3-Reranker-8B"],
    ["Qwen3-8B (Ollama qwen3:8b, Q4_K_M)", "Dịch câu hỏi sang Trung, Anh", "digest 500a1f067a9f", "<code>ollama pull qwen3:8b</code>"],
], ["25%", "30%", "17%", "28%"])}
<p><b>Cấu hình và prompt.</b> Dịch câu hỏi: nhiệt độ 0, tắt chế độ suy nghĩ, đầu ra ràng buộc JSON schema
{{"zh", "en"}}; system prompt:</p>
<pre>{TRANSLATE_PROMPT}</pre>
<p>Xếp hạng lại (định dạng chuẩn của Qwen3-Reranker; điểm = P(“yes”) / (P(“yes”) + P(“no”)) ở token cuối):</p>
<pre>{RERANK_PROMPT}</pre>
<p><b>Chỉ dùng khi phát triển</b> (không nằm trong quy trình tạo bài nộp): Qwen3-14B và Gemma 3 12B (Ollama) làm giám khảo
cho một tập phát triển tự gán nhãn trên 300 câu (<code>llm_judge.py</code>), dùng để so sánh các phương án xếp hạng lại.</p>

<h2>1.4. Mã nguồn</h2>
<p>Toàn bộ mã nguồn: <a href="{REPO}">{REPO}</a>.</p>
{table(["File", "Chức năng"], [
    ["clean_corpus.py", "Làm sạch HTML/XML → clean/corpus"],
    ["embed_corpus.py", "Vector BGE-M3 → emb/"],
    ["translate_queries.py", "Dịch câu hỏi (Qwen3-8B qua Ollama)"],
    ["search_docs.py", "Chỉ mục BM25, 9 lượt tìm, gộp RRF"],
    ["qwen_rerank.py · ensemble_rerank.py", "Xếp hạng lại bằng Qwen3-Reranker; gộp điểm 4B + 8B"],
    ["dyn_cut.py", "Cắt số tài liệu theo từng câu"],
    ["make_submission.py", "Phân đoạn, chọn đoạn, kiểm tra định dạng, nén"],
    ["build_submission.sh", "Bước gộp → xếp hạng lại → cắt → tạo file nộp trong một lệnh (tham số = cấu hình bài nộp)"],
    ["scripts/crawl/", "Crawl bổ sung (find_missing.py, crawl_missing2.py, …)"],
    ["tools/pack_data.sh", "Đóng gói dữ liệu chia sẻ"],
], ["32%", "68%"])}
{table(["Môi trường", "Thư viện chính (phiên bản)"], [
    ["conda base, Python 3.14 — làm sạch", "trafilatura 2.3.1 · zstandard 0.25.0 · lxml 6.1.3 · curl_cffi 0.16.3 · pyarrow 25.0.1 · pandas 3.0.6 "
     "(requirements-clean.txt)"],
    ["conda vibiomir, Python 3.11 — GPU", "torch 2.11.0+cu128 · sentence-transformers 6.1.0 · transformers 5.19.0 · bitsandbytes 0.50.2 · "
     "accelerate 1.15.0 · scikit-learn 1.9.1 · jieba 0.42.1 · pyarrow 26.0.0 (requirements-search.txt)"],
    ["Dịch vụ", "Ollama 0.31.1 · NVIDIA driver 595.91, CUDA 12.8"],
], ["30%", "70%"])}
<p><b>Cấu hình tái hiện bài nộp</b> (tham số mặc định trong build_submission.sh): RRF k = 150; hạn mức 300 Việt / 130
Trung / 0 Anh; reranker chấm 150 Việt + 50 Trung, đoạn ≤ 1.200 ký tự; cắt trung bình 140 tài liệu/câu, 75% Việt, kẹp
[80, 400]; đoạn nộp 4.000 ký tự, nén LZMA-XL.</p>

<h2>1.5. Hướng dẫn cài đặt và chạy lại</h2>
<p>Chi tiết đầy đủ trong <code>README.md</code> của repo. Tóm tắt:</p>
<pre>git clone {REPO}.git vibiomir &amp;&amp; cd vibiomir
pip install -r requirements-clean.txt                          # conda base, Python 3.14
conda create -n vibiomir python=3.11 -y &amp;&amp; conda activate vibiomir
pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements-search.txt &amp;&amp; ollama pull qwen3:8b
# dữ liệu: hf download (mục 1.2) + tar -xf vibiomir_db_extra.tar
python clean_corpus.py                                         # ~1 giờ 20 (conda base)
python embed_corpus.py                                         # ~3 giờ GPU
python search_docs.py --quota 300,130,0 --rrf-k 150 --out D_bi02   # ~20 phút
./build_submission.sh prr_m140                                 # Qwen3-Reranker-4B → bài 0,3606
RERANK=ens ./build_submission.sh ens_m140                      # gộp 4B + 8B → bài vòng private</pre>
<p>Tái tạo nhanh từ dữ liệu tăng tốc (không cần làm sạch, tạo vector, chạy reranker):</p>
<pre>CAND=results/D_bi02.jsonl ./build_submission.sh prr_m140
CAND=results/D_bi02.jsonl RERANK=ens ./build_submission.sh ens_m140</pre>
"""

CSS = """
@page { size: A4; margin: 18mm 17mm 18mm 17mm; }
body { font-family: "Liberation Serif", "DejaVu Serif", serif; font-size: 11pt; line-height: 1.38; color: #111; }
h1 { font-size: 18pt; text-align: center; margin: 0 0 4pt; } h1 .sub { font-size: 12pt; font-weight: normal; }
.meta { text-align: center; font-size: 9.5pt; color: #333; margin-bottom: 10pt; }
h2 { font-size: 13.5pt; border-bottom: 1px solid #999; padding-bottom: 2pt; margin: 16pt 0 6pt; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 10pt 0 4pt; page-break-after: avoid; }
p, li { text-align: justify; } ol, ul { padding-left: 18pt; margin: 4pt 0; } li { margin-bottom: 2pt; }
table { width: 100%; border-collapse: collapse; font-size: 9.3pt; margin: 4pt 0 8pt; page-break-inside: avoid; }
th, td { border: 1px solid #888; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #dde6f3; }
code { font-family: "Liberation Mono", monospace; font-size: 8.8pt; background: #f2f2f2; padding: 0 2px; }
pre { font-family: "Liberation Mono", monospace; font-size: 8.2pt; background: #f5f5f5; border: 1px solid #ddd;
      padding: 5pt 7pt; white-space: pre-wrap; page-break-inside: avoid; }
a { color: #1a4a8c; text-decoration: none; }
.fig { margin: 8pt 0; page-break-inside: avoid; } .cap { text-align: center; font-size: 9.5pt; font-style: italic; }
"""

out_html = ROOT / "docs" / "thuyet_minh_loi_cuda.html"
out_pdf = ROOT / "docs" / "thuyet_minh_loi_cuda.pdf"
out_html.write_text(f'<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Thuyết minh — loi_cuda</title>'
                    f"<style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={out_pdf}", out_html.as_uri()], check=True, capture_output=True)
print("→", out_html, "\n→", out_pdf)
