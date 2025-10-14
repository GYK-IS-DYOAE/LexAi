# src/services/query_service.py
from src.user_input.text_cleaner import clean_text
from src.rag.query_llm import query_llm
from src.retrieval.retrieve_combined import hybrid_search
from src.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt

def process_user_query(raw_query: str):
    cleaned_query = clean_text(raw_query)
    try:
        hits = hybrid_search(cleaned_query)
        passages = [{"doc_id": h.doc_id, "text": h.text_repr} for h in hits]
        user_prompt = build_user_prompt(cleaned_query, passages)
    except Exception:
        user_prompt = f"SORU:\n{cleaned_query}\n\nBu hukuki soruya açıklama yap."
    
    answer = query_llm(SYSTEM_PROMPT, user_prompt)
    return cleaned_query, answer