---
language:
- sah
- ru
license: mit
tags:
- sakha
- yakut
- саха
- сахалыы
- text-normalization
- spelling
datasets:
- ailabykt/sakha-corpus-mono
- ailabykt/sakha-russian-parallel
pretty_name: Sakha chat-text normalizer
---

# Нормализатор живого якутского письма / Sakha chat-text normalizer

[![Hugging Face Model](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Model-yellow)](https://huggingface.co/Sulus-ai/sakha-normalizer)
[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces%20Demo-blue)](https://huggingface.co/spaces/Sulus-ai/sakha-normalizer-demo)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Русский](#русский) · [English](#english) · [Онлайн-демо](https://huggingface.co/spaces/Sulus-ai/sakha-normalizer-demo)

## Русский

В чатах и на форумах по-якутски пишут кто как может: на телефоне часто нет якутской
раскладки, поэтому вместо **ҕ** пишут «г», «х» или «5», вместо **ө** — «о», «е», «8»,
вместо **һ** — «ь», «с» или латинскую «h», вместо **ү** — «у» или «y», вместо **ҥ** — «н».
Это нормальное живое письмо. Но программам (поиску, чат-ботам, языковым моделям,
определителю языка) такое письмо понять труднее: «кун» для них не то же самое, что «күн».

`sakha_normalizer` делает из такого текста копию в стандартной орфографии:

```python
from sakha_normalizer import normalize

normalize("ба5ар кун бэрт учугэй, оскуолага барабыт")
# 'баҕар күн бэрт үчүгэй, оскуолаҕа барабыт'

normalize("колодкалар баар дуо? WhatsApp-ка ыыт, ИП Иванов")
# 'колодкалар баар дуо? WhatsApp-ка ыыт, ИП Иванов'   (русское, латиница, аббревиатуры — как есть)
```

### Не для исправления людей

Это инструмент **для машин**, а не для людей. Нормализованный текст нужен внутри
системы: для поиска, разбора, статистики, подготовки данных. Человеку его не показывают
и его письмо не «исправляют». Писать «ба5ар» — нормально; живой язык — это язык,
на котором говорят и пишут каждый день, как получается.

### Как работает

Это программа, а не нейросеть: только стандартная библиотека Python, без зависимостей.

1. Ссылки, почты, @ники, #теги, числа с единицами («5шт», «10к»), чисто латинские слова
   и аббревиатуры («ИП», «ООО») не трогаются.
2. Для каждого слова строятся все написания, достижимые по таблице замен
   (г/х/5→ҕ, н/нг→ҥ, о/е/8/0→ө, у/y→ү, ь/с/х/h→һ), и из них берутся те, что есть
   в частотном словаре (~470 тыс. словоформ). Побеждает самое частое с учётом «цены» замены.
3. Если слово уже есть в словаре как есть (якутском или русском), оно меняется, только если
   вариант с якутскими буквами встречается намного чаще. Если человек в этом сообщении уже
   пишет якутскими буквами или фраза по-русски, порог ещё выше.
4. Русские слова с якутскими окончаниями («колодкалар», «заказыҥ») остаются как есть.

### Установка

```bash
# Через pip напрямую из GitHub:
pip install git+https://github.com/kurdga5as/sakha-normalizer.git

# Или клонированием:
git clone https://github.com/kurdga5as/sakha-normalizer.git
cd sakha-normalizer
pip install .

# Или загрузка весов и кода из Hugging Face:
hf download Sulus-ai/sakha-normalizer --local-dir sakha-normalizer
pip install ./sakha-normalizer

# Быстрая проверка в терминале:
python -m sakha_normalizer "ба5ар кун учугэй"     # баҕар күн үчүгэй
```

или просто скопируйте папку `sakha_normalizer/` в проект. Загрузка словаря — меньше секунды,
память — около 120 МБ. Для многих вызовов создайте объект один раз:

```python
from sakha_normalizer import Normalizer
n = Normalizer()
n.normalize("...")
```

### Демо в браузере

В репозитории есть готовое веб-демо на чистом JavaScript (`demo/index.html`), работающее полностью локально через Web Worker (текст никуда не отправляется):
- Онлайн-версия в [Hugging Face Spaces](https://huggingface.co/spaces/Sulus-ai/sakha-normalizer-demo)
- Локально: достаточно запустить любой статический веб-сервер внутри папки `demo/` (например, `python -m http.server 8000 -d demo`) и открыть `http://localhost:8000`.

### Качество

Замер на открытом наборе `eval/testset.jsonl` (часть `test`, 1377 предложений из документов,
не вошедших в словарь; на них наложены замены букв шести видов). Считается по словам.

| Как искажён текст | Исправлено искажённых слов | Испорчено правильных слов |
|---|---|---|
| ҕ ҥ ө ү һ → г н о у h (без якутской раскладки) | 94,9% | 0,2% |
| ө→е, ү→у, һ→ь (Леонтьев 2014) | 95,4% | 0,0% |
| ҕ→5, ө→8, ү→y, һ→h (цифры и латиница) | 98,0% | 0,4% |
| вперемешку: ө→о/8, ҕ→г/х/5, һ→ь/с/h, ҥ→н/нг | 96,7% | 0,3% |
| раскладка есть, но без ҕ и ҥ | 90,9% | 0,1% |
| текст без ошибок | — | 0,3% |
| **всего** | **95,8%** | **0,2%** |

Доля правильных слов: было 77,0%, стало 98,9%. Русские фразы (`eval/russian.txt`, 240 слов):
изменено 0 слов. Смешанные фразы (`eval/mixed.jsonl`, 25 шт.): верно 25.
Скорость — около 14 тыс. сообщений в секунду, загрузка — меньше секунды, память — около 120 МБ.

Повторить: `python scripts/evaluate.py` (результат — `eval/RESULTS_test.txt`).

### Ограничения

- Слова, которых нет в словаре в правильном виде (редкие формы, новые слова, имена), не
  восстанавливаются, кроме однозначных случаев («5» внутри слова → «ҕ», «ь» после гласной → «һ»).
- Если и чатовое, и правильное написание — настоящие слова («сон» и «сөҥ», «уол» и «үөл»,
  «заказын» и «заказыҥ»), остаётся то, что написано. Контекст фразы почти не учитывается.
- Не исправляет опечатки, пропущенные долгие гласные и двойные согласные («сурук» вместо «суруук»),
  пунктуацию и регистр. Текст, целиком набранный латиницей («kuruk»), не переводится в кириллицу.
- Словарь собран по газетам, книгам и вебу; говоры и сленг покрыты слабо.
- Тестовый набор искусственный (шум наложен на правильные предложения по известным заменам);
  на живой переписке качество может отличаться.

### Лицензия и источники

Код — MIT (`LICENSE`). Словари и тестовые данные — CC BY-SA 4.0 (`LICENSE-DATA.md`).
Источники: корпуса [ailabykt/sakha-corpus-mono](https://huggingface.co/datasets/ailabykt/sakha-corpus-mono)
и [ailabykt/sakha-russian-parallel](https://huggingface.co/datasets/ailabykt/sakha-russian-parallel)
(CC BY 4.0), Википедия на якутском (CC BY-SA 4.0). Замены букв — по работам
Н. А. Леонтьева (2014) и М. Эверстовой и соавт. (LREC 2026). Подробно — `SOURCES.md`.

Пересобрать словарь: `python scripts/build_lexicon.py --root <папка с корпусами>` (нужен `pyarrow`).
Замер: `python scripts/evaluate.py`. Тесты: `python -m unittest discover -s tests`.

---

## English

People write Sakha (Yakut) in chats and forums however they can: phones often lack a Sakha
keyboard, so **ҕ** becomes «г», «х» or «5», **ө** becomes «о», «е» or «8», **һ** becomes «ь»,
«с» or Latin «h», **ү** becomes «у» or «y», **ҥ** becomes «н». This is normal living language,
but it is harder for software (search, chatbots, language models, language ID) to handle:
«кун» is not the same string as «күн» (day).

`sakha_normalizer` produces a copy of such text in standard spelling:

```python
from sakha_normalizer import normalize

normalize("ба5ар кун бэрт учугэй, оскуолага барабыт")
# 'баҕар күн бэрт үчүгэй, оскуолаҕа барабыт'

normalize("колодкалар баар дуо? WhatsApp-ка ыыт, ИП Иванов")
# unchanged: Russian words, Latin words and abbreviations are kept as is
```

### Not for correcting people

This is a tool **for machines**. The normalized copy is for internal use: search, parsing,
statistics, data preparation. Do not show it to people or use it to "correct" how they write.
Writing «ба5ар» is fine; a living language is the one people use every day, however they type it.

### How it works

Rule-based, pure Python standard library, no dependencies.

1. URLs, e-mails, @handles, #tags, numbers with units («5шт», «10к»), pure-Latin words and
   abbreviations («ИП», «ООО») are left untouched.
2. For each word, all spellings reachable through the substitution table
   (г/х/5→ҕ, н/нг→ҥ, о/е/8/0→ө, у/y→ү, ь/с/х/h→һ) are generated and looked up in a frequency
   lexicon (~470k word forms). The most frequent one wins, minus a per-substitution cost.
3. A word that already exists in the lexicon (Sakha or Russian) is changed only if the variant
   with Sakha letters is much more frequent. The threshold is higher when the message already
   contains Sakha letters or is mostly Russian.
4. Russian words with Sakha suffixes («колодкалар», «заказыҥ») are kept.

### Installation

```bash
# Via pip directly from GitHub:
pip install git+https://github.com/kurdga5as/sakha-normalizer.git

# Or by cloning:
git clone https://github.com/kurdga5as/sakha-normalizer.git
cd sakha-normalizer
pip install .

# Or download from Hugging Face:
hf download Sulus-ai/sakha-normalizer --local-dir sakha-normalizer
pip install ./sakha-normalizer

# Quick test from CLI:
python -m sakha_normalizer "ба5ар кун учугэй"     # баҕар күн үчүгэй
```

or copy the `sakha_normalizer/` folder. Loading takes under a second and ~120 MB of RAM;
create one `Normalizer()` object and reuse it.

### Browser Demo

A self-contained pure JavaScript demo is included in `demo/index.html` (runs locally via Web Worker, sending zero data to external servers):
- Live demo on [Hugging Face Spaces](https://huggingface.co/spaces/Sulus-ai/sakha-normalizer-demo)
- Locally: run any static web server (e.g., `python -m http.server 8000 -d demo`) and open `http://localhost:8000`.

### Quality

Measured on the open set `eval/testset.jsonl` (`test` split, 1,377 sentences from documents
excluded from the lexicon, with six kinds of letter substitutions applied). Word-level.

| Noise | Corrupted words restored | Correct words damaged |
|---|---|---|
| ҕ ҥ ө ү һ → г н о у h (no Sakha keyboard) | 94.9% | 0.2% |
| ө→е, ү→у, һ→ь (Leontiev 2014) | 95.4% | 0.0% |
| ҕ→5, ө→8, ү→y, һ→h (digits and Latin) | 98.0% | 0.4% |
| mixed: ө→о/8, ҕ→г/х/5, һ→ь/с/h, ҥ→н/нг | 96.7% | 0.3% |
| Sakha keyboard without ҕ and ҥ | 90.9% | 0.1% |
| clean text | — | 0.3% |
| **total** | **95.8%** | **0.2%** |

Correct words: 77.0% before, 98.9% after. Russian sentences (`eval/russian.txt`, 240 words):
0 changed. Mixed Sakha/Russian phrases (`eval/mixed.jsonl`, 25): 25 correct.
Speed ≈ 14k messages/s, load time < 1 s, memory ≈ 120 MB.

Reproduce: `python scripts/evaluate.py` (output in `eval/RESULTS_test.txt`).

### Limitations

- Words whose correct form is missing from the lexicon (rare forms, new words, names) are not
  restored, except for unambiguous cases («5» inside a word → «ҕ», «ь» after a vowel → «һ»).
- When both the chat spelling and the standard one are real words («сон»/«сөҥ», «уол»/«үөл»,
  «заказын»/«заказыҥ»), the word is kept as written. Sentence context is barely used.
- No correction of typos, dropped long vowels, punctuation or case. Fully Latin-script Sakha
  («kuruk») is not transliterated.
- The lexicon comes from newspapers, books and the web; dialects and slang are weakly covered.
- The test set is synthetic (known substitutions applied to clean sentences); quality on real
  chats may differ.

### License and sources

Code: MIT (`LICENSE`). Lexicons and test data: CC BY-SA 4.0 (`LICENSE-DATA.md`).
Sources: [ailabykt/sakha-corpus-mono](https://huggingface.co/datasets/ailabykt/sakha-corpus-mono)
and [ailabykt/sakha-russian-parallel](https://huggingface.co/datasets/ailabykt/sakha-russian-parallel)
(CC BY 4.0), Sakha Wikipedia (CC BY-SA 4.0). Letter substitutions follow Leontiev (2014) and
Everstova et al. (LREC 2026). See `SOURCES.md`.

Rebuild the lexicon: `python scripts/build_lexicon.py --root <corpus folder>` (needs `pyarrow`).
Evaluate: `python scripts/evaluate.py`. Tests: `python -m unittest discover -s tests`.
