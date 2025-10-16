#!/usr/bin/env python3
"""
Simple Similar Case Test - Direct Qdrant Search
"""

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import json

def test_similar_search():
    print("Testing Similar Case Search")
    print("=" * 50)
    
    try:
        # Qdrant client
        client = QdrantClient(host="localhost", port=6333, timeout=60.0)
        
        # Test query
        query_text = "nafaka"
        print(f"Query: {query_text}")
        
        # Check available collections first
        print("Checking available collections...")
        collections = client.get_collections()
        print(f"Available collections: {[c.name for c in collections.collections]}")
        
        # Try different models based on collection vector size
        models_to_try = [
            ("all-MiniLM-L6-v2", 384),      # 384 boyutlu model
            ("BAAI/bge-m3", 1024),           # 1024 boyutlu model (büyük)
            ("sentence-transformers/all-MiniLM-L12-v2", 384)  # Alternatif 384 boyutlu
        ]
        
        model = None
        query_vector = None
        
        for model_name, expected_dim in models_to_try:
            try:
                print(f"Trying model: {model_name} (expected dim: {expected_dim})")
                model = SentenceTransformer(model_name, device="cpu")
                
                # Generate query vector
                print("Generating query vector...")
                query_vector = model.encode(query_text, normalize_embeddings=True).tolist()
                print(f"Generated vector dimension: {len(query_vector)}")
                
                # Test with legal_cases collection first
                print("Testing with legal_cases collection...")
                results = client.search(
                    collection_name="legal_cases",
                    query_vector=query_vector,
                    limit=5,
                    with_payload=True
                )
                print(f"✅ Success with {model_name} and legal_cases collection!")
                break
                
            except Exception as e:
                print(f"❌ Failed with {model_name}: {str(e)}")
                if "lexai_cases" in str(e):
                    # Try lexai_cases collection as fallback
                    try:
                        print("Trying lexai_cases collection...")
                        results = client.search(
                            collection_name="lexai_cases",
                            query_vector=query_vector,
                            limit=5,
                            with_payload=True
                        )
                        print(f"✅ Success with {model_name} and lexai_cases collection!")
                        break
                    except Exception as e2:
                        print(f"❌ Also failed with lexai_cases: {str(e2)}")
                continue
        
        if query_vector is None:
            print("❌ No working model found!")
            return
        
        points = results
        print(f"\nFound {len(points)} results")
        
        for i, point in enumerate(points, 1):
            payload = point.payload or {}
            print(f"\n{i}. Point ID: {point.id}")
            print(f"   Score: {point.score:.4f}")
            print(f"   Dava Turu: {payload.get('dava_turu', 'N/A')}")
            print(f"   Sonuc: {payload.get('sonuc', 'N/A')}")
            if payload.get('gerekce'):
                print(f"   Gerekce: {str(payload.get('gerekce'))[:100]}...")
            
        print(f"\n✅ Search successful with model: {model_name if model else 'Unknown'}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_similar_search()

