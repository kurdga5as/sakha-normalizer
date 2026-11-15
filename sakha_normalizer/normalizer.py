"""Нормализатор живого якутского письма (чат → стандартная орфография).

Только для внутреннего понимания: поиск, разбор, замеры. Человеку нормализованный
текст не показывается и людей не поправляет.

Как работает:
1. Текст режется на слова; ссылки, почты, @ники, #теги, числа, чисто латинские
   слова и аббревиатуры (ИП, ООО) не трогаются.
2. Однозначные замены делаются сразу: «5» внутри слова → «ҕ», латинская «h»
   в кириллическом слове → «һ», варианты букв из других алфавитов (ң, ӈ, ғ, ѳ) → якутские.
3. Для слова строятся все написания, достижимые по таблице замен
   (г→ҕ, н→ҥ, о/е/8/0→ө, у/y→ү, ь/с/х/h→һ и т. п.), и из них берутся те, что есть
   в словаре словоформ. Побеждает самое частое с учётом «цены» замен.
4. Слово, которое и так есть в словаре (якутском или русском), меняется, только
   если вариант с якутскими буквами встречается намного чаще. Если человек в этом
   сообщении уже пишет якутскими буквами или фраза по-русски, порог выше.

Только стандартная библиотека Python.
"""
from __future__ import annotations

import gzip
import math
import os
import re
from functools import lru_cache

__all__ = ['Normalizer', 'normalize']

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

SAH_LETTERS = 'ҕҥөһү'

# Буквы из других алфавитов, которыми иногда набирают якутские: меняются всегда.
VARIANT = {'ғ': 'ҕ', 'ң': 'ҥ', 'ӈ': 'ҥ', 'ҋ': 'й', 'ɵ': 'ө', 'ѳ': 'ө', 'ӧ': 'ө', 'ӱ': 'ү', 'ë': 'ё'}

# Латинские двойники кириллических букв (внутри кириллического слова).
LATIN_LOOKALIKE = {'a': 'а', 'c': 'с', 'e': 'е', 'o': 'о', 'p': 'р', 'x': 'х', 'k': 'к',
                   'm': 'м', 't': 'т', 'b': 'ь', 'y': 'у', 'h': 'һ', 'u': 'и', 'n': 'п',
                   'r': 'г', 'g': 'ҕ', 's': 'с'}

# Замены «как пишут» → «какая буква имелась в виду»: (стандартная буква, цена).
# Цена — штраф в натуральных логарифмах частоты: чем реже так пишут, тем выше.
SUBST = {
    'г': (('ҕ', 0.7),),
    'х': (('ҕ', 2.5), ('һ', 2.5)),
    'н': (('ҥ', 1.2),),
    'о': (('ө', 0.7),),
    'е': (('ө', 1.6),),
    'э': (('ө', 3.0),),
    'у': (('ү', 0.7),),
    'ь': (('һ', 1.0),),
    'с': (('һ', 3.5),),
    'һ': (('х', 3.0),),
    # цифры и латиница внутри слова: исходный вариант невозможен, цена маленькая
    '5': (('ҕ', 0.0),),
    '8': (('ө', 0.0),),
    '0': (('ө', 0.1), ('о', 0.3)),
    '9': (('ҕ', 0.5),),
    '4': (('ч', 0.5),),
    '6': (('б', 0.5),),
    '3': (('з', 0.5),),
    'h': (('һ', 0.0), ('н', 1.5)),
    'y': (('ү', 0.0), ('у', 0.3)),
    'o': (('о', 0.0), ('ө', 0.3)),
    'u': (('ү', 0.2), ('у', 0.3), ('и', 0.5)),
    'g': (('ҕ', 0.0), ('г', 0.3)),
    'n': (('ҥ', 0.3), ('н', 0.3), ('п', 0.6)),
}
for _lat, _cyr in LATIN_LOOKALIKE.items():
    SUBST.setdefault(_lat, ((_cyr, 0.0),))

CYR = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' + SAH_LETTERS
WORD = re.compile(r"[0-9A-Za-z" + CYR + CYR.upper() + ''.join(VARIANT) + ''.join(VARIANT).upper() + r"]+")
SKIP = re.compile(r"(?:https?://|www\.)\S+|\S+@\S+\.\S+|[@#]\w+", re.UNICODE)
HAS_CYR = re.compile('[' + CYR + ']')
ONLY_LATIN = re.compile(r'^[A-Za-z]+$')
LEADING_DIGITS = re.compile(r'^\d+')
_VOWEL = re.compile('[аэиыоуөүяеёю0-9a-z]')
_SOFT_AS_SHHA = re.compile(r'(?:^|[аэиыоуөүяеёю])ь')


