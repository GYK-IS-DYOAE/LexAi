# DYEOA – Dava Yönlendirme ve Emsal Öneri Asistanı

Bu depo, **metinden A→E çıktıları** (Yol Haritası, Olası Sonuçlar, İlgili Maddeler,
Delil Listesi, Emsal Kartları) üreten **LLM destekli ETL** ve ileride eklenecek
**GNN tabanlı emsal motoru** için iskelet içerir.

**Akış (ETL)**: raw → 00_clean → 01_segment → 02_extract_llm → 03_validate_normalize → 04_link_laws → 05_export_processed (cases.jsonl)


dyeoa/
├─ collectors/                          # veri çekme (senin scraper)
│  └─ yargitay_scraper/
│
├─ data/
│  ├─ raw/                              # ham PDF/HTML/JSON
│  ├─ interim/                          # 00–05 ara çıktılar (txt/json)
│  └─ processed/
│     └─ cases.jsonl                    # A→E için ana kaynak
│
├─ configs/
│  ├─ regex_patterns.yml                # başlık/mahkeme/esas/PII/tarih/para regex
│  ├─ keywords.yml                      # dava_türü / hak_ihlali / taraf ilişkisi sözlüğü
│  ├─ law_catalog.csv                   # kanun + madde + yürürlük + kısa açıklama-ID
│  ├─ rules/
│  │  ├─ court_jurisdiction.yml         # yetkili mahkeme kuralları
│  │  ├─ interim_measures.yml           # geçici talep kuralları (örn. tedbir nafakası)
│  │  └─ evidence_matrix.yml            # dava_türü×sonuç → delil listeleri + etki tabanı
│  ├─ templates/
│  │  ├─ action_plan.md                 # A) Yol Haritası
│  │  ├─ outcomes.md                    # B) Olası Sonuçlar
│  │  ├─ laws.md                        # C) İlgili Maddeler
│  │  ├─ evidence.md                    # D) Delil Listesi
│  │  └─ disclaimer.md                  # uyarı bandı
│  └─ thresholds.yml                    # skor/eşikler, yıl pencereleri vb.
│
├─ src/
│  ├─ etl/
│  │  ├─ 00_clean.py                    # ön-temizlik
│  │  ├─ 01_segment.py                  # blok ayırma
│  │  ├─ 02_extract_llm.py              # LLM ile yapısal çıkarım (JSON)
│  │  ├─ 03_validate_normalize.py       # şema kontrol + normalizasyon
│  │  ├─ 04_link_laws.py                # katalog eşleme + yürürlük
│  │  └─ 05_export_processed.py         # cases.jsonl yazımı
│  │
│  ├─ llm/
│  │  ├─ client.md                      # hangi LLM, sıcaklık, retry politikası (metinsel)
│  │  └─ prompts/
│  │     └─ extract_system.md           # “yalnız JSON, uydurma yok” yönergesi (metin)
│  │
│  ├─ retrieval/
│  │  ├─ contract.md                    # bu mesajdaki sözleşmenin düz metni
│  │  ├─ baseline.md                    # baseline mantığı (TF-IDF + Jaccard) – açıklama
│  │  └─ stats.md                       # istatistik hesaplama notları – açıklama
│  │
│  ├─ planner/
│  │  ├─ assemble.md                    # A→E şablonlarının nasıl birleştiği (metin)
│  │  └─ explain.md                     # “neden bu emsal?” mantığı – açıklama
│  │
│  ├─ validators/
│  │  ├─ schema.md                      # case_processed alan tanımları (metin)
│  │  └─ normalizers.md                 # adlandırma/haritalama kuralları (metin)
│  │
│  ├─ graph/                            # (GNN zamanı gelince)
│  │  ├─ build_graph.md                 # nodes/edges prensipleri (metin)
│  │  └─ temporal_masks.md              # yürürlük/zaman maskeleri (metin)
│  │
│  ├─ models/                           # (GNN eğitimi geldiğinde)
│  │  ├─ train_gnn.md
│  │  ├─ evaluate.md
│  │  └─ inference.md
│  │
│  └─ api/
│     └─ app.md                         # /analyze akışı nasıl cevap üretir (metin)
│
├─ tests/
│  ├─ test_etl_smoke.md                 # duman testi planı (metin)
│  ├─ test_schema.md                    # şema doğrulama planı
│  └─ test_retrieval.md                 # retrieval kalite ölçümü planı
│
├─ docs/
│  ├─ data_flow.md                      # uçtan uca veri akışı – diyagram/açıklama
│  └─ mapping_rules.md                  # metin→alan eşleme kuralları
│
└─ README.md
