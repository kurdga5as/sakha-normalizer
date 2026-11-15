"""Подбор порогов на dev-части открытого набора (test не трогаем)."""
import itertools, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from sakha_normalizer import Normalizer
from evaluate import score, russian, mixed

rows = [json.loads(l) for l in open(os.path.join(HERE, '..', 'eval', 'testset.jsonl'), encoding='utf-8')]
rows = [r for r in rows if r['split'] == 'dev']
base = Normalizer()
res = []
for kb, kbd, rb, cs in itertools.product([0.0, 0.5, 1.0, 1.5, 2.0, 3.0], [1.0, 2.0, 4.0], [2.0, 4.0], [0.2, 0.5, 1.0]):
    base.keep_bonus, base.keyboard_bonus, base.russian_bonus, base.cost_scale = kb, kbd, rb, cs
    base._best.cache_clear()
    c = score(base, rows, 'noisy', 'gold')['ВСЕГО']
    fixed = c['fixed'] / c['dirty']; broken = c['broken'] / c['clean']
    _, rch, _ = russian(base, os.path.join(HERE, '..', 'eval', 'russian.txt'))
    _, mok, _ = mixed(base, os.path.join(HERE, '..', 'eval', 'mixed.jsonl'))
    obj = fixed - 10 * broken - 0.01 * rch
    res.append((obj, kb, kbd, rb, cs, round(100 * fixed, 2), round(100 * broken, 2), rch, mok))
res.sort(reverse=True)
for r in res[:12]:
    print(r)
