from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class SimilarRequest(BaseModel):
    query: str                     # hybrid_search -> 'query'
    topn: int = 5                  # hybrid_search -> 'topn'
    include_summaries: bool = True 

class CaseItem(BaseModel):
    doc_id: str                    
    dava_turu: Optional[str] = None
    sonuc: Optional[str] = None
    gerekce: Optional[str] = None
    karar: Optional[str] = None
    hikaye: Optional[str] = None
    similarity_score: float        
    source: str                    


class LawItem(BaseModel):
    law_name: str
    article_no: str
    relevance_score: float


class SimilarResponse(BaseModel):
    query: str
    similar_cases: List[CaseItem]
    related_laws: List[LawItem]
    total_cases_found: int
    timestamp: datetime
