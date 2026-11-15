# Источники / Sources

## Данные словаря и тестового набора / Lexicon and test data

| Что / What | Где / Where | Лицензия / License | Как использовано / Use |
|---|---|---|---|
| Sakha Corpus Mono (ailabykt): газеты «Кыым», «Эдэр саас», «Саха сирэ», улусные СМИ, фонды Национальной библиотеки РС(Я) (OCR), детская библиотека, НИИ Олонхо, FineWeb-2, MADLAD, OSCAR | https://huggingface.co/datasets/ailabykt/sakha-corpus-mono | CC BY 4.0 | частоты словоформ; 0,3% документов отложены для теста / word-form counts; 0.3% of documents held out for testing |
| Википедия на якутском (дамп 2026-09-01) / Sakha Wikipedia dump | https://sah.wikipedia.org, https://dumps.wikimedia.org/sahwiki/ | CC BY-SA 4.0 | частоты словоформ; 0,3% статей отложены / word-form counts; 0.3% of articles held out |
| Sakha–Russian Parallel Corpus (ailabykt), колонка `ru` | https://huggingface.co/datasets/ailabykt/sakha-russian-parallel | CC BY 4.0 | частоты русских словоформ (чтобы не трогать русские слова) / Russian word-form counts |

В словари попали только словоформы и их частоты (не тексты). В якутский словарь
шли только строки, набранные с якутскими буквами (доля ҕ ҥ ө һ ү ≥ 2,5%),
чтобы чатовые написания вроде «кун» не считались правильными; минимальная частота 5.

Only word forms and counts are stored, not texts. The Sakha lexicon counts only lines typed
with Sakha letters (share of ҕ ҥ ө һ ү ≥ 2.5%), so chat spellings like «кун» are not
learned as correct; minimum frequency 5.

Тестовый набор `eval/testset.jsonl` — предложения из отложенных документов
(не вошли в словарь) с искусственным шумом; источник указан в каждой строке.
`eval/russian.txt` и `eval/mixed.jsonl` написаны авторами пакета.

The test set `eval/testset.jsonl` consists of sentences from held-out documents
(not used for the lexicon) with synthetic noise; the source is given on each line.
`eval/russian.txt` and `eval/mixed.jsonl` were written by the package authors.

## Таблица замен / Substitution table

Замены букв взяты из исследований письма в интернете:

- Леонтьев Н. А. (СВФУ), 2014: на форумах только ~6% сообщений набраны якутскими буквами;
  частые замены ө→е, ү→у, һ→ь. / Leontiev N. A., 2014: only ~6% of forum posts used Sakha
  letters; common substitutions ө→е, ү→у, һ→ь.
- Everstova M., Efimov N., Basile V. Bootstrapping NLP for Sakha: NER and Sentiment Analysis.
  LREC 2026: замены ө→о/8, ҕ→г/х/5, һ→ь/с/h (62% форумных фраз). / substitutions
  ө→o/8, ҕ→г/х/5, һ→ь/с/h in 62% of forum sentences.

Живая переписка в пакет не входит ни в каком виде (ни тексты, ни слова, ни примеры).
No private chat data is included in any form (no texts, words or examples).
