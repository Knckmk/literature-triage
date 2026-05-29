# AI-Assisted Literature Triage Tool - Değişiklik Özeti

Bu doküman, projeyi capstone seviyesinde daha profesyonel, tekrar kullanılabilir
ve sunulabilir hale getirmek için yapılan değişiklikleri açıklar. Amaç, Ahmet'in
hem "ne değişti" hem de "neden değişti" sorularına hızlı cevap bulabilmesidir.

## 1. Proje Temizliği ve Kurulum Yapısı

### Ne değişti?

- `.gitignore` eklendi.
- `__pycache__`, `.DS_Store`, `results/`, `tmp_results/` gibi üretilmiş dosyalar
  repodan uzak tutulacak hale getirildi.
- `pyproject.toml` eklendi.
- `requirements.txt` proje bağımlılıklarıyla hizalandı.
- `Makefile` eklendi:
  - `make install`
  - `make run-demo`
  - `make dashboard`
  - `make test`
  - `make clean`
- `README.md` kurulum, demo ve çıktı beklentileri açısından güncellendi.

### Neden yapıldı?

Bu değişiklikler projenin başka bir makinede daha kolay kurulmasını sağlar.
Üretilmiş sonuçların veya cache dosyalarının repoya karışmasını engeller.
`pyproject.toml` ise projeyi modern Python paketleme standardına yaklaştırır.

## 2. Yeni Veri Modeli ve Scholarly Metadata

### Ne değişti?

- `models.py` eklendi.
- Üç temel dataclass tanımlandı:
  - `Document`
  - `PaperMetadata`
  - `TriageResult`
- Local `.txt`, `.md`, `.pdf` dosyaları artık `Document` ve `PaperMetadata`
  yapısına dönüştürülüyor.
- Eski `Doc` kullanımı kırılmasın diye geriye uyumluluk korundu.
- `docs_to_text()` davranışı korundu.
- Ranking çıktıları eski alanların yanında metadata alanlarını da içeriyor:
  - `source`
  - `url`
  - `pdf_url`
  - `authors`
  - `year`
  - `citation_count`

### Neden yapıldı?

İlk sürüm sadece yerel metin dosyalarını temsil ediyordu. Capstone seviyesinde
literatür taraması için makale başlığı, yazarlar, yıl, arXiv linki, PDF linki,
kategori ve citation gibi alanlara ihtiyaç var. Bu model, ileride Semantic
Scholar gibi kaynakların da eklenmesini kolaylaştırır.

## 3. arXiv Online Retrieval

### Ne değişti?

- `retrievers/` klasörü oluşturuldu.
- `retrievers/arxiv_retriever.py` eklendi.
- `retrieve_arxiv.py` CLI eklendi.
- arXiv Atom API'den ücretsiz ve API key gerektirmeyen makale çekme desteği
  eklendi.
- `storage/jsonl_store.py` eklendi.
- JSONL okuma/yazma fonksiyonları eklendi:
  - `write_jsonl(path, records)`
  - `read_jsonl(path)`
- arXiv parser için canlı internet gerektirmeyen fixture tabanlı test eklendi.

### Neden yapıldı?

Proje artık yalnızca hazır yerel corpus ile sınırlı değil. Kullanıcı arXiv'den
gerçek scholarly metadata çekip aynı triage pipeline'ına verebilir. JSONL formatı
seçildi çünkü satır satır okunabilir, basittir ve büyük veri akışları için
uygundur.

## 4. Local Corpus ve JSONL Corpus Modları

### Ne değişti?

`triage.py` artık iki giriş modunu destekliyor:

```bash
python triage.py --corpus_dir examples/corpus --query "..."
python triage.py --jsonl data/arxiv_corpus.jsonl --query "..."
```

- `--corpus_dir` ve `--jsonl` seçeneklerinden tam olarak biri verilmek zorunda.
- JSONL paper kayıtları aynı internal `Document` modeline dönüştürülüyor.
- JSONL için ranking metni `title + abstract` olarak kullanılıyor.
- Dashboard metadata alanlarını göstermeye başladı.
- JSONL triage workflow'u için entegrasyon testi eklendi.

### Neden yapıldı?

Pipeline'ın local dosyalarla ve online retrieval çıktılarıyla aynı şekilde
çalışması gerekir. Bu, kod tekrarını azaltır ve ileride başka retrieval
kaynakları eklemeyi kolaylaştırır.

## 5. Explainability Katmanı

### Ne değişti?

- `explain.py` eklendi.
- Şu deterministic fonksiyonlar eklendi:
  - `extract_query_terms(query)`
  - `matched_terms(query, text)`
  - `top_weighted_terms_for_doc(vec, X, doc_index)`
  - `best_matching_sentences(text, query)`
- Ranking çıktılarına şu alanlar eklendi:
  - `matched_query_terms`
  - `top_doc_terms`
  - `best_snippets`
- `summaries.json` artık açıklanabilirlik alanları içeriyor.
- `report.md` önerilen dokümanlarda "neden alakalı?" bilgisini gösteriyor.
- Dashboard doküman detayında "Why this paper?" bölümü eklendi.

### Neden yapıldı?

Sadece cosine score göstermek kullanıcıya yeterli açıklama vermez. Capstone
sunumunda sistemin neden bir makaleyi önerdiğini göstermek önemlidir. Bu katman
LLM kullanmadan, deterministic ve test edilebilir şekilde açıklama üretir.

## 6. Sunulabilir Cluster Etiketleri

### Ne değişti?

- `cluster_labels.py` eklendi.
- Cluster keyword'lerinden deterministic label üreten kurallar yazıldı.
- Approximation algorithms alanına özel küçük vocabulary map eklendi:
  - LP & Rounding
  - TSP & Parity Correction
  - Connectivity / 2ECSS
  - Ear Decompositions
  - Network Design
