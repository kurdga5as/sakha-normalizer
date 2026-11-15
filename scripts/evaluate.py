"""Замер нормализатора.

  python scripts/evaluate.py                      # открытый набор eval/testset.jsonl (split=test)
  python scripts/evaluate.py --split dev
  python scripts/evaluate.py --jsonl FILE --noisy-key sah_noisy --gold-key sah_gold   # любой другой набор

Считается по словам (без регистра):
  замены букв — то же, но только по словам, которые отличаются от эталона лишь заменой
                букв из таблицы (без опечаток, пропуска долгих гласных, латиницы целиком);
  исправлено  — доля «грязных» слов (написано ≠ эталон), которые стали равны эталону;
  испорчено   — доля правильных слов (написано = эталон), которые нормализатор изменил;
  русские     — доля слов в русских фразах (eval/russian.txt), которые изменились.
"""
import argparse, collections, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from sakha_normalizer import Normalizer
from sakha_normalizer.normalizer import WORD


def toks(s):
    return [w.lower() for w in WORD.findall(s)]


def score(n, rows, noisy_key, gold_key, prof_key='profile'):
    by = collections.defaultdict(collections.Counter)
    for r in rows:
        noisy, gold = r[noisy_key], r[gold_key]
        out = n.normalize(noisy)
        tn, tg, to = toks(noisy), toks(gold), toks(out)
        p = r.get(prof_key, 'all')
        for key in (p, 'ВСЕГО'):
            c = by[key]
            c['sent'] += 1
            if not (len(tn) == len(tg) == len(to)):
                c['skipped'] += 1
                continue
            for a, g, o in zip(tn, tg, to):
                if a != g:
                    c['dirty'] += 1
                    c['fixed'] += o == g
                    if n._cost(a, g) is not None:  # отличие только заменой букв из таблицы
                        c['dirty_sub'] += 1
                        c['fixed_sub'] += o == g
                else:
                    c['clean'] += 1
                    c['broken'] += o != g
                c['tok'] += 1
                c['ok_after'] += o == g
                c['ok_before'] += a == g
    return by


def fmt(by):
    lines = [f"{'профиль':10} {'предл':>6} {'пропущ':>6} {'грязных':>8} {'исправлено':>10} {'испорчено':>9} {'верно до':>8} {'верно после':>11} {'замены букв: исправлено':>24}"]
    for p in sorted(by, key=lambda x: (x == 'ВСЕГО', x)):
        c = by[p]
        pct = lambda a, b: f"{100 * a / b:.1f}%" if b else '—'
        lines.append(f"{p:10} {c['sent']:6} {c['skipped']:6} {c['dirty']:8} {pct(c['fixed'], c['dirty']):>10} "
                     f"{pct(c['broken'], c['clean']):>9} {pct(c['ok_before'], c['tok']):>8} {pct(c['ok_after'], c['tok']):>11} {pct(c['fixed_sub'], c['dirty_sub']):>14} из {c['dirty_sub']}")
    return '\n'.join(lines)


def russian(n, path):
    total = changed = 0
    bad = []
    for line in open(path, encoding='utf-8'):
        s = line.strip()
        if not s:
            continue
        out = n.normalize(s)
        a, b = toks(s), toks(out)
        total += len(a)
        d = sum(x != y for x, y in zip(a, b))
        changed += d
        if d:
            bad.append((s, out))
    return total, changed, bad


def mixed(n, path):
    rows = [json.loads(l) for l in open(path, encoding='utf-8') if l.strip()]
    ok = 0; bad = []
    for r in rows:
        out = n.normalize(r['in'])
        if out == r['out']:
            ok += 1
        else:
            bad.append((r['in'], out, r['out']))
    return len(rows), ok, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jsonl', default=os.path.join(HERE, '..', 'eval', 'testset.jsonl'))
    ap.add_argument('--split', default='test')
    ap.add_argument('--noisy-key', default='noisy')
    ap.add_argument('--gold-key', default='gold')
    ap.add_argument('--russian', default=os.path.join(HERE, '..', 'eval', 'russian.txt'))
    ap.add_argument('--mixed', default=os.path.join(HERE, '..', 'eval', 'mixed.jsonl'))
    ap.add_argument('--show', type=int, default=0, help='показать N ошибок')
    a = ap.parse_args()
    n = Normalizer()
    rows = [json.loads(l) for l in open(a.jsonl, encoding='utf-8')]
    if rows and 'split' in rows[0]:
        rows = [r for r in rows if r['split'] == a.split]
    t = time.time()
    by = score(n, rows, a.noisy_key, a.gold_key)
    dt = time.time() - t
    print(f"Набор: {os.path.basename(a.jsonl)} ({a.split if 'split' in (rows[0] if rows else {}) else 'весь'}), {len(rows)} предложений, {dt:.1f} c")
    print(fmt(by))
    tot, ch, bad = russian(n, a.russian)
    print(f"\nРусские фразы: изменено {ch} из {tot} слов ({100 * ch / max(tot, 1):.1f}%)")
    for s, o in bad[:a.show or 0]:
        print('   ', s, '→', o)
    tot, ok, badm = mixed(n, a.mixed)
    print(f"Смешанные фразы (ручной набор): верно {ok} из {tot}")
    for i, o, g in badm[:a.show or 0]:
        print('    вход:', i, '| вышло:', o, '| ждали:', g)
    if a.show:
        print('\nПримеры ошибок на наборе:')
        k = 0
        for r in rows:
            out = n.normalize(r[a.noisy_key])
            tn, tg, to = toks(r[a.noisy_key]), toks(r[a.gold_key]), toks(out)
            if len(tn) == len(tg) == len(to):
                errs = [(x, y, z) for x, y, z in zip(tn, tg, to) if y != z]
                if errs:
                    print('   ', r.get('profile'), errs[:4])
                    k += 1
            if k >= a.show:
                break


if __name__ == '__main__':
    main()
