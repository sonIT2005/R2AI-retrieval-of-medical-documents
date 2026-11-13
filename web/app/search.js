// Khu tra cứu: 1.200 câu, gợi ý câu mẫu gần nhất, kết quả theo hạng, lọc ngôn ngữ.
// Hai danh sách chia trang vừa đúng khung (không cuộn ẩn bên trong): đổ từng mục tới khi đầy thì dừng.
// Dữ liệu: data/questions.json và data/q/<id>.json do tools/build_demo_data.py dựng.
import { i18n } from './i18n.js';
import { Bm25 } from './bm25.js';

const $ = s => document.querySelector(s);
const t = (k, v) => i18n.t(k, v);
const fmt = n => n.toLocaleString(i18n.lang === 'en' ? 'en-US' : 'vi-VN');
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

let meta = null, index = null, current = null, docs = [], langFilter = '', pdfView = null;
let qStart = 0, qCount = 0, rStart = 0, rCount = 0;
const qHist = [], rHist = [];   // điểm bắt đầu các trang trước, để nút "Trước" quay đúng trang

// Đổ mục vào ol cho tới khi đầy khung; trả về số mục đã giữ (ít nhất 1).
function fill(ol, items, start, make) {
  ol.replaceChildren();
  let n = 0;
  for (let i = start; i < items.length; i++) {
    const li = make(items[i]);
    ol.append(li);
    if (ol.scrollHeight > ol.clientHeight + 1 && n > 0) { li.remove(); break; }
    n++;
  }
  return n;
}

async function init() {
  status(t('st.loading'));
  try {
    const r = await fetch('data/questions.json');
    if (!r.ok) throw new Error(r.status);
    meta = await r.json();
  } catch {
    status(t('st.nodata'));
    return;
  }
  index = new Bm25(meta.questions.map(q => q.vi));
  // mặc định câu 341 (rụng tóc), cùng câu với cửa sổ ở hero; #q=<id> trên URL mở câu khác
  const fromHash = Number(new URLSearchParams(location.hash.slice(1)).get('q'));
  const start = [fromHash, 341].find(id => meta.questions.some(q => q.id === id)) ?? meta.questions[0].id;
  select(start, true);
}

function status(text) { $('#r-status').textContent = text; }

// --- Danh sách câu hỏi ---
function qItem(q) {
  const li = el('li');
  const b = el('button');
  b.type = 'button';
  b.dataset.id = q.id;
  if (current && q.id === current.id) b.setAttribute('aria-current', 'true');
  b.append(el('span', 'n', q.id), el('span', null, q.vi));
  li.append(b);
  return li;
}
function renderList() {
  if (!meta) return;
  qCount = fill($('#q-list'), meta.questions, qStart, qItem);
  const end = qStart + qCount;
  $('#q-page').textContent = `${fmt(qStart + 1)}–${fmt(end)} / ${fmt(meta.questions.length)}`;
  $('#q-prev').disabled = qStart === 0;
  $('#q-next').disabled = end >= meta.questions.length;
}

async function select(id, jump = false) {
  pdfView = null;
  current = meta.questions.find(q => q.id === id);
  if (jump) { qStart = meta.questions.indexOf(current); qHist.length = 0; }
  renderList();
  $('#qh-vi').textContent = current.vi;
  $('#qh-tr').textContent = [current.zh, current.en].filter(Boolean).join(' · ');
  docs = [];
  rStart = 0; rHist.length = 0;
  status(t('st.loading'));
  $('#r-list').replaceChildren();
  try {
    const r = await fetch(`data/q/${id}.json`);
    if (current.id !== id) return;
    docs = (await r.json()).docs;
  } catch {
    status(t('st.nodata'));
    return;
  }
  renderResults();
}

// --- Kết quả ---
function visible() { return langFilter ? docs.filter(d => d.lang === langFilter) : docs; }

function renderResults() {
  if (pdfView) return renderPdfResults();
  const list = visible();
  const nvi = docs.filter(d => d.lang === 'vi').length, nzh = docs.filter(d => d.lang === 'zh').length;
  let msg = list.length ? t('st.count', { n: docs.length, vi: nvi, zh: nzh }) : t('st.empty');
  if (meta && !meta.complete) msg += ' ' + t('st.partial');
  status(msg);
  $('#r-pager').hidden = false;   // giữ chỗ cho thanh phân trang trước khi đổ; pager() ẩn lại nếu vừa một trang
  rCount = list.length ? fill($('#r-list'), list, rStart, resultItem) : (($('#r-list').replaceChildren()), 0);
  pager(list.length);
}

function pager(total) {
  const end = rStart + rCount;
  $('#r-pager').hidden = total <= rCount;
  $('#r-page').textContent = total ? `${fmt(rStart + 1)}–${fmt(end)} / ${fmt(total)}` : '';
  $('#r-prev').disabled = rStart === 0;
  $('#r-next').disabled = end >= total;
}

function resultItem(d) {
  const li = el('li');
  const head = el('div', 'ri__head');
  head.append(el('span', 'ri__rank', d.rank));
  head.append(el('span', `ri__lang ri__lang--${d.lang}`, t('lang.' + d.lang)));
  const title = d.title || t('ri.doc', { id: d.doc_id });
  if (d.url) {
    const a = el('a', 'ri__title link', title);
    a.href = d.url; a.target = '_blank'; a.rel = 'noopener';
    if (d.lang) a.lang = d.lang;
    head.append(a);
  } else {
    head.append(el('span', 'ri__title', title));
  }
  if (d.host) head.append(el('span', 'ri__host', d.host));
  li.append(head);
  if (d.chunk) li.append(...chunkBlock(d.chunk, d.lang));
  return li;
}

