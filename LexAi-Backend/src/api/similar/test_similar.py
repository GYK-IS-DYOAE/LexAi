#!/usr/bin/env python3
"""
Similar Case API Test Script
Qdrant verilerini kullanarak similar case özelliğini test eder
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path.parent))

from src.models.similar.similar_service import find_similar_and_laws
from src.models.similar.similar_schemas import SimilarRequest

def test_similar_cases():
    print(" Similar Case API Test")
    print("=" * 50)
    
    # Test query
    query = "nafaka davası"
    
    request = SimilarRequest(
        query=query,
        topn=5,
        include_summaries=True
    )
    
    try:
        print(f" Query: {query}")
        print(" Searching for similar cases...")
        
        response = find_similar_and_laws(request)
        
        print(f"\n Found {response.total_cases_found} similar cases")
        print(f" Timestamp: {response.timestamp}")
        
        print("\n Similar Cases:")
        for i, case in enumerate(response.similar_cases, 1):
            print(f"\n{i}. Case ID: {case.doc_id}")
            print(f"   Dava Türü: {case.dava_turu}")
            print(f"   Sonuç: {case.sonuc}")
            print(f"   Similarity Score: {case.similarity_score}")
            print(f"   Source: {case.source}")
            if case.gerekce:
                print(f"   Gerekçe: {case.gerekce[:100]}...")
        
        print("\nRelated Laws:")
        for law in response.related_laws:
            print(f"   - {law.law_name} (Article: {law.article_no})")
            
    except Exception as e:
        print(f" Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_similar_cases()




