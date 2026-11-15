/* Нормализатор живого якутского письма: порт sakha_normalizer (Python) v0.1.1 на JavaScript.
   Те же правила, словарь и пороги; ответы сверены с Python на открытом тестовом наборе.
   Только для машин: человеку нормализованный текст не показывается. MIT. */
(function (root) {
  'use strict';

  const SAH_LETTERS = 'ҕҥөһү';
  const VARIANT = { 'ғ': 'ҕ', 'ң': 'ҥ', 'ӈ': 'ҥ', 'ҋ': 'й', 'ɵ': 'ө', 'ѳ': 'ө', 'ӧ': 'ө', 'ӱ': 'ү', 'ë': 'ё' };
  const LATIN_LOOKALIKE = { a: 'а', c: 'с', e: 'е', o: 'о', p: 'р', x: 'х', k: 'к', m: 'м', t: 'т', b: 'ь',
    y: 'у', h: 'һ', u: 'и', n: 'п', r: 'г', g: 'ҕ', s: 'с' };
  const SUBST = {
    'г': [['ҕ', 0.7]],
    'х': [['ҕ', 2.5], ['һ', 2.5]],
    'н': [['ҥ', 1.2]],
    'о': [['ө', 0.7]],
    'е': [['ө', 1.6]],
    'э': [['ө', 3.0]],
    'у': [['ү', 0.7]],
    'ь': [['һ', 1.0]],
    'с': [['һ', 3.5]],
    'һ': [['х', 3.0]],
    '5': [['ҕ', 0.0]],
    '8': [['ө', 0.0]],
    '0': [['ө', 0.1], ['о', 0.3]],
    '9': [['ҕ', 0.5]],
    '4': [['ч', 0.5]],
    '6': [['б', 0.5]],
    '3': [['з', 0.5]],
    'h': [['һ', 0.0], ['н', 1.5]],
    'y': [['ү', 0.0], ['у', 0.3]],
    'o': [['о', 0.0], ['ө', 0.3]],
    'u': [['ү', 0.2], ['у', 0.3], ['и', 0.5]],
    'g': [['ҕ', 0.0], ['г', 0.3]],
    'n': [['ҥ', 0.3], ['н', 0.3], ['п', 0.6]],
  };
  for (const [lat, cyr] of Object.entries(LATIN_LOOKALIKE)) if (!(lat in SUBST)) SUBST[lat] = [[cyr, 0.0]];

  const CYR = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' + SAH_LETTERS;
  const VARIANT_KEYS = Object.keys(VARIANT).join('');
  const esc = s => s.replace(/[\]\\^-]/g, '\\$&');
  const WORD = new RegExp('[0-9A-Za-z' + esc(CYR + CYR.toUpperCase() + VARIANT_KEYS + VARIANT_KEYS.toUpperCase()) + ']+', 'gu');
  const SKIP = /(?:https?:\/\/|www\.)\S+|\S+@\S+\.\S+|[@#][\p{L}\p{N}_]+/gu;
  const HAS_CYR = new RegExp('[' + CYR + ']', 'u');
  const ONLY_LATIN = /^[A-Za-z]+$/;
  const LEADING_DIGITS = /^\d+/;
  const VOWEL = /[аэиыоуөүяеёю0-9a-z]/u;
  const SOFT_AS_SHHA = /(?:^|[аэиыоуөүяеёю])ь/u;
  const VOWELS_AFTER_SOFT = 'аэиыоуөүяеёю';
  const IS_ALPHA = /\p{L}/u;

  const VARIANT_T = {};
  for (const [k, v] of Object.entries(VARIANT)) { VARIANT_T[k] = v; VARIANT_T[k.toUpperCase()] = v.toUpperCase(); }
  const translateVariants = w => Array.from(w, ch => VARIANT_T[ch] || ch).join('');

  // Классы букв, которые могут подменять друг друга (ключ индекса словаря).
  const FOLD = (() => {
    const parent = {};
    const find = x => {
      if (!(x in parent)) parent[x] = x;
      while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x]; }
      return x;
    };
    for (const [src, opts] of Object.entries(SUBST)) for (const [dst] of opts) parent[find(src)] = find(dst);
    const out = {};
    for (const ch of Object.keys(parent)) out[ch] = find(ch);
    return out;
  })();
  const fold = w => Array.from(w, ch => FOLD[ch] || ch).join('');

  const isUpper = s => s === s.toUpperCase() && s !== s.toLowerCase();
  const isDigits = s => /^\p{Nd}+$/u.test(s);

  function restoreCase(orig, neu) {
    const o = Array.from(orig), n = Array.from(neu);
    if (o.length !== n.length) {
      return o.length && isUpper(o[0]) ? n[0].toUpperCase() + n.slice(1).join('') : neu;
    }
    if (isUpper(orig) && o.length > 1) return neu.toUpperCase();
    return n.map((ch, i) => (isUpper(o[i]) ? ch.toUpperCase() : ch)).join('');
  }

  class Normalizer {
    /** sahTsv, ruTsv — содержимое sah_lexicon.tsv и ru_lexicon.tsv («слово\tчастота» в строке). */
    constructor(sahTsv, ruTsv, opts = {}) {
      this.groups = new Map();
      this.sahTotal = 0;
      for (const line of sahTsv.split('\n')) {
        if (!line) continue;
        const tab = line.indexOf('\t');
        const w = line.slice(0, tab), n = line.slice(tab + 1);
        this.sahTotal += +n;
        const k = fold(w);
        const prev = this.groups.get(k);
        this.groups.set(k, prev === undefined ? w + ' ' + n : prev + ' ' + w + ' ' + n);
      }
      this.ru = new Map();
      this.ruTotal = 0;
      for (const line of ruTsv.split('\n')) {
        if (!line) continue;
        const tab = line.indexOf('\t');
        const n = +line.slice(tab + 1);
        this.ru.set(line.slice(0, tab), n);
        this.ruTotal += n;
      }
      this.keepBonus = opts.keepBonus ?? 0.5;
      this.keyboardBonus = opts.keyboardBonus ?? 1.0;
      this.russianBonus = opts.russianBonus ?? 2.0;
      this.costScale = opts.costScale ?? 1.0;
      this.oovFloor = opts.oovFloor ?? -19.0;
      this.cache = new Map();
    }

    entries(key) {
      const packed = this.groups.get(key);
      if (!packed) return [];
      const p = packed.split(' ');
      const out = [];
      for (let i = 0; i < p.length; i += 2) out.push([p[i], +p[i + 1]]);
      return out;
    }

    sahCount(word) {
      for (const [w, n] of this.entries(fold(word))) if (w === word) return n;
      return undefined;
    }

    logpSah(w) { const n = this.sahCount(w); return n ? Math.log(n / this.sahTotal) : null; }
    logpRu(w) { const n = this.ru.get(w); return n ? Math.log(n / this.ruTotal) : null; }

    isRussian(w) {
      const r = this.logpRu(w);
      if (r === null || Array.from(w).some(c => SAH_LETTERS.includes(c))) return false;
      const s = this.logpSah(w);
      return s === null || r > s;
    }

    static cost(src, dst) {
      const a = Array.from(src), b = Array.from(dst);
      if (a.length !== b.length) return null;
      let total = 0;
      for (let i = 0; i < a.length; i++) {
        if (a[i] === b[i]) continue;
        const opt = (SUBST[a[i]] || []).find(([d]) => d === b[i]);
        if (!opt) return null;
        total += opt[1];
      }
      return total;
    }

    candidates(w) {
      const out = [];
      const keys = [fold(w)];
      const alt = w.includes('нг') ? w.split('нг').join('ҥ') : null;
      if (alt !== null && !keys.includes(fold(alt))) keys.push(fold(alt));
      const len = Array.from(w).length;
      for (const k of keys) {
        for (const [cand] of this.entries(k)) {
          const src = Array.from(cand).length === len ? w : alt;
          if (src === null) continue;
          let c = Normalizer.cost(src, cand);
          if (c === null) continue;
          if (src !== w) c += 0.5;
          out.push([cand, c]);
        }
      }
      return out;
    }

    forced(w) {
      for (const ch of w) if (!((ch >= 'а' && ch <= 'я') || 'ёҕҥөһү'.includes(ch))) return true;
      return SOFT_AS_SHHA.test(w);
    }

    static deterministic(w) {
      const a = Array.from(w);
      return a.map((ch, i) => {
        const prevL = i > 0 && IS_ALPHA.test(a[i - 1]);
        const nextL = i + 1 < a.length && IS_ALPHA.test(a[i + 1]);
        if (ch === '5' && prevL) return 'ҕ';
        if (ch === '8' && (prevL || nextL)) return 'ө';
        if (ch === '0' && prevL && nextL) return 'ө';
        if (ch === 'ь' && (i === 0 || VOWELS_AFTER_SOFT.includes(a[i - 1]))) return 'һ';
        if (ch === 'h') return 'һ';
        if (ch in LATIN_LOOKALIKE) return ch !== 'y' ? LATIN_LOOKALIKE[ch] : 'ү';
        return ch;
      }).join('');
    }

    best(w, keyboard, russianCtx) {
      const key = w + '\u0001' + (keyboard ? 1 : 0) + (russianCtx ? 1 : 0);
      if (this.cache.has(key)) return this.cache.get(key);
      const r = this._best(w, keyboard, russianCtx);
      if (this.cache.size > 200000) this.cache.clear();
      this.cache.set(key, r);
      return r;
    }

    _best(w, keyboard, russianCtx) {
      const forced = this.forced(w);
      const a = Array.from(w);
      if (LEADING_DIGITS.test(w) && (!'58'.includes(a[0]) || (a.length > 1 && isDigits(a[1])))) return w;
      const cands = this.candidates(w);
      let idScore = null;
      if (!forced) {
        const s = this.logpSah(w), r = this.logpRu(w);
        if (s !== null || r !== null) idScore = Math.max(...[s, r].filter(x => x !== null));
      }
      let best = null, bestScore = -1e9;
      for (const [cand, cost] of cands) {
        if (cand === w) continue;
        const s = this.logpSah(cand) - cost * (keyboard ? 1.0 : this.costScale);
        if (s > bestScore) { best = cand; bestScore = s; }
      }
      if (best === null) return forced ? Normalizer.deterministic(w) : w;
      if (idScore === null) {
        if (!forced && bestScore < this.oovFloor) return w;
        return best;
      }
      let bonus = this.keepBonus;
      if (keyboard) bonus += this.keyboardBonus;
      if (russianCtx || this.isRussian(w)) bonus += this.russianBonus;
      return bestScore > idScore + bonus ? best : w;
    }

    context(words) {
      const lows = words.map(w => w.toLowerCase());
      const keyboard = lows.some(w => Array.from(w).some(ch => SAH_LETTERS.includes(ch)));
      const cyr = lows.filter(w => HAS_CYR.test(w) && !this.forced(w));
      const ru = cyr.filter(w => this.isRussian(w)).length;
      const russianCtx = cyr.length >= 3 && ru / cyr.length >= 0.6;
      return [keyboard, russianCtx];
    }

    normalizeWord(word, keyboard = false, russianCtx = false) {
      if (ONLY_LATIN.test(word) || !HAS_CYR.test(translateVariants(word.toLowerCase()))) {
        if (!(!ONLY_LATIN.test(word) && Array.from(word).some(ch => IS_ALPHA.test(ch)))) return word;
      }
      if (isDigits(word)) return word;
      if (Array.from(word).length <= 5 && isUpper(word) && !Array.from(word).some(ch => 'ҔҤӨҺҮ'.includes(ch))) return word;
      const low = translateVariants(word.toLowerCase());
      if (!VOWEL.test(low)) return word;
      return restoreCase(word, this.best(low, keyboard, russianCtx));
    }

    normalize(text) {
      if (!text) return text;
      const pieces = [];
      let pos = 0;
      for (const m of text.matchAll(SKIP)) {
        pieces.push([false, text.slice(pos, m.index)]);
        pieces.push([true, m[0]]);
        pos = m.index + m[0].length;
      }
      pieces.push([false, text.slice(pos)]);
      const words = [];
      for (const [skip, chunk] of pieces) if (!skip) for (const m of chunk.matchAll(WORD)) words.push(m[0]);
      const [keyboard, russianCtx] = this.context(words);
      return pieces.map(([skip, chunk]) => (skip ? chunk : chunk.replace(WORD, w => this.normalizeWord(w, keyboard, russianCtx)))).join('');
    }

    /** Нормализованный текст и куски для подсветки: {text} или {text, from}. */
    explain(text) {
      const out = this.normalize(text);
      const a = [...text.matchAll(WORD)], b = [...out.matchAll(WORD)];
      if (a.length !== b.length) return { normalized: out, pieces: [{ text: out }], changed: 0, words: b.length };
      const pieces = [];
      let pos = 0, changed = 0;
      a.forEach((ma, i) => {
        const mb = b[i];
        if (mb.index > pos) pieces.push({ text: out.slice(pos, mb.index) });
        if (ma[0] !== mb[0]) { changed++; pieces.push({ text: mb[0], from: ma[0] }); }
        else pieces.push({ text: mb[0] });
        pos = mb.index + mb[0].length;
      });
      if (pos < out.length) pieces.push({ text: out.slice(pos) });
      return { normalized: out, pieces, changed, words: b.length };
    }
  }

  const api = { Normalizer, fold, WORD };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SakhaNormalizer = api;
})(typeof self !== 'undefined' ? self : this);