function chunkBlock(text, lang) {
  const p = el('p', 'ri__chunk', text);
  if (lang) p.lang = lang;
  if (text.length < 240) return [p];
  const b = el('button', 'ri__toggle', t('ri.more'));
  b.type = 'button';
  b.addEventListener('click', () => {
    const open = p.classList.toggle('is-open');
    b.textContent = t(open ? 'ri.less' : 'ri.more');
    // mục đang mở giữ nguyên chỗ; các mục sau nó dời sang trang sau
    const ol = p.closest('ol');
    if (open && ol) { let next = p.closest('li').nextElementSibling; while (next) { const n = next.nextElementSibling; next.remove(); next = n; } }
    if (ol?.id === 'r-list') { rCount = ol.children.length; pager(pdfView ? 0 : visible().length); }
  });
  return [p, b];
}

// --- Kết quả trong PDF tải lên (upload.js đặt window.vbUploads) ---
function renderPdfResults() {
  const hits = window.vbUploads ? window.vbUploads.search(pdfView, 30) : [];
  $('#qh-vi').textContent = pdfView;
  $('#qh-tr').textContent = t('pdf.results', { q: pdfView });
  status(hits.length ? t('pdf.hits', { n: hits.length }) : t('pdf.nohit'));
  const make = h => {
    const li = el('li');
    const head = el('div', 'ri__head');
    head.append(el('span', 'ri__rank', h.rank), el('span', 'ri__lang ri__lang--pdf', t('ri.pdf')),
      el('span', 'ri__title', h.file), el('span', 'ri__host', t('ri.page', { p: h.page })));
    li.append(head, ...chunkBlock(h.text));
    return li;
  };
  const ranked = hits.map((h, i) => ({ ...h, rank: i + 1 }));
  $('#r-pager').hidden = false;
  rCount = ranked.length ? fill($('#r-list'), ranked, rStart, make) : (($('#r-list').replaceChildren()), 0);
  pager(ranked.length);
}

// --- Ô hỏi: gợi ý 3 câu mẫu gần nhất ---
let timer = 0;
function suggest() {
  const q = $('#q-input').value.trim();
  const box = $('#q-suggest');
  if (!q || !index) { box.hidden = true; box.replaceChildren(); return renderList(); }
  const top = index.search(q, 3);
  const nodes = [el('p', null, top.length ? t('sug.title') : t('sug.none'))];
  for (const [i] of top) {
    const qq = meta.questions[i];
    const b = el('button');
    b.type = 'button';
    b.append(el('span', 'n', qq.id), el('span', null, qq.vi));
    b.addEventListener('click', () => { closeSuggest(); select(qq.id, true); });
    nodes.push(b);
  }
  if (window.vbUploads?.count) {
    const b = el('button');
    b.type = 'button';
    b.append(el('span', 'n', 'PDF'), el('span', null, t('sug.pdf')));
    b.addEventListener('click', () => { closeSuggest(); pdfView = q; rStart = 0; rHist.length = 0; renderResults(); });
    nodes.push(b);
  }
  box.replaceChildren(...nodes);
  box.hidden = false;
  renderList();   // gợi ý chiếm chỗ: danh sách đổ lại cho vừa
}
function closeSuggest() { $('#q-suggest').hidden = true; renderList(); }

function bind() {
  $('#q-list').addEventListener('click', e => {
    const b = e.target.closest('button[data-id]');
    if (b) select(Number(b.dataset.id));
  });
  $('#q-prev').addEventListener('click', () => { qStart = qHist.pop() ?? Math.max(0, qStart - qCount); renderList(); });
  $('#q-next').addEventListener('click', () => { qHist.push(qStart); qStart += qCount; renderList(); });
  $('#r-prev').addEventListener('click', () => { rStart = rHist.pop() ?? Math.max(0, rStart - rCount); renderResults(); });
  $('#r-next').addEventListener('click', () => { rHist.push(rStart); rStart += rCount; renderResults(); });
  $('#q-input').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(suggest, 120); });
  $('#q-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); $('#q-suggest button')?.click(); }
    if (e.key === 'Escape') closeSuggest();
  });
  document.querySelectorAll('.chips .chip').forEach(c => c.addEventListener('click', () => {
    langFilter = c.dataset.lang;
    document.querySelectorAll('.chips .chip').forEach(o => o.setAttribute('aria-pressed', String(o === c)));
    rStart = 0; rHist.length = 0;
    pdfView = null;
    renderResults();
  }));
  i18n.onChange(() => { if (current) { renderList(); renderResults(); } if (!$('#q-suggest').hidden) suggest(); });
  window.addEventListener('vb:uploads', () => { if (pdfView) renderResults(); if (!$('#q-suggest').hidden) suggest(); });
  // khung đổi cỡ (xoay máy, đổi cửa sổ): chia trang lại
  let w = 0;
  new ResizeObserver(() => {
    const now = $('#q-list').clientHeight + 'x' + $('#r-list').clientHeight;
    if (now !== w) { w = now; renderList(); if (docs.length || pdfView) renderResults(); }
  }).observe($('[data-app]'));
}

bind();
init();
