// BM25 nhỏ chạy trong trình duyệt: gợi ý câu mẫu gần nhất và tìm trong PDF tải lên.
// Tiếng Việt: âm tiết + cặp âm tiết liền nhau (như lượt bm25bi_vi), thêm bản bỏ dấu để gõ không dấu vẫn khớp.
// Chữ Hán: từng chữ + cặp chữ liền nhau.
const HAN = /\p{Script=Han}/u;
const strip = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd');

export function tokenize(text) {
  const out = [];
  const words = (text || '').normalize('NFC').toLowerCase().match(/[\p{L}\p{N}]+/gu) || [];
  let prev = null;
  for (const w of words) {
    if (HAN.test(w)) {
      const chars = [...w];
      chars.forEach((c, i) => { out.push(c); if (i) out.push(chars[i - 1] + c); });
      prev = null;
      continue;
    }
    // luôn có bản bỏ dấu: gõ "huyet ap" vẫn khớp "huyết áp"; gõ có dấu khớp cả hai bản, nên đúng dấu được điểm cao hơn
    const bare = strip(w);
    out.push(w, '~' + bare);
    if (prev) out.push(prev + '_' + w, '~' + strip(prev) + '_' + bare);
    prev = w;
  }
  return out;
}

export class Bm25 {
  constructor(texts, k1 = 1.2, b = 0.75) {
    this.k1 = k1; this.b = b;
    this.docs = texts.map(t => {
      const tf = new Map();
      const toks = tokenize(t);
      for (const tok of toks) tf.set(tok, (tf.get(tok) || 0) + 1);
      return { tf, len: toks.length };
    });
    this.avg = this.docs.reduce((s, d) => s + d.len, 0) / Math.max(1, this.docs.length);
    this.df = new Map();
    for (const d of this.docs) for (const tok of d.tf.keys()) this.df.set(tok, (this.df.get(tok) || 0) + 1);
  }

  search(query, k = 10) {
    const n = this.docs.length;
    const terms = [...new Set(tokenize(query))].filter(t => this.df.has(t));
    if (!terms.length) return [];
    const idf = new Map(terms.map(t => [t, Math.log(1 + (n - this.df.get(t) + 0.5) / (this.df.get(t) + 0.5))]));
    const scores = [];
    this.docs.forEach((d, i) => {
      let s = 0;
      for (const t of terms) {
        const f = d.tf.get(t);
        if (f) s += idf.get(t) * f * (this.k1 + 1) / (f + this.k1 * (1 - this.b + this.b * d.len / this.avg));
      }
      if (s > 0) scores.push([i, s]);
    });
    return scores.sort((a, b) => b[1] - a[1]).slice(0, k);
  }
}
