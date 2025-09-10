Yalnızca **GEÇERLİ JSON** üret. Metin dışında hiçbir şey yazma.  
Uydurma yapma; emin değilsen ilgili alanı `null` veya `[]` bırak.  
Her iddia için metinden kısa bir **"span"** (1–2 cümle) ver; **span bulamazsan o adımı yazma**.

## ŞEMA
{
  "dava_turu": "string|null",
  "alt_dava_turleri": ["string"],
  "taraf_iliskisi": "string|null",

  "sonuc": "onama|bozma|kısmen_bozma|duzelterek_onama|ret|kabul|kısmen_kabul|diger|null",

  "kanun_atiflari": [
    {"kanun":"string|null","madde":"string|null","fikra":"string|null","span":"string|null"}
  ],

  "deliller": ["string"],
  "talepler": ["string"],
  "gecici_tedbirler": ["string"],
  "basvuru_yolu": "istinaf|temyiz|yok|null",

  "onemli_tarihler": [
    {"tip":"string","tarih":"YYYY-MM-DD|null","span":"string"}
  ],
  "miktarlar": [
    {"tutar":"string","para_birimi":"string|null","span":"string"}
  ],

  "adimlar": [
    {
      "ad": "ILK_DERECE|ISTINAF_BASVURU|ISTINAF_INCELEME|ISTINAF_KARAR|TEMYIZ_BASVURU|TEMYIZ_INCELEME|BOZMA|ONAMA|DUZELTEREK_ONAMA|KARAR_DUZELTME_BASVURU|KARAR_DUZELTME_REDDI|KARAR_DUZELTME_KABUL|NIHAI_KARAR|DIGER",
      "ozet": "string|null",
      "tarih": "YYYY-MM-DD|null",
      "mercii": "İlk Derece Mahkemesi|BAM|Yargıtay|davacı|davalı|null",
      "spans": ["string"]
    }
  ]
}

## KURALLAR
- **Kronoloji zorunlu.** Metindeki her önemli **işlem** ayrı bir adım olsun (başvuru, inceleme, karar).
- **Sebep–sonuç dili kullan:** Her `ozet` **tek cümle** olsun ve **“X olduğu için/üzerine Y oldu; ardından Z oldu”** kalıbını izlesin.  
  Ör.: “Davacı temyize başvurduğu **için** Yargıtay dosyayı inceledi.”  
  Ör.: “Karar düzeltme yolu **tamamlanmadığı için** Özel Daire kararları **bozdu**.”
- **Aynı satırda birden çok işlem varsa böl:** “başvuru + inceleme + karar” aynı cümledeyse 2–3 ayrı adım yaz.
- **Doğru aileyi seç:**  
  - Metinde “**Yargıtay / HGK**” varsa **TEMYİZ** ailesi (`TEMYIZ_BASVURU`, `TEMYIZ_INCELEME`, `BOZMA`/`ONAMA`/`DUZELTEREK_ONAMA`).  
  - “**BAM / Bölge Adliye**” varsa **İSTİNAF** ailesi (`ISTINAF_BASVURU`, `ISTINAF_INCELEME`, `ISTINAF_KARAR`).
- **Karar adımı** (BOZMA/ONAMA/DUZELTEREK_ONAMA/KARAR_DUZELTME_REDDI/KABUL/NIHAI_KARAR) **varsa**, aynı olaya ait **başvuru adımı** da bulunmalı ve kronolojide önce gelmeli.
- **Tarih** metinde açıksa `YYYY-MM-DD`, emin değilsen `null`.
- **Span zorunlu:** Her adım için metinden **en az bir** kısa alıntı `spans` içine koy (kanıt cümlesi). **Span bulamıyorsan o adımı yazma.**
- **Uydurma yapma.** Emin olmadığın alanları `null`/`[]` bırak.
- **Yalnızca JSON** döndür; açıklama/etiket/yorum yazma.
