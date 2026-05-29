# Çalıştırma Komutları

Bu dosya, projeyi **ilk kez kurup denemek** için gereken komutları içerir.  
Kavramsal açıklamalar için [REHBER.md](REHBER.md), teknik detaylar için [README.md](README.md) dosyasına bakın.

**Gereksinimler:** Python 3.10 veya üzeri, internet bağlantısı (yalnızca online mod için).

---

## 1. İlk kurulum (bir kez)

Proje klasöründe terminal açın:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`make` yüklüyse:

```bash
make install
```

---

## 2. En hızlı deneme (önerilen)

### A) Dashboard ile (tek komut, en kolay yol)

Dashboard hem online makale çeker hem analiz eder hem sonuçları gösterir:

```bash
source .venv/bin/activate
streamlit run dashboard.py
```

Tarayıcıda açılan panelde:
1. Araştırma sorusunu yazın
2. **Run analysis** (veya eşdeğer buton) ile çalıştırın
3. Sol menüden geçmiş sorgulara dönebilirsiniz

Make ile:

```bash
make dashboard
```

> `make dashboard` komutu `.venv` klasörünün oluşturulmuş olmasını bekler.

### B) Yerel demo corpus ile (internetsiz)

Repoda hazır 43 örnek doküman vardır (`examples/corpus/`):

```bash
source .venv/bin/activate
make run-demo
```

veya:

```bash
python triage.py \
  --corpus_dir examples/corpus \
  --query "2-edge-connected spanning subgraph approximation in subcubic graphs" \
  --topn 10 \
  --n_clusters 4 \
  --cache
```

Sonuçlar `results/` altına yazılır. Görmek için:

```bash
streamlit run dashboard.py
```

---

## 3. Modlara göre komutlar

### Yerel klasör modu

Kendi `.txt`, `.md` veya `.pdf` dosyalarınızla:

```bash
python triage.py \
  --corpus_dir /yol/corpus_klasoru \
  --query "your research question" \
  --topn 10 \
  --n_clusters 4 \
  --cache
```

### arXiv modu

Önce makaleleri indir, sonra analiz et:

```bash
python retrieve_arxiv.py \
  --query "graphic TSP approximation parity correction" \
  --max_results 50 \
  --out data/arxiv_corpus.jsonl

python triage.py \
  --jsonl data/arxiv_corpus.jsonl \
  --query "graphic TSP approximation parity correction" \
  --topn 10 \
  --n_clusters 4
```

### arXiv + OpenAlex modu

```bash
python retrieve_online.py \
  --query "federated learning differential privacy" \
  --sources arxiv,openalex \
  --max_results 50 \
  --out data/online_corpus.jsonl

python triage.py \
  --jsonl data/online_corpus.jsonl \
  --query "federated learning differential privacy" \
  --topn 10 \
  --n_clusters 4
```

Sadece arXiv:

```bash
python retrieve_online.py --query "your query" --sources arxiv --max_results 50
```

---

## 4. Make hedefleri

| Komut | Ne yapar? |
|-------|-----------|
| `make install` | `requirements.txt` bağımlılıklarını kurar |
| `make run-demo` | Yerel demo corpus üzerinde analiz çalıştırır |
| `make dashboard` | Streamlit panelini açar |
| `make retrieve-online` | arXiv + OpenAlex'ten örnek sorgu ile JSONL indirir |
| `make test` | Testleri çalıştırır (önce `pip install -e ".[dev]"` gerekir) |
| `make clean` | `results/`, cache ve bytecode dosyalarını temizler |

Farklı sorgu ile Make:

```bash
make run-demo QUERY="LP relaxations integrality gap network design"
make retrieve-online QUERY="quantum error correction surface codes"
```

---

## 5. `triage.py` parametreleri

| Parametre | Açıklama | Varsayılan |
|-----------|----------|------------|
| `--corpus_dir` | Yerel doküman klasörü | — |
| `--jsonl` | JSONL makale corpus yolu | — |
| `--query` | Araştırma sorusu (**zorunlu**) | — |
| `--topn` | Listelenecek üst N doküman | `10` |
| `--n_clusters` | Küme sayısı | `4` |
| `--top_keywords` | Küme başına anahtar kelime | `10` |
| `--summary_sentences` | Özet cümle sayısı | `3` |
| `--steps` | `rank,cluster,summarize,report` veya `all` | `all` |
| `--cache` | TF-IDF önbelleği kullan | kapalı |
| `--out_dir` | Çıktı klasörü | `results` |

> `--corpus_dir` ve `--jsonl` birlikte verilmez; tam olarak biri seçilir.

Kısmi pipeline örneği:

```bash
python triage.py \
  --corpus_dir examples/corpus \
  --query "approximation algorithms" \
  --steps rank,cluster
```

---

## 6. OpenAlex (isteğe bağlı)

OpenAlex API anahtarı **gerekmez**. İsteğe bağlı olarak e-posta vererek rate limit iyileştirilebilir:

```bash
export OPENALEX_MAILTO=you@example.com
```

Kalıcı kullanım için `.env.example` dosyasını `.env` olarak kopyalayıp e-postanızı yazabilirsiniz; ortam değişkenini terminal oturumunda export etmeniz yeterlidir.

---

## 7. Testler (geliştiriciler için)

```bash
pip install -e ".[dev]"
make test
```

---

## 8. Çıktı dosyaları

Analiz sonrası `results/` (veya `--out_dir`) altında:

| Dosya | İçerik |
|-------|--------|
| `ranking.csv` / `ranking.json` | Sıralı doküman listesi |
| `clusters.csv` | Küme atamaları |
| `cluster_keywords.json` | Küme anahtar kelimeleri |
| `summaries.json` | Soruya odaklı özetler |
| `report.md` | Okunabilir Markdown rapor |

Dashboard kullanıldığında her çalıştırma ayrıca `results/runs/<run_id>/` altına kaydedilir.

---

## 9. Sık karşılaşılan sorunlar

| Sorun | Çözüm |
|-------|--------|
| `command not found: streamlit` | `source .venv/bin/activate` ile sanal ortamı açın |
| `make dashboard` çalışmıyor | Önce `python -m venv .venv` ve `make install` yapın |
| Online mod yavaş / hata | İnternet bağlantısını kontrol edin; arXiv ~3 sn/istek bekler |
| Dashboard boş | Önce `triage.py` veya dashboard üzerinden analiz çalıştırın |
| `pytest` bulunamadı | `pip install -e ".[dev]"` çalıştırın |

---

## 10. Tek sayfalık özet

```bash
# Kurulum
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# En kolay deneme
streamlit run dashboard.py

# Yerel demo (internetsiz)
make run-demo

# Temizlik
make clean
```
