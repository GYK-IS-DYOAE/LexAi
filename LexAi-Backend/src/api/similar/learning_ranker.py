"""
Learning Ranker for Similar Cases
=================================
Bu modül, Qdrant'tan gelen embedding sonuçlarını özellik olarak kullanarak
öğrenen bir model ile yeniden puanlama yapar.

Özellikler:
- Embedding benzerlik skorları
- Dava türü ağırlıklandırması
- Kullanıcı geçmişi (gelecekte)
- Belge türü özellikleri
- Özelleştirilmiş skorlar
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import os
from datetime import datetime

from src.models.similar.similar_schemas import CaseItem, SimilarResponse
from src.retrieval.retrieve_combined import Hit


@dataclass
class RankingFeatures:
    """Sıralama için özellik vektörü"""
    embedding_score: float          # Qdrant'tan gelen semantic similarity
    bm25_score: float               # OpenSearch'ten gelen BM25 skoru
    fused_score: float              # Mevcut hibrit skor
    dava_turu_weight: float        # Dava türü ağırlığı
    doc_length: int                # Belge uzunluğu
    source_type: int                # Kaynak türü (0: OS, 1: Qdrant, 2: Both)
    has_gerekce: int               # Gerekçe var mı (0/1)
    has_karar: int                 # Karar var mı (0/1)
    has_hikaye: int                # Hikaye var mı (0/1)
    text_quality_score: float      # Metin kalite skoru


class LearningRanker:
    """Öğrenen sıralama modeli"""
    
    def __init__(self, model_type: str = "random_forest"):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = [
            'embedding_score', 'bm25_score', 'fused_score', 
            'dava_turu_weight', 'doc_length', 'source_type',
            'has_gerekce', 'has_karar', 'has_hikaye', 'text_quality_score'
        ]
        self.model_path = "models/learning_ranker.pkl"
        self.scaler_path = "models/scaler.pkl"
        
        # Dava türü ağırlıkları (domain knowledge)
        self.dava_turu_weights = {
            'İş Hukuku': 1.0,
            'Ticaret Hukuku': 0.9,
            'Borçlar Hukuku': 0.8,
            'Aile Hukuku': 0.9,
            'Ceza Hukuku': 0.7,
            'İdare Hukuku': 0.6,
            'Anayasa Hukuku': 0.5,
            'default': 0.5
        }
        
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Modeli yükle veya yeni oluştur"""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                print("Learning ranker model loaded successfully")
            except Exception as e:
                print(f"Model loading failed: {e}, creating new model")
                self._create_new_model()
        else:
            self._create_new_model()
    
    def _create_new_model(self):
        """Yeni model oluştur"""
        if self.model_type == "random_forest":
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == "logistic":
            self.model = LogisticRegression(
                random_state=42,
                max_iter=1000
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        print("New learning ranker model created")
    
    def extract_features(self, hit: Hit, query: str) -> RankingFeatures:
        """Hit'ten özellik vektörü çıkar"""
        payload = hit.payload or {}
        
        # Embedding ve BM25 skorları
        embedding_score = hit.score_norm if hit.source in ["qdrant", "both"] else 0.0
        bm25_score = hit.score_norm if hit.source in ["opensearch", "both"] else 0.0
        fused_score = hit.score_norm
        
        # Dava türü ağırlığı
        dava_turu = payload.get("dava_turu", "")
        dava_turu_weight = self.dava_turu_weights.get(dava_turu, self.dava_turu_weights["default"])
        
        # Belge uzunluğu
        text_repr = hit.text_repr or ""
        doc_length = len(text_repr)
        
        # Kaynak türü
        source_type = 0 if hit.source == "opensearch" else 1 if hit.source == "qdrant" else 2
        
        # İçerik varlığı
        has_gerekce = 1 if payload.get("gerekce") else 0
        has_karar = 1 if payload.get("karar") else 0
        has_hikaye = 1 if payload.get("hikaye") else 0
        
        # Metin kalite skoru (basit heuristik)
        text_quality_score = self._calculate_text_quality(payload)
        
        return RankingFeatures(
            embedding_score=embedding_score,
            bm25_score=bm25_score,
            fused_score=fused_score,
            dava_turu_weight=dava_turu_weight,
            doc_length=doc_length,
            source_type=source_type,
            has_gerekce=has_gerekce,
            has_karar=has_karar,
            has_hikaye=has_hikaye,
            text_quality_score=text_quality_score
        )
    
    def _calculate_text_quality(self, payload: Dict[str, Any]) -> float:
        """Metin kalite skoru hesapla"""
        score = 0.0
        
        # Gerekçe varsa +0.3
        if payload.get("gerekce"):
            score += 0.3
        
        # Karar varsa +0.3
        if payload.get("karar"):
            score += 0.3
        
        # Hikaye varsa +0.2
        if payload.get("hikaye"):
            score += 0.2
        
        # Sonuç varsa +0.2
        if payload.get("sonuc"):
            score += 0.2
        
        return min(score, 1.0)
    
    def features_to_array(self, features: RankingFeatures) -> np.ndarray:
        """Özellikleri numpy array'e çevir"""
        return np.array([
            features.embedding_score,
            features.bm25_score,
            features.fused_score,
            features.dava_turu_weight,
            features.doc_length,
            features.source_type,
            features.has_gerekce,
            features.has_karar,
            features.has_hikaye,
            features.text_quality_score
        ]).reshape(1, -1)
    
    def rank_cases(self, hits: List[Hit], query: str) -> List[Tuple[Hit, float]]:
        """Davaları öğrenen model ile yeniden sırala"""
        if not hits:
            return []
        
        # Özellikleri çıkar
        features_list = []
        for hit in hits:
            features = self.extract_features(hit, query)
            features_list.append(features)
        
        # Özellikleri array'e çevir
        X = np.array([self.features_to_array(f).flatten() for f in features_list])
        
        # Normalize et
        X_scaled = self.scaler.transform(X)
        
        # Model ile tahmin et
        try:
            predicted_scores = self.model.predict(X_scaled)
        except Exception as e:
            print(f"Prediction failed: {e}, using original scores")
            predicted_scores = [hit.score_norm for hit in hits]
        
        # Hit'lerle skorları eşleştir
        ranked_cases = list(zip(hits, predicted_scores))
        
        # Skora göre sırala
        ranked_cases.sort(key=lambda x: x[1], reverse=True)
        
        return ranked_cases
    
    def train_model(self, training_data: List[Dict[str, Any]]):
        """Modeli eğit (gelecekte kullanıcı feedback'i ile)"""
        if not training_data:
            print("No training data provided")
            return
        
        # Training data'yı işle
        X = []
        y = []
        
        for data in training_data:
            features = data['features']
            relevance_score = data['relevance_score']  # 0-1 arası
            
            X.append(features)
            y.append(relevance_score)
        
        X = np.array(X)
        y = np.array(y)
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Normalize et
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Modeli eğit
        self.model.fit(X_train_scaled, y_train)
        
        # Test skoru
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        print(f"Training completed - Train Score: {train_score:.3f}, Test Score: {test_score:.3f}")
        
        # Modeli kaydet
        os.makedirs("models", exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        
        print("Model saved successfully")
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Özellik önemini döndür"""
        if not hasattr(self.model, 'feature_importances_'):
            return {}
        
        importance_dict = {}
        for i, importance in enumerate(self.model.feature_importances_):
            importance_dict[self.feature_names[i]] = importance
        
        return importance_dict


def enhance_similar_cases_with_learning_ranker(
    hits: List[Hit], 
    query: str,
    ranker: LearningRanker = None
) -> List[Hit]:
    """Similar case sonuçlarını öğrenen model ile geliştir"""
    
    if ranker is None:
        ranker = LearningRanker()
    
    # Öğrenen model ile yeniden sırala
    ranked_cases = ranker.rank_cases(hits, query)
    
    # Hit'leri yeni skorlarla güncelle
    enhanced_hits = []
    for hit, new_score in ranked_cases:
        # Yeni skorla hit'i güncelle
        enhanced_hit = Hit(
            doc_id=hit.doc_id,
            score_raw=hit.score_raw,
            score_norm=new_score,  # Yeni öğrenen skor
            source=hit.source,
            payload=hit.payload,
            text_repr=hit.text_repr
        )
        enhanced_hits.append(enhanced_hit)
    
    return enhanced_hits


# Örnek kullanım ve test fonksiyonları
def create_sample_training_data() -> List[Dict[str, Any]]:
    """Örnek eğitim verisi oluştur"""
    # Bu gerçek kullanıcı feedback'i ile doldurulacak
    sample_data = [
        {
            'features': [0.8, 0.6, 0.7, 1.0, 500, 2, 1, 1, 1, 0.9],
            'relevance_score': 0.9
        },
        {
            'features': [0.7, 0.8, 0.75, 0.8, 300, 1, 1, 0, 1, 0.7],
            'relevance_score': 0.8
        },
        {
            'features': [0.6, 0.5, 0.55, 0.6, 200, 0, 0, 1, 0, 0.5],
            'relevance_score': 0.6
        }
    ]
    return sample_data


if __name__ == "__main__":
    # Test
    print("Learning Ranker Test")
    
    # Ranker oluştur
    ranker = LearningRanker()
    
    # Örnek eğitim verisi ile eğit
    training_data = create_sample_training_data()
    ranker.train_model(training_data)
    
    # Özellik önemini göster
    importance = ranker.get_feature_importance()
    print("\nFeature Importance:")
    for feature, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True):
        print(f"  {feature}: {imp:.3f}")
    
    print("\nLearning Ranker ready!")