- `cluster_summaries.json` çıktısı eklendi.
- Her cluster için şu bilgiler üretiliyor:
  - `cluster_id`
  - `label`
  - `keywords`
  - `number_of_docs`
  - `representative_docs`
- Dashboard ve report numeric cluster id yerine label göstermeye başladı.

### Neden yapıldı?

Sadece keyword listesi demo için zayıf görünür. "Cluster 1 - Connectivity /
2ECSS" gibi etiketler jüriye ve kullanıcıya daha anlaşılır bir anlatım verir.
Bu çözüm LLM kullanmadığı için deterministik ve açıklanabilirdir.

## 7. Dashboard'un Capstone Demo Arayüzüne Dönüşmesi

### Ne değişti?

- `dashboard.py` iki sekmeli hale getirildi:
  - `Load existing results`
  - `Run new analysis`
- Eski diskten sonuç okuma modu korundu.
- Yeni analiz sekmesinde kullanıcı şunları seçebiliyor:
  - Local corpus veya arXiv JSONL
  - input path
  - query
  - `topn`
  - `n_clusters`
  - `summary_sentences`
  - `out_dir`
- Dashboard artık shell komutu çalıştırmıyor; pipeline fonksiyonunu doğrudan
  çağırıyor.
- Progress/status mesajları eklendi:
  - loading corpus
  - vectorizing
  - ranking
  - clustering
  - summarizing
  - done
- Download butonları eklendi:
  - `ranking.csv`
  - `report.md`
  - `summaries.json`
- Paper card görünümü eklendi:
  - title
  - score
  - source/year/authors
  - cluster label
  - matched terms
  - URL/PDF linkleri
- Temel hata yakalama eklendi:
  - boş query
  - eksik corpus path
  - eksik JSONL
  - boş corpus

### Neden yapıldı?

Dashboard artık sadece sonuç görüntüleyen pasif bir ekran değil. Demo sırasında
kullanıcı query ve input seçip analizi başlatabilir. Bu, projeyi capstone sunumu
için daha etkileyici ve kullanılabilir hale getirir.

## 8. Pipeline Refactor ve Artifact Sözleşmesi

### Ne değişti?

- Core pipeline mantığı `pipeline.py` içine taşındı.
- `TriageConfig` dataclass'ı pipeline input ayarlarını temsil ediyor.
- `PipelineArtifacts` dataclass'ı pipeline sonucunu ve üretilen dosya yollarını
  temsil ediyor.
- `run_pipeline(config: TriageConfig) -> PipelineArtifacts` fonksiyonu eklendi.
- `triage.py` artık yalnızca:
  - CLI argümanlarını parse ediyor
  - `TriageConfig` oluşturuyor
  - `run_pipeline()` çağırıyor
  - kısa özet yazdırıyor
- `PipelineArtifacts` şu dosya yollarını içeriyor:
  - `ranking_csv`
  - `ranking_json`
  - `clusters_csv`
  - `cluster_keywords_json`
  - `cluster_summaries_json`
  - `summaries_json`
  - `report_md`
- `PipelineResult` adı geriye uyumluluk için `PipelineArtifacts` alias'ı olarak
  bırakıldı.
- `tests/test_pipeline.py` eklendi:
  - temporary local corpus ile `run_pipeline()` testi
  - temporary JSONL corpus ile `run_pipeline()` testi
  - artifact path'lerinin gerçekten oluştuğunu doğrulama

### Neden yapıldı?

CLI odaklı kod başka yerlerden çağırmak için uygun değildir. Pipeline fonksiyonu
ayrı olunca hem CLI hem dashboard aynı core logic'i kullanır. Bu, davranış
tutarlılığı sağlar ve test yazmayı kolaylaştırır. Artifact path'lerinin dönüş
tipinde yer alması dashboard, test ve ileride eklenecek otomasyonların dosya
konumlarını tahmin etmeden kullanmasını sağlar.

## Korunan Davranışlar

Aşağıdaki eski kullanım halen çalışır:

```bash
python triage.py --corpus_dir examples/corpus --query "graphic TSP approximation parity correction" --topn 10 --n_clusters 4
```

Local corpus modu, ranking logic, clustering logic, summarization logic ve
report üretimi korunmuştur. Yeni özellikler mevcut davranışı değiştirmek yerine
aynı pipeline'ın üstüne eklenmiştir.

## Üretilen Ana Çıktılar

Pipeline varsayılan olarak şu dosyaları üretir:

- `ranking.csv`
- `ranking.json`
- `clusters.csv`
- `cluster_keywords.json`
- `cluster_summaries.json`
- `summaries.json`
- `report.md`

Bu çıktılar hem CLI hem dashboard tarafından aynı şekilde kullanılır.

## Test Durumu

Son doğrulamada test paketi şu şekilde geçti:

```text
10 passed
```

Kapsanan başlıklar:

- local ingestion metadata
- JSONL read/write
- arXiv XML parser
- JSONL triage integration
- explainability helpers
- deterministic cluster label generation
- `run_pipeline()` local corpus artifacts
- `run_pipeline()` JSONL corpus artifacts

## Mimari Sonuç

Projenin akışı artık şu şekilde düşünülebilir:

```text
Input source
  -> ingest/load JSONL
  -> Document + PaperMetadata
  -> TF-IDF vectorization
  -> ranking
  -> explainability
  -> clustering + labels
  -> summaries
  -> report + dashboard outputs
```

Bu yapı, ileride Semantic Scholar retrieval, citation-based ranking, advanced
filters veya daha güçlü dashboard görselleştirmeleri eklemek için sağlam bir
temel oluşturur.
