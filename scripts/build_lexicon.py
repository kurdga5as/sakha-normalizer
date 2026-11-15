"""Собирает словари словоформ для нормализатора из открытых корпусов.

Источники (только открытые лицензии):
  - ailabykt/sakha-corpus-mono (CC BY 4.0)            -> якутский словарь
  - Википедия на якутском, дамп 2026-09-01 (CC BY-SA 4.0) -> якутский словарь
  - ailabykt/sakha-russian-parallel, колонка ru (CC BY 4.0) -> русский словарь

0,3% документов откладываются (по хешу) и в словарь не идут: из них собирается
открытый тестовый набор (scripts/make_testset.py).

Запуск (нужен pyarrow только для сборки, сам нормализатор работает без него):
  python scripts/build_lexicon.py --root "../"   # корень папки sakha language
"""
import argparse, collections, glob, gzip, hashlib, json, os, re, sys

VARIANTS = str.maketrans({'ғ': 'ҕ', 'ң': 'ҥ', 'ӈ': 'ҥ', 'ɵ': 'ө', 'ӧ': 'ө', 'ӱ': 'ү', 'ё': 'ё'})
TOKEN = re.compile(r'[^\W\d_]+')
CYR = re.compile(r'^[а-яёҕҥөһү]+$')
SAH_LETTERS = set('ҕҥөһү')


def held_out(key: str) -> bool:
    return int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16) % 1000 < 3


def tokens(text):
    for t in TOKEN.findall(text.lower().translate(VARIANTS)):
        if CYR.match(t):
            yield t


def sakha_lines(text, min_share=0.025):
    """Строки, набранные с якутской раскладкой (доля ҕҥөһү среди букв >= 2,5%).

    В вебе и OCR есть якутский текст без якутских букв («кун» вместо «күн»):
    если считать его, «грязные» формы попадут в словарь как правильные.
    Русские строки тоже отсекаются: для них отдельный словарь.
    """
    for line in text.split('\n'):
        low = line.lower()
        letters = sum(c.isalpha() for c in low)
        if not letters:
            continue
        if sum(c in 'ҕҥөһү' for c in low) / letters >= min_share:
            yield line


def sah_tokens(text):
    for line in sakha_lines(text):
        yield from tokens(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='папка sakha language')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(__file__), '..', 'sakha_normalizer', 'data'))
    ap.add_argument('--holdout', default=os.path.join(os.path.dirname(__file__), '..', 'eval', 'holdout_docs.jsonl'))
    ap.add_argument('--min-freq', type=int, default=5)
    a = ap.parse_args()
    import pyarrow.parquet as pq

    sah = collections.Counter()
    ru = collections.Counter()
    stats = collections.Counter()
    hold = open(a.holdout, 'w', encoding='utf-8')

    for path in sorted(glob.glob(os.path.join(a.root, 'raw', 'ailabykt_mono', 'data', '*.parquet'))):
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(batch_size=2000, columns=['text', 'source']):
            for text, src in zip(batch.column('text').to_pylist(), batch.column('source').to_pylist()):
                if not text:
                    continue
                key = 'ailabykt:' + hashlib.md5(text[:2000].encode('utf-8')).hexdigest()
                if held_out(key):
                    hold.write(json.dumps({'source': 'ailabykt/sakha-corpus-mono:' + src, 'text': text}, ensure_ascii=False) + '\n')
                    stats['held_docs'] += 1
                    continue
                sah.update(sah_tokens(text))
                stats['docs_ailabykt'] += 1
        print(path, len(sah), file=sys.stderr)

    for line in open(os.path.join(a.root, 'data', 'sahwiki.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        if held_out('wiki:' + r['title']):
            hold.write(json.dumps({'source': 'sah.wikipedia:' + r['title'], 'text': r['text']}, ensure_ascii=False) + '\n')
            stats['held_docs'] += 1
            continue
        sah.update(sah_tokens(r['text']))
        stats['docs_wiki'] += 1
    hold.close()

    pf = pq.ParquetFile(os.path.join(a.root, 'raw', 'ailabykt_parallel', 'sakha-russian.parquet'))
    for batch in pf.iter_batches(batch_size=5000, columns=['ru']):
        for text in batch.column('ru').to_pylist():
            if text:
                ru.update(t for t in tokens(text) if not (set(t) & SAH_LETTERS))

    os.makedirs(a.out, exist_ok=True)
    for name, cnt, mf in (('sah_lexicon.tsv.gz', sah, a.min_freq), ('ru_lexicon.tsv.gz', ru, 2)):
        kept = [(w, n) for w, n in cnt.items() if n >= mf]
        kept.sort(key=lambda x: (-x[1], x[0]))
        with gzip.open(os.path.join(a.out, name), 'wt', encoding='utf-8', compresslevel=9) as f:
            for w, n in kept:
                f.write(f'{w}\t{n}\n')
        stats[name + ':forms'] = len(kept)
        stats[name + ':tokens'] = sum(n for _, n in kept)
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    json.dump(stats, open(os.path.join(a.out, 'lexicon_stats.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