def _fold_classes():
    """Классы букв, которые могут подменять друг друга (для индекса словаря)."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for src, opts in SUBST.items():
        for dst, _ in opts:
            parent[find(src)] = find(dst)
    return {ch: find(ch) for ch in parent}


FOLD = _fold_classes()


def fold(word: str) -> str:
    return ''.join(FOLD.get(ch, ch) for ch in word)


def _load_lexicon(path):
    freq = {}
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            w, _, n = line.rstrip('\n').partition('\t')
            freq[w] = int(n)
    return freq


class _FoldedLexicon:
    """Якутский словарь, сложенный по классам букв: ключ — fold(слово),
    значение — строка «слово частота слово частота…». Так он занимает втрое
    меньше памяти, чем два словаря (частоты + индекс кандидатов)."""

    def __init__(self, path):
        groups = {}
        self.total = 0
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            for line in f:
                w, _, n = line.rstrip('\n').partition('\t')
                self.total += int(n)
                k = fold(w)
                prev = groups.get(k)
                groups[k] = f'{w} {n}' if prev is None else f'{prev} {w} {n}'
        self.groups = groups

    def entries(self, key):
        packed = self.groups.get(key)
        if not packed:
            return ()
        parts = packed.split(' ')
        return [(parts[i], int(parts[i + 1])) for i in range(0, len(parts), 2)]

    def get(self, word, default=None):
        for w, n in self.entries(fold(word)):
            if w == word:
                return n
        return default

    def __contains__(self, word):
        return self.get(word) is not None


class Normalizer:
    """normalize(text) -> text. Создавать один раз: загрузка ~1 с, память ~100 МБ."""

    def __init__(self, data_dir: str = DATA_DIR,
                 keep_bonus: float = 0.5,
                 keyboard_bonus: float = 1.0,
                 russian_bonus: float = 2.0,
                 cost_scale: float = 1.0,
                 oov_floor: float = -19.0):
        self.sah = _FoldedLexicon(os.path.join(data_dir, 'sah_lexicon.tsv.gz'))
        self.ru = _load_lexicon(os.path.join(data_dir, 'ru_lexicon.tsv.gz'))
        self.sah_total = self.sah.total
        self.ru_total = sum(self.ru.values())
        # log-бонусы, подобраны на открытом dev-наборе
        self.keep_bonus = keep_bonus
        self.keyboard_bonus = keyboard_bonus
        self.russian_bonus = russian_bonus
        # без якутской раскладки замены — норма, их цена ниже
        self.cost_scale = cost_scale
        # минимальный log-вес варианта для слова, которого нет в словаре
        self.oov_floor = oov_floor

    # --- частоты -----------------------------------------------------------
    def logp_sah(self, w):
        n = self.sah.get(w)
        return math.log(n / self.sah_total) if n else None

    def logp_ru(self, w):
        n = self.ru.get(w)
        return math.log(n / self.ru_total) if n else None

    def is_russian(self, w):
        """Слово скорее русское, чем якутское (по частотам в двух корпусах)."""
        r = self.logp_ru(w)
        if r is None or any(c in SAH_LETTERS for c in w):
            return False
        s = self.logp_sah(w)
        return s is None or r > s

    # --- кандидаты ---------------------------------------------------------
    @staticmethod
    def _cost(src: str, dst: str):
        """Цена перехода от написанного к словарному слову; None — недостижимо."""
        if len(src) != len(dst):
            return None
        total = 0.0
        for a, b in zip(src, dst):
            if a == b:
                continue
            for d, c in SUBST.get(a, ()):
                if d == b:
                    total += c
                    break
            else:
                return None
        return total

    def candidates(self, w: str):
        out = []
        keys = {fold(w)}
        if 'нг' in w:
            keys.add(fold(w.replace('нг', 'ҥ')))
        for k in keys:
            for cand, _ in self.sah.entries(k):
                src = w if len(cand) == len(w) else w.replace('нг', 'ҥ')
                c = self._cost(src, cand)
                if c is None:
                    continue
                if src is not w:
                    c += 0.5
                out.append((cand, c))
        return out

    def _forced(self, w: str) -> bool:
        """В слове есть знак, которого в правильном слове быть не может:
        цифра, латиница или «ь» после гласной / в начале слова (так пишут «һ»)."""
        if any(not ('а' <= ch <= 'я' or ch in 'ёҕҥөһү') for ch in w):
            return True
        return bool(_SOFT_AS_SHHA.search(w))

    @staticmethod
    def _deterministic(w: str) -> str:
        """Однозначные замены, если словарь не помог."""
        out = []
        for i, ch in enumerate(w):
            prev_l = i > 0 and w[i - 1].isalpha()
            next_l = i + 1 < len(w) and w[i + 1].isalpha()
            if ch == '5' and prev_l:
                out.append('ҕ')
            elif ch == '8' and (prev_l or next_l):
                out.append('ө')
            elif ch == '0' and prev_l and next_l:
                out.append('ө')
            elif ch == 'ь' and (i == 0 or w[i - 1] in 'аэиыоуөүяеёю'):
                out.append('һ')
            elif ch == 'h':
                out.append('һ')
            elif ch in LATIN_LOOKALIKE:
                out.append(LATIN_LOOKALIKE[ch] if ch != 'y' else 'ү')
            else:
                out.append(ch)
        return ''.join(out)

    @lru_cache(maxsize=200_000)
    def _best(self, w: str, keyboard: bool, russian_ctx: bool) -> str:
        """w — слово в нижнем регистре без вариантных букв."""
        forced = self._forced(w)
        # Цифры в начале (5шт, 10к, 2гис) — это число с единицей, не трогаем.
        if LEADING_DIGITS.match(w) and (w[0] not in '58' or w[1:2].isdigit()):
            return w
        cands = self.candidates(w)
        if not forced:
            id_s = self.logp_sah(w)
            id_r = self.logp_ru(w)
            id_score = max(x for x in (id_s, id_r, None) if x is not None) if (id_s or id_r) else None
        else:
            id_score = None
        best, best_score = None, -1e9
        for cand, cost in cands:
            if cand == w:
                continue
            s = self.logp_sah(cand) - cost * (1.0 if keyboard else self.cost_scale)
            if s > best_score:
                best, best_score = cand, s
        if best is None:
            return self._deterministic(w) if forced else w
        if id_score is None:
            # слова нет в словаре: берём лучший вариант, если он не слишком редкий
            # и «дорогой» (иначе русские заимствования: «насоса» → «насоһа»)
            if not forced and best_score < self.oov_floor:
                return w
            return best
        bonus = self.keep_bonus
        if keyboard:
            bonus += self.keyboard_bonus
        if russian_ctx or self.is_russian(w):
            bonus += self.russian_bonus
        return best if best_score > id_score + bonus else w

    # --- текст -------------------------------------------------------------
    def _context(self, words):
        lows = [w.lower() for w in words]
        keyboard = any(ch in SAH_LETTERS for w in lows for ch in w)
        cyr = [w for w in lows if HAS_CYR.search(w) and not self._forced(w)]
        ru = sum(1 for w in cyr if self.is_russian(w))
        russian_ctx = len(cyr) >= 3 and ru / len(cyr) >= 0.6
        return keyboard, russian_ctx

    def normalize_word(self, word: str, keyboard: bool = False, russian_ctx: bool = False) -> str:
        if ONLY_LATIN.match(word) or not HAS_CYR.search(word.lower().translate(_VARIANT_T)):
            if not (ONLY_LATIN.match(word) is None and any(ch.isalpha() for ch in word)):
                return word
        if word.isdigit():
            return word
        # аббревиатуры: ИП, ООО, СВФУ — короткие слова целиком заглавными
        if len(word) <= 5 and word.isupper() and not any(ch in 'ҔҤӨҺҮ' for ch in word):
            return word
        low = word.lower().translate(_VARIANT_T)
        if not _VOWEL.search(low):
            return word  # сокращения без гласных: бьлх, мкр, шт
        out = self._best(low, keyboard, russian_ctx)
        return _restore_case(word, out)

    def normalize(self, text: str) -> str:
        if not text:
            return text
        pieces = []
        pos = 0
        for m in SKIP.finditer(text):
            pieces.append((False, text[pos:m.start()]))
            pieces.append((True, m.group(0)))
            pos = m.end()
        pieces.append((False, text[pos:]))
        words = [w for skip, chunk in pieces if not skip for w in WORD.findall(chunk)]
        keyboard, russian_ctx = self._context(words)
        out = []
        for skip, chunk in pieces:
            if skip:
                out.append(chunk)
            else:
                out.append(WORD.sub(lambda m: self.normalize_word(m.group(0), keyboard, russian_ctx), chunk))
        return ''.join(out)


_VARIANT_T = str.maketrans({**VARIANT, **{k.upper(): v.upper() for k, v in VARIANT.items()}})


def _restore_case(orig: str, new: str) -> str:
    if len(orig) != len(new):
        if orig[:1].isupper():
            return new[:1].upper() + new[1:]
        return new
    if orig.isupper() and len(orig) > 1:
        return new.upper()
    return ''.join(n.upper() if o.isupper() else n for o, n in zip(orig, new))


_default = None


def normalize(text: str) -> str:
    """Удобная функция: грузит словарь при первом вызове."""
    global _default
    if _default is None:
        _default = Normalizer()
    return _default.normalize(text)
