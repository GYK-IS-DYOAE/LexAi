#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
utils_preprocess.py
-------------------
Kullanıcıdan veya dış kaynaklardan gelen metinleri temizleme, normalize etme
ve güvenlik filtresinden geçirme yardımcı fonksiyonları.

Kullanım alanları:
- API (/ask, /feedback)
- ETL ve training pipeline'ları
- Arama öncesi sorgu hazırlığı (OpenSearch + Qdrant)
"""

import re
import html

# ---------------------------------------------------------------------
# 1. Temel metin temizleme
# ---------------------------------------------------------------------

def clean_user_text(text: str) -> str:
    """
    Temel metin temizliği:
    - HTML çözme
    - Emoji ve kontrolsüz karakterleri kaldırma
    - Fazla boşlukları sadeleştirme
    - Gereksiz noktalama tekrarlarını düzeltme
    """
    if not text:
        return ""

    # HTML encode çöz
    text = html.unescape(text)

    # Unicode kontrolsüz karakterler / emoji kaldır
    text = re.sub(r"[^\w\s.,;:!?@%&/()ğüşöçİĞÜŞÖÇ-]", "", text)

    # Fazla boşlukları sadeleştir
    text = re.sub(r"\s+", " ", text).strip()

    # Gereksiz noktalama tekrarlarını azalt
    text = re.sub(r"([.!?])\1+", r"\1", text)

    # Uzunluğu sınırlamak (ör. 512 karakter)
    text = text[:512]

    return text


# ---------------------------------------------------------------------
# 2. Hukuki terim normalizasyonu
# ---------------------------------------------------------------------

def normalize_legal_terms(text: str) -> str:
    """
    Hukuk terimlerini normalize eder:
    Kısaltmaları tam forma çevirir (ör. HMK -> Hukuk Muhakemeleri Kanunu)
    """
    replacements = {
        r"\bHMK\b": "Hukuk Muhakemeleri Kanunu",
        r"\bTCK\b": "Türk Ceza Kanunu",
        r"\bTBK\b": "Türk Borçlar Kanunu",
        r"\bİŞK\b": "İş Kanunu",
        r"\b5510\b": "5510 sayılı Sosyal Sigortalar ve Genel Sağlık Sigortası Kanunu",
        r"\b1475\b": "1475 sayılı İş Kanunu",
        r"\b4857\b": "4857 sayılı İş Kanunu",
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


# ---------------------------------------------------------------------
# 3. Güvenlik ve sanitization
# ---------------------------------------------------------------------

def sanitize_input(text: str) -> str:
    """
    Güvenlik amaçlı temel sanitization:
    - Komut enjeksiyonu, kod, URL veya SQL ifadelerini engeller
    """
    blacklist = [
        "DELETE FROM", "DROP TABLE", "INSERT INTO", "os.system",
        "import ", "exec(", "eval(", "```", "curl ", "wget ", "rm -rf",
        "<script>", "</script>", "SELECT * FROM", "--", "sleep("
    ]

    for bad in blacklist:
        if bad.lower() in text.lower():
            raise ValueError(f"⚠️ Uygunsuz veya potansiyel olarak tehlikeli ifade tespit edildi: {bad}")

    return text


# ---------------------------------------------------------------------
# 4. Bütünleşik temizleme pipeline'ı
# ---------------------------------------------------------------------

def preprocess_user_query(raw_query: str) -> str:
    """
    Kullanıcıdan gelen sorguyu uçtan uca temizler:
    clean → normalize → sanitize
    """
    text = clean_user_text(raw_query)
    text = normalize_legal_terms(text)
    text = sanitize_input(text)
    return text
