// PDF của bạn: đọc PDF có lớp chữ ngay trong trình duyệt (pdf.js, chép sẵn trong vendor/, chạy được khi
// không có mạng), chia đoạn ~1.000 ký tự theo dòng như make_submission.py, tìm bằng BM25 trong phiên.
// File không gửi đi đâu; tải lại trang là mất.
import { i18n } from './i18n.js';
import { Bm25 } from './bm25.js';

const $ = s => document.querySelector(s);
const t = (k, v) => i18n.t(k, v);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const CHUNK = 1000;

const files = [];        // { name, pages, chunks: [{ text, page }], state: 'reading' | 'ok' | error key }
let index = null, refs = [];
let pdfjs = null;

async function lib() {
  if (!pdfjs) {
    pdfjs = await import('../vendor/pdfjs/pdf.min.mjs');
    pdfjs.GlobalWorkerOptions.workerSrc = new URL('../vendor/pdfjs/pdf.worker.min.mjs', import.meta.url).href;
  }
  return pdfjs;
}

function linesOf(content) {
  const lines = [];
  let cur = '';
  for (const it of content.items) {
    cur += it.str;
    if (it.hasEOL) { lines.push(cur.trim()); cur = ''; }
  }
  if (cur.trim()) lines.push(cur.trim());
  return lines.filter(Boolean);
}

function chunk(lines, page, out) {
  let buf = '';
  for (const line of lines) {
    if (buf && buf.length + line.length + 1 > CHUNK) { out.push({ text: buf, page }); buf = ''; }
    buf = buf ? buf + '\n' + line : line;
  }
  if (buf) out.push({ text: buf, page });
}

async function read(file) {
  const entry = { name: file.name, pages: 0, chunks: [], state: 'reading' };
  files.push(entry);
  render();
  if (!/\.pdf$/i.test(file.name) && file.type !== 'application/pdf') { entry.state = 'pdf.notPdf'; return render(); }
  try {
    const { getDocument } = await lib();
    const doc = await getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
    entry.pages = doc.numPages;
    for (let p = 1; p <= doc.numPages; p++) {
      const page = await doc.getPage(p);
      chunk(linesOf(await page.getTextContent()), p, entry.chunks);
    }
    const chars = entry.chunks.reduce((s, c) => s + c.text.length, 0);
    entry.state = chars < 20 * Math.max(1, doc.numPages) ? 'pdf.noText' : 'ok';
    if (entry.state !== 'ok') entry.chunks = [];
  } catch {
    entry.state = 'pdf.err';
  }
  rebuild();
  render();
}

function rebuild() {
  refs = files.flatMap(f => f.chunks.map(c => ({ file: f.name, page: c.page, text: c.text })));
  index = refs.length ? new Bm25(refs.map(r => r.text)) : null;
  $('#pdf-q').disabled = !index;
  window.dispatchEvent(new Event('vb:uploads'));
}

function render() {
  const list = $('#pdf-files');
  list.replaceChildren(...files.map((f, i) => {
    const li = el('li');
    if (f.state !== 'ok' && f.state !== 'reading') li.className = 'is-err';
    const info = el('span');
    info.append(el('span', null, f.name + ' '),
      el('small', null, f.state === 'reading' ? t('pdf.reading') : f.state === 'ok' ? t('pdf.ok', { pages: f.pages, chunks: f.chunks.length }) : t(f.state)));
    const rm = el('button', null, '✕');
    rm.type = 'button';
    rm.setAttribute('aria-label', t('pdf.remove', { name: f.name }));
    rm.addEventListener('click', () => { files.splice(i, 1); rebuild(); render(); searchHere(); });
    li.append(info, rm);
    return li;
  }));
}

function searchHere() {
  const q = $('#pdf-q').value.trim();
  const out = $('#pdf-results');
  if (!q || !index) { out.replaceChildren(); return; }
  const hits = search(q, 10);
  if (!hits.length) { out.replaceChildren(el('li', 'rs', t('pdf.nohit'))); return; }
  out.replaceChildren(...hits.map((h, i) => {
    const li = el('li');
    const head = el('div', 'ri__head');
    head.append(el('span', 'ri__rank', i + 1), el('span', 'ri__title', h.file), el('span', 'ri__host', t('ri.page', { p: h.page })));
    const p = el('p', 'ri__chunk', h.text);
    li.append(head, p);
    return li;
  }));
}

function search(q, k = 10) {
  return index ? index.search(q, k).map(([i, score]) => ({ ...refs[i], score })) : [];
}

window.vbUploads = { get count() { return refs.length; }, search };

const box = $('[data-pdf]');
const input = $('#pdf-input');
input.addEventListener('change', () => { [...input.files].forEach(read); input.value = ''; });
box.addEventListener('dragover', e => { e.preventDefault(); box.classList.add('is-over'); });
box.addEventListener('dragleave', e => { if (!box.contains(e.relatedTarget)) box.classList.remove('is-over'); });
box.addEventListener('drop', e => { e.preventDefault(); box.classList.remove('is-over'); [...e.dataTransfer.files].forEach(read); });
let timer = 0;
$('#pdf-q').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(searchHere, 150); });
i18n.onChange(() => { render(); searchHere(); });
