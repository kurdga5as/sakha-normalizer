/* Нормализатор в фоновом потоке: словарь грузится и разбирается, не подвешивая страницу. */
importScripts('normalizer.js');

async function loadTsv(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url + ': ' + r.status);
  const buf = new Uint8Array(await r.arrayBuffer());
  // Сервер мог уже распаковать gzip (Content-Encoding): проверяем сигнатуру 1f 8b.
  if (buf[0] === 0x1f && buf[1] === 0x8b) {
    const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'));
    return await new Response(stream).text();
  }
  return new TextDecoder().decode(buf);
}

const ready = (async () => {
  const [sah, ru] = await Promise.all([loadTsv('data/sah_lexicon.tsv.gz'), loadTsv('data/ru_lexicon.tsv.gz')]);
  return new self.SakhaNormalizer.Normalizer(sah, ru);
})();

ready.then(() => postMessage({ type: 'ready' }), e => postMessage({ type: 'error', error: String(e) }));

onmessage = async ({ data }) => {
  try {
    const n = await ready;
    postMessage({ type: 'result', id: data.id, ...n.explain(data.text) });
  } catch (e) {
    postMessage({ type: 'error', id: data.id, error: String(e) });
  }
};
