// Chuyển Việt/Anh. Chữ tiếng Việt nằm sẵn trong HTML (data-i18n); bản tiếng Anh ở đây.
// Chuỗi động (trạng thái, nút) có cả hai bản trong DYN.
const EN = {
  'skip': 'Skip to content',
  'nav.label': 'Main', 'nav.search': 'Search', 'nav.how': 'How it works', 'nav.upload': 'Your PDFs',
  'cta': 'Try a search',
  'hero.pill': 'Team loi_cuda · R2AI 2026', 'hero.pill2': 'See the three steps',
  'hero.h1': 'Vietnamese–Chinese medical search',
  'hero.lead': 'Type a health question in Vietnamese: the system searches 1.2 million Vietnamese, Chinese and PubMed pages, then quotes the passage that answers it.',
  'hero.how': 'See how it works',
  'hero.window': 'A question about hair loss translated into Chinese and English before the search',
  'search.h2': 'Documents for 1,200 contest questions',
  'search.lead': 'Pick a question on the left, or type your own to see the closest ones. Each list is the submitted run, ranked by Qwen3-Reranker.',
  'search.label': 'Question', 'search.ph': 'e.g. what to take for high blood pressure', 'search.list': '1,200 questions',
  'filter.label': 'Filter by language', 'filter.all': 'All', 'filter.vi': 'Vietnamese', 'filter.zh': 'Chinese',
  'pg.qprev': 'Previous page of questions', 'pg.qnext': 'Next page of questions',
  'pg.rprev': 'Previous page of results', 'pg.rnext': 'Next page of results',
  'how.h2': '3 steps from question to passage',
  'how.s1.h': 'Translate the question into Chinese and English',
  'how.s1.p': 'Qwen3-8B translates at temperature 0 and keeps numbers, units and drug names, so Chinese pages can be found too.',
  'how.s1.alt': 'Question 1039 in three languages',
  'how.s2.h': 'Search nine times, then merge the rankings',
  'how.s2.p': 'BM25 on syllables, syllable pairs and jieba words plus BGE-M3 vectors search each language group; RRF with k = 150 merges them.',
  'how.s3.h': 'Rerank 200 candidates, cut per question',
  'how.s3.p': 'Qwen3-Reranker-4B reads the question with the best-matching passage of 200 candidates; each question keeps its own number of documents, 140 on average, each with a 4,000-character passage.',
  'how.s3.alt': 'Candidates with reranker scores and the cut line',
  'pdf.h2': 'Add your own PDF documents',
  'pdf.p': 'Drop a PDF with a text layer into the box. The browser reads and splits it on this computer; the file goes nowhere and is gone when the page reloads.',
  'pdf.s1b': 'Read the text layer', 'pdf.s1': 'with pdf.js, page by page',
  'pdf.s2b': 'Split into passages', 'pdf.s2': 'of about 1,000 characters by line, as in the submission',
  'pdf.s3b': 'Search with BM25', 'pdf.s3': 'on syllables, syllable pairs and Chinese characters',
  'pdf.drop': 'Drop a PDF here or choose a file', 'pdf.hint': 'Text PDFs only; scanned PDFs are not supported yet',
  'pdf.label': 'Search your PDFs', 'pdf.ph': 'Type a phrase from the file',
  'close.h2': 'Try a search on 1,200 contest questions', 'close.p': 'Runs right here on this computer, no GPU needed.',
  'foot.lede': 'Vietnamese–Chinese medical retrieval, R2AI 2026', 'foot.q': '1,200 questions', 'foot.steps': 'Three steps',
  'foot.code': 'Source code', 'foot.med': 'Not a substitute for a doctor’s advice.',
  'foot.data': 'Data: ViBioMIR (R2AI 2026 organisers), snute/ai_guru-S3 · CC BY-NC',
};

