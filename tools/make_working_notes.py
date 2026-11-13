"""Tạo working-notes paper (Word, tiếng Việt) cho đội loi_cuda — ViBioMIR, R2AI 2026.

    conda activate base   # cần python-docx
    python tools/make_working_notes.py docs/working_notes_loi_cuda.docx
"""
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = sys.argv[1]
FONT = "Times New Roman"

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Cm(2.5))


def set_font(style, size, bold=None):
    style.font.name = FONT
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for k in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(k), FONT)


set_font(doc.styles["Normal"], 12)
doc.styles["Normal"].paragraph_format.space_after = Pt(6)
doc.styles["Normal"].paragraph_format.line_spacing = 1.15
for name, size in (("Heading 1", 14), ("Heading 2", 12.5), ("Title", 17)):
    set_font(doc.styles[name], size, bold=True)
doc.styles["Heading 2"].font.italic = False


def runs(p, text):
    """**đậm**, *nghiêng*, `mã` trong một đoạn."""
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**"):
            p.add_run(part[2:-2]).bold = True
        elif part.startswith("`"):
            r = p.add_run(part[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(10.5)
        elif part.startswith("*"):
            p.add_run(part[1:-1]).italic = True
        else:
            p.add_run(part)
    return p


def para(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=None, italic=False):
    p = runs(doc.add_paragraph(), text)
    p.alignment = align
    for r in p.runs:
        if size:
            r.font.size = Pt(size)
        if italic:
            r.italic = True
    return p


def bullets(items):
    for it in items:
        p = runs(doc.add_paragraph(style="List Bullet"), it)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(3)


def h1(t):
    doc.add_heading(t, level=1)


def h2(t):
    doc.add_heading(t, level=2)


def shade(cell, color):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcpr.append(shd)


def table(header, rows, widths, caption, bold_rows=()):
    cap = para(caption, align=WD_ALIGN_PARAGRAPH.CENTER, size=11)
    cap.runs[0].bold = True
    cap.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate([header] + rows):
        for j, val in enumerate(row):
            c = t.rows[i].cells[j]
            c.width = Cm(widths[j])
            c.text = ""
            p = runs(c.paragraphs[0], str(val))
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.size = Pt(10)
                if i == 0 or (i - 1) in bold_rows:
                    r.bold = True
            if i == 0:
                shade(c, "D9E2F3")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ── Tiêu đề ──────────────────────────────────────────────────────────────
t = doc.add_paragraph(style="Title")
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.add_run("Đội loi_cuda tại ViBioMIR – R2AI 2026: truy hồi tài liệu y khoa xuyên ngôn ngữ Việt – Trung "
          "bằng gộp thứ hạng nhiều lượt và Qwen3-Reranker")
para("[Họ tên thành viên 1], [Họ tên thành viên 2], [Họ tên thành viên 3]", align=WD_ALIGN_PARAGRAPH.CENTER)
para("[Đơn vị / Trường] · [email liên hệ]", align=WD_ALIGN_PARAGRAPH.CENTER, size=11, italic=True)

h1("Tóm tắt")
para("Bài viết mô tả hệ thống của đội loi_cuda cho nhiệm vụ ViBioMIR (R2AI 2026, AI Guru Season 3): với mỗi câu hỏi "
     "y khoa tiếng Việt, tìm các tài liệu liên quan và trích đoạn nội dung liên quan trong một kho khoảng 1,2 triệu "
     "trang web Việt, Trung và tóm tắt PubMed. Hệ thống gồm năm bước: (1) thu thập và làm sạch HTML; (2) dịch câu hỏi "
     "sang tiếng Trung và tiếng Anh bằng Qwen3-8B; (3) chín lượt tìm kiếm riêng theo từng nhóm ngôn ngữ (BM25 theo âm "
     "tiết, BM25 theo cặp âm tiết, BM25 tiếng Trung tách từ bằng jieba, và vector BGE-M3 cùng ngôn ngữ lẫn xuyên ngôn "
     "ngữ), gộp bằng Reciprocal Rank Fusion có trọng số với k = 150; (4) chấm lại 200 ứng viên đầu mỗi câu bằng "
     "Qwen3-Reranker (bản 4B; bài nộp private gộp thêm bản 8B) trên đoạn khớp nhất của tài liệu; (5) cắt số tài liệu theo từng câu dựa trên điểm của reranker "
     "và trích một đoạn 4.000 ký tự quanh vị trí khớp nhất của mỗi tài liệu. Bài nộp tốt nhất đạt **0,3606** trên bảng "
     "xếp hạng public (F2 tài liệu 0,3938; F2 đoạn 0,3274), tăng từ 0,1606 của bản đầu tiên qua hơn 70 thí nghiệm được ghi "
     "nhật ký. Sau khi vòng public đóng, chúng tôi xây một tập phát triển gán nhãn bằng LLM (Qwen3-14B và Gemma 3 12B) "
     "trên 300 câu, hiệu chuẩn bằng các bài đã nộp, để chọn bài nộp private: gộp điểm Qwen3-Reranker-4B và 8B. Chúng tôi "
     "trình bày cả các hướng thất bại (HyDE, tách câu hỏi nhiều ý, reranker nhỏ, mô hình embedding thứ hai) và một số bài "
     "học về cách đo lường khi chỉ có điểm tổng hợp từ bảng xếp hạng.")
para("**Từ khoá:** truy hồi thông tin xuyên ngôn ngữ, y sinh, tiếng Việt, BM25, BGE-M3, Reciprocal Rank Fusion, "
     "reranker, F2.")

# ── 1 ────────────────────────────────────────────────────────────────────
h1("1. Giới thiệu")
para("Người dùng Việt Nam thường đặt câu hỏi sức khoẻ bằng ngôn ngữ đời thường, dài, kèm bối cảnh cá nhân (tuổi, triệu "
     "chứng, kết quả xét nghiệm). Câu trả lời có thể nằm trong bài viết tiếng Việt của bệnh viện, nhà thuốc, báo sức "
     "khoẻ, hoặc trong các trang hỏi đáp y khoa tiếng Trung. ViBioMIR đặt bài toán truy hồi xuyên ngôn ngữ này ở hai "
     "cấp: tài liệu (doc_id) và đoạn nội dung (chunk) trích nguyên văn từ tài liệu, đánh giá bằng F2 (coi trọng độ "
     "bao phủ gấp bốn lần độ chính xác).")
para("Ràng buộc của cuộc thi định hình thiết kế: chỉ dùng mô hình mã nguồn mở không quá 15 tỷ tham số, phát hành trước "
     "01/08/2026; không có tập phát triển có nhãn; bảng xếp hạng public chỉ trả về bảy con số tổng hợp cho mỗi bài nộp, "
     "tối đa 10 bài mỗi ngày và file nộp dưới 100 MB. Toàn bộ hệ thống chạy trên một máy cá nhân (RTX 5060 Ti 16 GB, "
     "32 luồng CPU, 29 GB RAM). Đóng góp của bài viết gồm: (i) một quy trình truy hồi lai chạy được trên phần cứng phổ "
     "thông; (ii) phân tích có số liệu cho từng quyết định thiết kế, kể cả các thử nghiệm không thành công; (iii) cách "
     "đo độ chính xác biên từ điểm tổng hợp của bảng xếp hạng để quyết định số lượng tài liệu cần nộp; (iv) một tập phát "
     "triển gán nhãn bằng LLM, kèm cách hiệu chuẩn và các giới hạn đã đo được.")

# ── 2 ────────────────────────────────────────────────────────────────────
h1("2. Nhiệm vụ và dữ liệu")
h2("2.1. Đánh giá")
para("Với mỗi câu hỏi, gọi D là tập tài liệu nộp và G là tập tài liệu đúng: Precision = |D ∩ G| / |D|, "
     "Recall = |D ∩ G| / |G|, F2 = 5·P·R / (4·P + R). Một đoạn nộp c được tính đúng nếu tồn tại đoạn tham chiếu g cùng "
     "câu hỏi và cùng doc_id sao cho LCS_token(c, g) / max(|c|, |g|) ≥ 0,4, sau khi chuẩn hoá NFKC, giải mã HTML "
     "entity, đưa về chữ thường và gộp khoảng trắng. F2 được tính cho từng câu rồi lấy trung bình; điểm cuối là trung "
     "bình của F2 tài liệu và F2 đoạn.")
h2("2.2. Kho tài liệu và câu hỏi")
para("Ban tổ chức (BTC) công bố danh sách 1.220.598 URL (740.598 trang Việt, 240.000 trang Trung, 240.000 bài PubMed) "
     "và 1.200 câu hỏi tiếng Việt; bảng public chấm 600 câu. Nội dung trang không được phát hành kèm. Chúng tôi dùng "
     "bộ dữ liệu crawl dùng chung snute/ai_guru-S3 (HTML nén zstd trong SQLite, khoảng 64 GB) và tự crawl bổ sung các "
     "trang còn thiếu. Một bài học thực tế: nhiều trang trả mã HTTP 200 nhưng nội dung là trang xác minh CAPTCHA, nên "
     "độ phủ phải được kiểm bằng nội dung chứ không chỉ bằng mã trạng thái. Sau làm sạch, kho còn 1.205.706 tài liệu "
     "(98,8%): 729.490 Việt, 236.518 Trung và 239.698 PubMed.")
para("Từ điểm tổng hợp của bảng xếp hạng (không dùng nhãn từng câu), chúng tôi suy ra ba đặc điểm của đáp án: (a) đáp án "
     "rất lớn, trung vị khoảng 60 tài liệu mỗi câu (tối đa 190), mỗi tài liệu đúng có khoảng một đoạn tham chiếu; (b) "
     "bài nộp thử chỉ gồm tài liệu PubMed đạt 0 điểm, nên nhóm tiếng Anh được đặt hạn mức 0; (c) độ chính xác tài liệu "
     "ở nhóm Việt (khoảng 0,38) cao hơn nhóm Trung (khoảng 0,16), nhưng độ chính xác đoạn thì ngược lại, vì bài Việt dài "
     "hơn nhiều (trung vị 4.387 ký tự so với 547 ký tự).")

# ── 3 ────────────────────────────────────────────────────────────────────
h1("3. Hệ thống")
para("Hình dung tổng quát: câu hỏi Việt → dịch (Trung, Anh) → 9 lượt tìm theo nhóm ngôn ngữ → RRF trong từng nhóm "
     "(300 ứng viên Việt, 130 Trung) → Qwen3-Reranker-4B chấm 150 Việt + 50 Trung → cắt theo điểm reranker (trung bình "
     "140 tài liệu/câu, 75% Việt) → mỗi tài liệu một đoạn 4.000 ký tự → file JSON nén LZMA.", italic=False)
h2("3.1. Làm sạch")
para("HTML được giải mã theo bảng mã khai báo (trang GBK/GB2312 giải mã bằng gb18030 vì thư viện trích xuất hay đoán "
     "sai), trích nội dung chính bằng trafilatura (favor_recall, giữ bảng). Với từng website, chúng tôi lấy mẫu 1.500 "
     "trang và coi các dòng xuất hiện ở ít nhất 3% số trang là rác giao diện (menu, chân trang, câu miễn trừ trách "
     "nhiệm) để loại bỏ. Trang quá ngắn sau trích xuất được thay bằng toàn bộ chữ trong thân trang (đã bỏ script, nav, "
     "header, footer). Bài PubMed ở dạng XML của API efetch được đọc riêng: tiêu đề, tóm tắt theo mục, từ khoá và MeSH. "
     "Kiểm tra trên 400 bài Việt được xếp hạng cao cho thấy phần bị loại chủ yếu là tiêu đề bài liên quan, form đặt "
     "lịch và quảng cáo; không bài nào bị cắt cụt nội dung chính.")
h2("3.2. Dịch câu hỏi")
para("Mỗi câu hỏi được dịch sang tiếng Trung (giọng người bệnh hỏi trên trang hỏi đáp y khoa Trung Quốc, dùng thuật ngữ "
     "chuẩn) và tiếng Anh bằng Qwen3-8B chạy qua Ollama, nhiệt độ 0, đầu ra ràng buộc bằng JSON schema, yêu cầu giữ "
     "nguyên số, đơn vị, tên thuốc và chữ viết tắt. Dịch 1.200 câu mất khoảng 1,5 giờ GPU.")
h2("3.3. Truy hồi tầng một")
para("Tài liệu được chia thành ba nhóm theo website (Việt, Trung, PubMed). Mỗi lượt tìm trả về 300 tài liệu trong một "
     "nhóm:")
bullets([
    "**BM25 từ đơn** (k1 = 1,2; b = 0,75) trên 10.000 ký tự đầu của tiêu đề + nội dung, vector hoá bằng hashing "
    "2^23 chiều; tiếng Việt tách theo âm tiết, tiếng Trung tách từ bằng jieba (chế độ tìm kiếm), tiếng Anh bỏ từ dừng.",
    "**BM25 cặp âm tiết** cho tiếng Việt (bigram âm tiết liền nhau, 2^24 chiều). Tiếng Việt là ngôn ngữ đơn lập: các "
    "từ ghép như “huyết áp”, “đau đầu” bị BM25 âm tiết khớp lẫn ở hai vị trí khác nhau. Top-10 của lượt này chỉ trùng "
    "18% với BM25 từ đơn, tức là một tín hiệu mới cho bước gộp. Dựng chỉ mục mất chưa tới 30 giây.",
    "**Dense BGE-M3** (fp16, 512 token đầu của tài liệu): câu Việt → tài liệu Việt; câu Việt → tài liệu Trung (xuyên "
    "ngôn ngữ); câu dịch Trung → tài liệu Trung; tương tự cho PubMed.",
])
para("Tổng cộng chín lượt cho ba nhóm: nhóm Việt có bm25_vi, bm25bi_vi, dense_vi_vi; nhóm Trung có bm25_zh, dense_vi_zh, "
     "dense_zh_zh; nhóm Anh có bm25_en, dense_vi_en, dense_en_en (nhóm Anh có hạn mức 0, xem mục 2.2).")
h2("3.4. Gộp thứ hạng")
para("Trong từng nhóm, tài liệu d nhận điểm RRF có trọng số: s(d) = Σ_lượt w_lượt / (k + hạng_lượt(d)), với k = 150. "
     "Trọng số dò trên bảng xếp hạng: BM25 từ đơn tiếng Việt 0,33, BM25 cặp âm tiết 0,2, BM25 tiếng Trung 0,3, các lượt "
     "dense 1. Mỗi câu giữ 300 ứng viên Việt và 130 ứng viên Trung, xen kẽ theo tỉ lệ hạn mức. Giá trị k lớn làm phẳng "
     "khoảng cách giữa các hạng, nên tài liệu được nhiều lượt cùng tìm thấy ở hạng trung bình được ưu tiên hơn tài "
     "liệu chỉ đứng đầu một lượt. Điều này phù hợp với đáp án lớn (khoảng 60 tài liệu/câu).")
h2("3.5. Chấm lại bằng Qwen3-Reranker")
para("Với mỗi câu, 150 ứng viên Việt và 50 ứng viên Trung đầu tiên được chấm bằng Qwen3-Reranker-4B. Đầu vào gồm câu hỏi "
     "**đầy đủ** (tài liệu Trung dùng bản dịch Trung), tiêu đề và **đoạn khớp nhất** của tài liệu (đoạn có cosine BGE-M3 "
     "cao nhất với câu hỏi, cắt còn 1.200 ký tự) thay vì phần đầu bài: 36,6% bài Việt có đoạn khớp nhất nằm sau ký tự "
     "thứ 2.000. Điểm là xác suất token “yes”. Thứ tự trong pool được sắp lại hoàn toàn theo điểm reranker; tài liệu "
     "ngoài pool giữ thứ tự cũ và xếp sau. Chấm 240.000 cặp mất khoảng 6,3 giờ (10,6 cặp/giây, trung bình 384 "
     "token/cặp, lô 12.000 token; lô 24.000 token gây tràn bộ nhớ 16 GB). Điểm được lưu đệm sau mỗi khối 40.000 cặp "
     "nên quá trình có thể dừng và chạy tiếp. Bài nộp private dùng thêm Qwen3-Reranker-8B (nạp 8-bit bằng bitsandbytes "
     "để vừa thẻ 16 GB; 8,2 cặp/giây, khoảng 8 giờ cho 240.000 cặp) và lấy trung bình xác suất “yes” của hai mô hình "
     "làm điểm cuối.")
h2("3.6. Cắt số tài liệu theo từng câu")
para("Đáp án mỗi câu dao động từ vài đến 190 tài liệu, nên số tài liệu nộp cũng thay đổi theo câu. Trong từng ngôn ngữ, "
     "chúng tôi giữ các tài liệu có điểm ≥ τ·(điểm cao nhất của câu đó); τ được dò nhị phân sao cho trung bình số tài "
     "liệu bằng 140 × tỉ lệ ngôn ngữ (75% Việt, 25% Trung), mỗi câu kẹp trong [80, 400] tài liệu. Ngưỡng tương đối "
     "giúp câu có điểm giảm nhanh (ít tài liệu liên quan) được nộp ít, câu có điểm giảm chậm được nộp nhiều.")
h2("3.7. Trích đoạn")
para("Mỗi tài liệu được chia đoạn theo dòng, gom tới khoảng 1.000 ký tự (Việt, Anh) hoặc 500 ký tự (Trung), dòng tiêu "
     "đề mục đi cùng đoạn ngay sau. Đoạn được chọn theo max(cosine với câu Việt, cosine với bản dịch cùng ngôn ngữ) trên "
     "vector BGE-M3 của tiêu đề + đoạn, rồi mở rộng hai phía thành cửa sổ 4.000 ký tự (2.000 với tiếng Trung), cắt ở "
     "khoảng trắng để luôn là trích dẫn nguyên văn. Mọi tài liệu nộp đều kèm đúng một đoạn. File JSON (khoảng 800 MB) "
     "được nén LZMA với từ điển bằng kích thước file, còn 73 MB, dưới giới hạn 100 MB.")

# ── 4 ────────────────────────────────────────────────────────────────────
h1("4. Thực nghiệm và kết quả")
para("Không có nhãn phát triển, nên mọi quyết định được kiểm bằng bảng xếp hạng public (600 câu, bộ chấm tất định). Mỗi "
     "thí nghiệm chỉ thay đổi một yếu tố, giả thuyết và tiêu chí bác bỏ được ghi trước khi nộp. Bảng 1 tóm tắt các bước "
     "cải thiện chính.")
table(["Bước (thí nghiệm)", "F2 tài liệu", "F2 đoạn", "Điểm"], [
    ["Bản đầu: RRF 8 lượt, 100 tài liệu (40 Việt / 50 Trung / 10 Anh), đoạn ~1.000 ký tự (exp-000)", "0,2375", "0,0837", "0,1606"],
    ["Đoạn dài 4.000 ký tự (exp-006)", "0,2309", "0,2104", "0,2207"],
    ["Bỏ nhóm Anh, 300 tài liệu/câu (exp-007, 009)", "0,2736", "0,2176", "0,2456"],
    ["Giảm trọng số BM25 Việt 1 → 0,33 (exp-010)", "0,3038", "0,2434", "0,2736"],
    ["Tỉ lệ Việt/Trung 210/90, tách hạn mức đoạn (exp-016, 019)", "0,3228", "0,2709", "0,2968"],
    ["Nén LZMA-XL → đoạn cho mọi tài liệu, 200 tài liệu (exp-032, 037)", "0,3387", "0,2855", "0,3121"],
    ["Cắt số tài liệu theo từng câu, TB 180 (exp-038, 040)", "0,3467", "0,2919", "0,3193"],
    ["Dựng lại danh sách ứng viên trên kho đầy đủ (exp-041)", "—", "—", "0,3365"],
    ["RRF k = 150, 75% Việt (exp-046, 049)", "0,3728", "0,3126", "0,3427"],
    ["+ BM25 cặp âm tiết, trọng số 0,2 (exp-057)", "0,3748", "0,3135", "0,3442"],
    ["+ Qwen3-Reranker-4B, cắt theo điểm reranker, TB 180 (exp-066)", "—", "—", "0,3479"],
    ["Cắt TB 160 → 140 tài liệu/câu (exp-069, 073)", "0,3938", "0,3274", "**0,3606**"],
    ["+ gộp điểm Qwen3-Reranker-8B — bài nộp private (exp-079)", "—", "—", "tập PT: +0,0051"],
], [9.2, 2.2, 2.2, 2.0], "Bảng 1. Các bước cải thiện chính trên bảng xếp hạng public (600 câu); dòng cuối đo bằng tập "
   "phát triển (mục 4.2) vì vòng private không công bố điểm", bold_rows=(11,))
para("Bài tốt nhất có Precision / Recall tài liệu 0,2379 / 0,5565 và Precision / Recall đoạn 0,2035 / 0,4513. "
     "Bước nhảy giữa exp-040 (0,3193) và exp-041 (0,3365) xảy ra khi dựng lại danh sách ứng viên trên một máy khác với "
     "cùng các bước sau; chúng tôi chưa tách được nguyên nhân (kho tài liệu đầy đủ hơn khoảng 15.000 bài Việt, hoặc khác "
     "biệt về các lượt tìm được gộp), nên ghi nhận nó như một kết quả chưa giải thích.")
h2("4.1. Các hướng không thành công")
table(["Thử nghiệm", "Thay đổi điểm", "Nhận xét"], [
    ["BM25 tiếng Việt đơn thuần, 30–100 tài liệu (exp-001…003)", "−0,08 … −0,11", "Dense và nhóm Trung đóng góp lớn"],
    ["bge-reranker-v2-m3 trên 1.500 ký tự đầu bài (exp-018)", "−0,012", "Đầu bài thường không chứa phần liên quan"],
    ["Qwen3-Reranker-0.6B trên đoạn khớp nhất (exp-041)", "+0,0004", "Quá yếu; bản 4B mới có ích"],
    ["Vector cửa sổ phần sau bài, lấy điểm max (exp-011, 012)", "−0,042 / −0,013", "Kéo lên tài liệu sai"],
    ["HyDE: Qwen3-8B viết đoạn trả lời giả định (exp-035)", "−0,0029", "Đoạn giả định dẫn sai hướng"],
    ["Qwen3-Embedding-0.6B cho nhóm Trung (exp-047)", "−0,0011", "Kém BGE-M3 dù khác biệt lớn"],
    ["BM25 cặp chữ Hán (exp-059, 060)", "−0,0006 … −0,0016", "Trùng 32% với lượt jieba"],
    ["Tách câu hỏi nhiều ý thành câu con (exp-063…065)", "−0,0046 … −0,0198", "Recall không tăng, precision giảm"],
    ["RRF giữa thứ tự cũ và reranker (prrf, exp-066)", "−0,0091 so với prr", "Điểm RRF phẳng làm hỏng bước cắt"],
    ["Đoạn 3.000 / 2.500 ký tự (exp-067, 068)", "−0,0045 / −0,0109", "Đoạn ngắn hơn bắt được ít đoạn đúng hơn"],
    ["Đoạn 6.000 ký tự cho 30 tài liệu đầu (exp-039)", "+0,0002", "Bão hoà quanh 4.000 ký tự"],
    ["Gộp 4B + 8B theo thứ hạng thay vì theo điểm (tập PT)", "−0,041 (tập PT)", "Điểm phẳng làm hỏng bước cắt"],
], [7.6, 3.2, 5.0], "Bảng 2. Các thử nghiệm bị bác bỏ (so với cấu hình tốt nhất tại thời điểm thử)")

h2("4.2. Tập phát triển gán nhãn bằng LLM")
para("Sau khi vòng public đóng, mọi thay đổi chỉ còn được đánh giá qua 5 lượt nộp private không công bố điểm. Chúng tôi "
     "lấy ngẫu nhiên 300 câu (seed cố định) và gom mọi tài liệu mà 22 cấu hình đã nộp public cho các câu đó (trung bình "
     "275 tài liệu/câu, 82.524 cặp). Qwen3-14B được hỏi “bác sĩ trả lời đúng câu hỏi này có dùng tài liệu này không?” và "
     "trả lời Yes/No; điểm là log P(Yes) − log P(No) của token đầu (xác suất thô bão hoà ở 1,0 với nhiều tài liệu). "
     "Gemma 3 12B (khác họ mô hình với reranker) chấm cùng tập để kiểm tra chéo. Với mỗi câu, khoảng 71 tài liệu điểm cao "
     "nhất được coi là liên quan, rồi tính F2 tài liệu cho bất kỳ danh sách nộp nào.")
para("Hai lựa chọn hiệu chuẩn được chọn theo mức tương quan với điểm public của 22 cấu hình: chỉ xét tài liệu nằm trong "
     "top-300 của các lượt dense, và trừ một hằng số vào log-odds của tài liệu tiếng Trung (giám khảo cho tài liệu Trung "
     "“liên quan” nhiều hơn tỉ lệ mà các bài nộp đầu cho thấy; hằng số riêng cho từng giám khảo, chọn để tỉ lệ độ chính xác "
     "Việt/Trung ≈ 2,4). Kết quả trên 300 câu: với các cặp cấu hình chênh nhau ≥ 0,005 điểm public, tập phát triển xếp "
     "đúng thứ tự 99% (134 cặp), Pearson 0,94; trên 149 câu không dùng khi chọn hằng số vẫn đạt 99% và 0,935; Gemma 3 12B "
     "cho kết quả tương đương (99%, 0,936). Giới hạn đã đo: tập phát triển đánh giá sai khi so các độ sâu cắt khác nhau "
     "(dự đoán bước 160 → 140 tài liệu tăng +0,0057, thực tế +0,0013), nên chỉ được dùng để so các phương án cùng độ sâu "
     "cắt. Trên tập này, Qwen3-Reranker-8B hơn 4B +0,0035 (khoảng tin cậy 95%: +0,0003 … +0,0067) và gộp điểm hai mô "
     "hình hơn 4B +0,0048 (+0,0026 … +0,0071), tương đương khoảng +0,0015 điểm public theo hệ số quy đổi 0,32.")

# ── 5 ────────────────────────────────────────────────────────────────────
h1("5. Phân tích")
h2("5.1. Đo độ chính xác biên từ điểm tổng hợp")
para("Với một câu hỏi có G tài liệu đúng, nộp N tài liệu trong đó H tài liệu đúng: F2 = 5H / (4G + N). Thêm ΔN tài liệu "
     "với ΔH tài liệu đúng làm F2 tăng khi và chỉ khi ΔH / ΔN > F2 / 5. Bảng xếp hạng trả về Precision và số mục nộp đã "
     "biết, nên số trúng H = P × N. Hai bài nộp chỉ khác nhau một lát hạng (ví dụ hạng 201–250) cho ra độ chính xác biên "
     "của lát đó mà không cần nhãn từng câu. Chúng tôi dùng quy tắc này để chọn số tài liệu (lát 251–300 chỉ đúng 5,2%, "
     "dưới ngưỡng F2/5 ≈ 6,7%) và số đoạn trích (đoạn cho bài Việt hạng 86–135 đúng 10,2%, trên ngưỡng 5,7%).")
h2("5.2. Liên quan theo toàn bộ câu hỏi")
para("Giả thuyết “câu hỏi nhiều ý cần tìm riêng từng ý” bị bác bỏ rõ ràng: lượt tìm bằng câu con đưa vào nhiều tài liệu "
     "mới với các câu có 3–4 ý (top-50 chỉ trùng 21–41% với lượt gốc), nhưng Recall tài liệu không tăng (0,5895 → "
     "0,5877) trong khi Precision giảm: các tài liệu chỉ nói về một ý của câu hỏi không làm tăng điểm. "
     "Ngược lại, reranker đọc câu hỏi đầy đủ cùng đoạn khớp nhất đem lại mức tăng lớn nhất của giai đoạn cuối (+0,016). "
     "Hai kết quả này nhất quán: mức liên quan được đánh giá theo toàn bộ bối cảnh câu hỏi.")
h2("5.3. Reranker cần đi cùng bước cắt phù hợp")
para("Cùng một điểm reranker, sắp lại hoàn toàn theo điểm (prr, 0,3479) tốt hơn hẳn trộn RRF với thứ tự cũ (prrf, "
     "0,3388). Lý do nằm ở bước cắt: xác suất “yes” của reranker phản ánh độ tự tin thật, nên số tài liệu giữ lại thay "
     "đổi theo câu (p10 = 143, p90 = 200), còn điểm RRF rất phẳng nên câu nào cũng giữ gần bằng nhau (171–189). Khi thứ "
     "tự đã tốt hơn, cắt sớm hơn có lợi: trung bình 180 → 160 → 140 tài liệu cho 0,3479 → 0,3593 → 0,3606.")
h2("5.4. Độ dài đoạn trích")
para("Với cùng danh sách tài liệu (F2 tài liệu không đổi), Recall đoạn tăng đều theo độ dài cửa sổ: 2.500 ký tự → 0,4456; "
     "3.000 → 0,4652; 4.000 → 0,4795, trong khi cửa sổ 6.000 ký tự cho các tài liệu đầu gần như không thêm gì. Vì độ "
     "trùng chia cho max(|c|, |g|), đoạn nộp quá dài so với đoạn tham chiếu sẽ không được tính đúng; với cửa sổ đến "
     "4.000 ký tự, đoạn dài hơn vẫn có lợi. Khoảng 18% trường hợp tìm đúng tài liệu nhưng trượt "
     "đoạn vẫn chưa giải thích được; gần như toàn bộ rơi vào bài Việt dài (54,6% bài Việt nộp dài hơn cửa sổ).")

h2("5.5. Cỡ mô hình reranker")
para("Cùng cách dùng (câu hỏi đầy đủ + đoạn khớp nhất), Qwen3-Reranker-0.6B gần như không thêm gì (+0,0004), bản 4B đem "
     "lại +0,016 điểm public, còn bản 8B chỉ thêm khoảng +0,001 (đo bằng tập phát triển). Từ các thử nghiệm với reranker "
     "nhỏ (bge-reranker-v2-m3, Qwen3-Reranker-0.6B), chúng tôi từng kết luận quá sớm rằng xếp hạng lại không có ích cho bài "
     "toán này và để lỡ vài ngày. Bài học: trước khi loại bỏ một hướng, nên thử nhanh bản mô hình lớn hơn trên một mẫu nhỏ.")

# ── 6 ────────────────────────────────────────────────────────────────────
h1("6. Hạn chế và hướng phát triển")
bullets([
    "Phần lớn siêu tham số được dò trên 600 câu public; các mức chênh khoảng 0,001 nằm trong biên nhiễu khi chuyển sang "
    "tập private. Tập phát triển gán nhãn bằng LLM (mục 4.2) chỉ đáng tin khi so các phương án cùng độ sâu cắt.",
    "Reranker chỉ chấm 200 ứng viên/câu (150 Việt + 50 Trung) do giới hạn thời gian GPU. Trên tập phát triển, khoảng 27% "
    "tài liệu Việt hạng RRF 151–200 có nhãn được chấm là liên quan, nên mở rộng phạm vi chấm có thể tăng thêm Recall.",
    "Vector BGE-M3 chỉ biểu diễn 512 token đầu tài liệu; bài Việt dài cần biểu diễn theo đoạn tốt hơn (thử lấy max theo "
    "cửa sổ đã thất bại, exp-011).",
    "Chọn đoạn trích vẫn dùng cosine BGE-M3; chấm đoạn bằng reranker có thể giảm 18% trường hợp đúng tài liệu sai đoạn.",
    "Nhóm PubMed tiếng Anh chưa được dùng (hạn mức 0, xem mục 2.2).",
])

# ── 7 ────────────────────────────────────────────────────────────────────
h1("7. Kết luận")
para("Hệ thống của đội loi_cuda kết hợp nhiều lượt tìm từ vựng và ngữ nghĩa theo từng ngôn ngữ, gộp bằng RRF với k lớn, "
     "chấm lại bằng Qwen3-Reranker-4B trên đoạn khớp nhất và cắt số tài liệu theo độ tự tin của reranker, đạt 0,3606 trên "
     "bảng xếp hạng public, toàn bộ chạy trên một GPU 16 GB; bài nộp private gộp thêm điểm Qwen3-Reranker-8B, được chọn "
     "nhờ một tập phát triển gán nhãn bằng LLM đã hiệu chuẩn với các bài nộp public. Ba yếu tố đóng góp nhiều nhất là: đoạn trích dài và có cho mọi "
     "tài liệu; cắt số tài liệu theo từng câu; và reranker đủ mạnh đi kèm bước cắt dựa trên điểm của chính nó. Mã nguồn, "
     "nhật ký hơn 70 thí nghiệm và lệnh tái tạo bài nộp tốt nhất được lưu trong kho mã của đội.")

# ── TLTK ─────────────────────────────────────────────────────────────────
h1("Tài liệu tham khảo")
refs = [
    "S. Robertson, H. Zaragoza. The Probabilistic Relevance Framework: BM25 and Beyond. Foundations and Trends in "
    "Information Retrieval, 3(4), 2009.",
    "G. V. Cormack, C. L. A. Clarke, S. Büttcher. Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank "
    "Learning Methods. SIGIR 2009.",
    "J. Chen, S. Xiao, P. Zhang, K. Luo, D. Lian, Z. Liu. BGE M3-Embedding: Multi-Lingual, Multi-Functionality, "
    "Multi-Granularity Text Embeddings Through Self-Knowledge Distillation. arXiv:2402.03216, 2024.",
    "Y. Zhang và cộng sự. Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models. "
    "arXiv:2506.05176, 2025.",
    "Qwen Team. Qwen3 Technical Report. arXiv:2505.09388, 2025.",
    "Gemma Team. Gemma 3 Technical Report. arXiv:2503.19786, 2025.",
    "A. Barbaresi. Trafilatura: A Web Scraping Library and Command-Line Tool for Text Discovery and Extraction. "
    "ACL 2021 System Demonstrations.",
    "L. Gao, X. Ma, J. Lin, J. Callan. Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE). ACL 2023.",
    "J. Sun. jieba: Chinese text segmentation. https://github.com/fxsjy/jieba",
    "AIGuruTinix/ViBioMIR (danh sách URL và câu hỏi của BTC); snute/ai_guru-S3 (dữ liệu crawl dùng chung), Hugging Face.",
]
for i, r in enumerate(refs, 1):
    p = para(f"[{i}] {r}", align=WD_ALIGN_PARAGRAPH.LEFT, size=11)
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.first_line_indent = Cm(-0.8)
    p.paragraph_format.space_after = Pt(3)

doc.save(OUT)
print("→", OUT)
