"""Открытый тестовый набор: предложения из отложенных документов (в словарь не вошли)
+ искусственный «чатовый» шум по известным заменам (Леонтьев 2014; Эверстова и др. 2026).

Выход: eval/testset.jsonl — поля id, split (dev/test), profile, gold, noisy, source.
Лицензия текстов — как у источника (CC BY 4.0 / CC BY-SA 4.0), см. SOURCES.md.
"""
import hashlib, json, os, random, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'eval', 'holdout_docs.jsonl')
OUT = os.path.join(HERE, '..', 'eval', 'testset.jsonl')

def mapper(table):
    def f(s, rng):
        return ''.join(_pick(table, ch, rng) for ch in s)
    return f

def _pick(table, ch, rng):
    low = ch.lower()
    if low not in table:
        return ch
    v = table[low]
    if isinstance(v, (list, tuple)):
        v = rng.choice(v)
    return v.upper() if ch.isupper() and len(v) == 1 and v.isalpha() else v

PROFILES = {
    # как в генераторе make_noisy.py: якутские буквы → русские, һ → латинская h
    'ru_fold':  mapper({'ҕ': 'г', 'ҥ': 'н', 'ө': 'о', 'ү': 'у', 'һ': 'h'}),
    # Леонтьев 2014: ө→е, ү→у, һ→ь (+ ҕ→г, ҥ→н)
    'leontiev': mapper({'ҕ': 'г', 'ҥ': 'н', 'ө': 'е', 'ү': 'у', 'һ': 'ь'}),
    # цифры и латиница
    'digits':   mapper({'ҕ': '5', 'ҥ': 'н', 'ө': '8', 'ү': 'y', 'һ': 'h'}),
    # Эверстова и др. 2026: вперемешку ө→о/8, ҕ→г/х/5, һ→ь/с/h
    'mixed':    mapper({'ҕ': ['г', 'х', '5'], 'ҥ': ['н', 'нг'], 'ө': ['о', '8'], 'ү': ['у', 'y'], 'һ': ['ь', 'с', 'h']}),
    # якутская раскладка есть, но без ҕ и ҥ
    'partial':  mapper({'ҕ': 'г', 'ҥ': 'н'}),
    # без изменений: проверка, что правильный текст не портится
    'clean':    lambda s, rng: s,
}

SENT = re.compile(r'(?<=[.!?…])\s+')

def main():
    rng = random.Random(2026)
    sents = []
    for line in open(SRC, encoding='utf-8'):
        d = json.loads(line)
        if ':natlib' in d['source']:
            continue  # OCR, много ошибок распознавания
        split = 'dev' if int(hashlib.md5(d['source'].encode() + d['text'][:200].encode()).hexdigest(), 16) % 2 == 0 else 'test'
        for s in SENT.split(d['text']):
            s = ' '.join(s.split())
            if not 40 <= len(s) <= 220:
                continue
            letters = [c for c in s.lower() if c.isalpha()]
            if not letters or sum(c in 'ҕҥөһү' for c in letters) / len(letters) < 0.03:
                continue  # нет якутских букв: русский текст или OCR без них
            if re.search(r'[A-Za-z]', s):
                continue
            sents.append((split, d['source'], s))
    rng.shuffle(sents)
    seen = set(); rows = []
    profiles = list(PROFILES)
    for split, src, s in sents:
        if s in seen:
            continue
        seen.add(s)
        prof = profiles[len(rows) % len(profiles)]
        rows.append({'id': len(rows) + 1, 'split': split, 'profile': prof, 'gold': s,
                     'noisy': PROFILES[prof](s, rng), 'source': src})
        if len(rows) >= 3000:
            break
    with open(OUT, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(len(rows), 'предложений →', OUT, {p: sum(r['split'] == p for r in rows) for p in ('dev', 'test')})

if __name__ == '__main__':
    main()