const DYN = {
  vi: {
    'st.loading': 'Đang tải…',
    'st.count': '{n} tài liệu · {vi} Việt, {zh} Trung',
    'st.partial': '· dữ liệu tạm: thứ tự trước reranker, chưa có đoạn trích',
    'st.nodata': 'Chưa có dữ liệu: chạy python tools/build_demo_data.py ở gốc repo.',
    'st.empty': 'Không có tài liệu nào ở ngôn ngữ này.',
    'sug.title': 'Câu mẫu gần nhất', 'sug.none': 'Không có câu mẫu nào gần với câu này.',
    'sug.pdf': 'Tìm câu này trong PDF của bạn',
    'ri.doc': 'Tài liệu #{id}', 'ri.more': 'Xem cả đoạn', 'ri.less': 'Thu gọn', 'ri.pdf': 'PDF của bạn', 'ri.page': 'trang {p}',
    'lang.vi': 'Việt', 'lang.zh': 'Trung', 'lang.en': 'Anh',
    'more': 'Xem thêm {n} tài liệu',
    'pdf.reading': 'Đang đọc…', 'pdf.ok': '{pages} trang · {chunks} đoạn',
    'pdf.noText': 'Không có lớp chữ (PDF ảnh), chưa hỗ trợ', 'pdf.err': 'Không đọc được file này', 'pdf.notPdf': 'Không phải file PDF',
    'pdf.remove': 'Xoá {name}', 'pdf.hits': '{n} đoạn khớp', 'pdf.nohit': 'Không có đoạn nào khớp.',
    'pdf.results': 'Kết quả trong PDF của bạn cho: {q}',
    'toggle': 'EN', 'toggle.label': 'Xem bằng tiếng Anh',
  },
  en: {
    'st.loading': 'Loading…',
    'st.count': '{n} documents · {vi} Vietnamese, {zh} Chinese',
    'st.partial': '· interim data: order before reranking, no passages yet',
    'st.nodata': 'No data yet: run python tools/build_demo_data.py at the repo root.',
    'st.empty': 'No documents in this language.',
    'sug.title': 'Closest questions', 'sug.none': 'No question in the set is close to this one.',
    'sug.pdf': 'Search your PDFs for this',
    'ri.doc': 'Document #{id}', 'ri.more': 'Show the whole passage', 'ri.less': 'Show less', 'ri.pdf': 'Your PDF', 'ri.page': 'page {p}',
    'lang.vi': 'Vietnamese', 'lang.zh': 'Chinese', 'lang.en': 'English',
    'more': 'Show {n} more documents',
    'pdf.reading': 'Reading…', 'pdf.ok': '{pages} pages · {chunks} passages',
    'pdf.noText': 'No text layer (scanned PDF), not supported yet', 'pdf.err': 'Could not read this file', 'pdf.notPdf': 'Not a PDF file',
    'pdf.remove': 'Remove {name}', 'pdf.hits': '{n} matching passages', 'pdf.nohit': 'No passage matches.',
    'pdf.results': 'Results in your PDFs for: {q}',
    'toggle': 'VI', 'toggle.label': 'Xem bằng tiếng Việt',
  },
};

const viText = new Map();
const viAttr = new Map();
const listeners = [];
let lang = 'vi';

function capture() {
  document.querySelectorAll('[data-i18n]').forEach(el => viText.set(el, el.textContent));
  document.querySelectorAll('[data-i18n-attr]').forEach(el => {
    const pairs = el.dataset.i18nAttr.split(';').map(p => p.split(':'));
    viAttr.set(el, pairs.map(([a, k]) => [a, k, el.getAttribute(a)]));
  });
}

function apply() {
  document.documentElement.lang = lang;
  viText.forEach((vi, el) => { el.textContent = lang === 'en' ? (EN[el.dataset.i18n] ?? vi) : vi; });
  viAttr.forEach((pairs, el) => pairs.forEach(([a, k, vi]) => el.setAttribute(a, lang === 'en' ? (EN[k] ?? vi) : vi)));
  const btn = document.querySelector('[data-lang-toggle]');
  if (btn) { btn.textContent = DYN[lang].toggle; btn.setAttribute('aria-label', DYN[lang]['toggle.label']); }
  listeners.forEach(fn => fn(lang));
}

export const i18n = {
  get lang() { return lang; },
  t(key, vars = {}) {
    const s = DYN[lang][key] ?? DYN.vi[key] ?? key;
    return s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');
  },
  onChange(fn) { listeners.push(fn); },
  set(l) {
    lang = l === 'en' ? 'en' : 'vi';
    try { localStorage.setItem('vb-lang', lang); } catch { /* không lưu được thì thôi */ }
    apply();
  },
};

capture();
document.querySelector('[data-lang-toggle]')?.addEventListener('click', () => i18n.set(lang === 'en' ? 'vi' : 'en'));
let saved = 'vi';
try { saved = localStorage.getItem('vb-lang') || 'vi'; } catch { /* trình duyệt chặn lưu trữ */ }
if (saved === 'en') i18n.set('en');
