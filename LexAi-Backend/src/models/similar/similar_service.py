from datetime import datetime
from typing import List, Any
from src.retrieval.retrieve_combined import hybrid_search
from src.models.similar.similar_schemas import (
    SimilarRequest,
    SimilarResponse,
    CaseItem,
    LawItem,
)


def _as_text(value: Any) -> str:
    """Liste veya None gelen alanları güvenli şekilde stringe çevirir."""
    if value is None:
        return None
    if isinstance(value, list):
        return " ".join([str(v) for v in value if isinstance(v, str)])
    return str(value)


def find_similar_and_laws(request: SimilarRequest) -> SimilarResponse:
    hits = hybrid_search(query=request.query, topn=request.topn)

    similar_cases: List[CaseItem] = []
    for h in hits:
        p = h.payload or {}
        case = CaseItem(
            doc_id=h.doc_id,
            dava_turu=_as_text(p.get("dava_turu")),
            sonuc=_as_text(p.get("sonuc")),
            gerekce=_as_text(p.get("gerekce")) if request.include_summaries else None,
            karar=_as_text(p.get("karar")) if request.include_summaries else None,
            karar_metni=_as_text(
                p.get("karar_metni_meta") or p.get("karar_metni") or p.get("karar_preview")
            ),  # 🔹 tam karar metnini ekliyoruz
            hikaye=_as_text(p.get("hikaye")) if request.include_summaries else None,
            similarity_score=round(float(h.score_norm), 4),
            source=h.source,
        )
        similar_cases.append(case)

    # basit kanun tespiti (ileride BM25+graph ile genişletilebilir)
    related_laws: List[LawItem] = []
    law_terms = ("İş Kanunu", "HMK", "TBK", "TMK", "Borçlar Kanunu")
    for c in similar_cases:
        text_fields = [c.karar_metni, c.karar, c.gerekce, c.hikaye]
        text = " ".join([t for t in text_fields if t])
        for term in law_terms:
            if term.lower() in text.lower():
                related_laws.append(
                    LawItem(law_name=term, article_no="-", relevance_score=1.0)
                )

    return SimilarResponse(
        query=request.query,
        similar_cases=similar_cases,
        related_laws=related_laws,
        total_cases_found=len(similar_cases),
        timestamp=datetime.utcnow(),
    )
