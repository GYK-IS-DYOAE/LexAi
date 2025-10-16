"""
Similar Case Machine Learning Modeli
Bu script, hukuki case'ler için benzerlik tahmin modeli oluşturur.
"""

import json
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Embedding, LSTM
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Tuple
import pickle
import warnings
warnings.filterwarnings('ignore')

class SimilarCaseMLModel:
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(max_features=5000, stop_words=None)
        self.label_encoder = LabelEncoder()
        self.sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.tokenizer = Tokenizer(num_words=10000)
        
    def load_and_preprocess_data(self, file_path: str, max_samples: int = 1000):
        """Veriyi yükle ve ön işle"""
        print("Veri yukleniyor ve on isleniyor...")
        
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= max_samples:
                    break
                try:
                    data.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        
        # DataFrame oluştur
        df = pd.DataFrame(data)
        df['question'] = df['output'].apply(lambda x: x['question'])
        df['answer'] = df['output'].apply(lambda x: x['answer'])
        df['combined_text'] = df['question'] + ' ' + df['answer']
        
        # Hukuk kategorilerini çıkar
        df['category'] = self.extract_legal_categories(df['question'])
        
        print(f"Toplam {len(df)} kayit yuklendi")
        print(f"Kategori dagilimi:")
        print(df['category'].value_counts())
        
        return df
    
    def extract_legal_categories(self, questions: pd.Series) -> List[str]:
        """Sorulardan hukuk kategorilerini çıkar"""
        categories = []
        
        for question in questions:
            question_lower = question.lower()
            
            if any(word in question_lower for word in ['iş', 'çalışan', 'işçi', 'işveren', 'maaş', 'ücret']):
                categories.append('İş Hukuku')
            elif any(word in question_lower for word in ['tapu', 'gayrimenkul', 'taşınmaz', 'kadastro']):
                categories.append('Gayrimenkul Hukuku')
            elif any(word in question_lower for word in ['temyiz', 'istinaf', 'karar', 'mahkeme']):
                categories.append('Usul Hukuku')
            elif any(word in question_lower for word in ['miras', 'vasiyet', 'mirasçı']):
                categories.append('Miras Hukuku')
            elif any(word in question_lower for word in ['sözleşme', 'borç', 'alacak']):
                categories.append('Borçlar Hukuku')
            elif any(word in question_lower for word in ['ceza', 'suç', 'hapis']):
                categories.append('Ceza Hukuku')
            else:
                categories.append('Diğer')
        
        return categories
    
    def create_similarity_dataset(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Benzerlik veri seti oluştur"""
        print("Benzerlik veri seti olusturuluyor...")
        
        X_pairs = []
        y_similarity = []
        
        # Aynı kategoriden case'ler → benzer (1)
        for category in df['category'].unique():
            category_cases = df[df['category'] == category]
            if len(category_cases) > 1:
                for i in range(len(category_cases)):
                    for j in range(i+1, min(i+3, len(category_cases))):  # Her case için max 2 benzer
                        case1 = category_cases.iloc[i]['combined_text']
                        case2 = category_cases.iloc[j]['combined_text']
                        X_pairs.append([case1, case2])
                        y_similarity.append(1)  # Benzer
        
        # Farklı kategoriden case'ler → benzer değil (0)
        categories = df['category'].unique()
        for i, cat1 in enumerate(categories):
            for j, cat2 in enumerate(categories):
                if i != j:
                    cases1 = df[df['category'] == cat1]
                    cases2 = df[df['category'] == cat2]
                    
                    # Her kategori çifti için birkaç örnek
                    for k in range(min(2, len(cases1))):
                        for l in range(min(2, len(cases2))):
                            case1 = cases1.iloc[k]['combined_text']
                            case2 = cases2.iloc[l]['combined_text']
                            X_pairs.append([case1, case2])
                            y_similarity.append(0)  # Benzer değil
        
        print(f"Toplam {len(X_pairs)} benzerlik cifti olusturuldu")
        print(f"Benzer: {sum(y_similarity)}, Benzer degil: {len(y_similarity) - sum(y_similarity)}")
        
        return np.array(X_pairs), np.array(y_similarity)
    
    def extract_features(self, text_pairs: np.ndarray) -> np.ndarray:
        """Metin çiftlerinden özellik çıkar"""
        print("Ozellikler cikariliyor...")
        
        features = []
        
        # Tüm metinleri birleştir ve TF-IDF fit et
        all_texts = []
        for pair in text_pairs:
            all_texts.extend(pair)
        
        self.tfidf_vectorizer.fit(all_texts)
        
        for pair in text_pairs:
            text1, text2 = pair
            
            # TF-IDF özellikleri
            tfidf1 = self.tfidf_vectorizer.transform([text1])
            tfidf2 = self.tfidf_vectorizer.transform([text2])
            
            # Cosine similarity
            cosine_sim = np.dot(tfidf1.toarray(), tfidf2.toarray().T)[0][0]
            
            # Sentence transformer embeddings
            emb1 = self.sentence_model.encode([text1])[0]
            emb2 = self.sentence_model.encode([text2])[0]
            
            # Embedding cosine similarity
            emb_cosine = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            
            # Metin uzunlukları
            len1, len2 = len(text1), len(text2)
            len_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 0
            
            # Kelime sayıları
            words1, words2 = len(text1.split()), len(text2.split())
            word_ratio = min(words1, words2) / max(words1, words2) if max(words1, words2) > 0 else 0
            
            # Ortak kelimeler
            words1_set = set(text1.lower().split())
            words2_set = set(text2.lower().split())
            common_words = len(words1_set.intersection(words2_set))
            jaccard_sim = common_words / len(words1_set.union(words2_set)) if len(words1_set.union(words2_set)) > 0 else 0
            
            feature_vector = [
                cosine_sim,
                emb_cosine,
                len_ratio,
                word_ratio,
                jaccard_sim,
                len1, len2,
                words1, words2,
                common_words
            ]
            
            features.append(feature_vector)
        
        return np.array(features)
    
    def train_classical_models(self, X: np.ndarray, y: np.ndarray):
        """Klasik ML modellerini eğit"""
        print("Klasik ML modelleri egitiliyor...")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Random Forest
        rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
        rf_model.fit(X_train, y_train)
        rf_pred = rf_model.predict(X_test)
        
        # SVM
        svm_model = SVC(kernel='rbf', random_state=42)
        svm_model.fit(X_train, y_train)
        svm_pred = svm_model.predict(X_test)
        
        print("\n=== RANDOM FOREST SONUCLARI ===")
        print(classification_report(y_test, rf_pred))
        
        print("\n=== SVM SONUCLARI ===")
        print(classification_report(y_test, svm_pred))
        
        # Model kaydet
        with open('rf_model.pkl', 'wb') as f:
            pickle.dump(rf_model, f)
        with open('svm_model.pkl', 'wb') as f:
            pickle.dump(svm_model, f)
        
        return rf_model, svm_model, X_test, y_test, rf_pred, svm_pred
    
    def train_deep_learning_model(self, X: np.ndarray, y: np.ndarray):
        """Deep Learning modelini eğit"""
        print("Deep Learning modeli egitiliyor...")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Model oluştur
        model = Sequential([
            Dense(128, activation='relu', input_shape=(X.shape[1],)),
            Dropout(0.3),
            Dense(64, activation='relu'),
            Dropout(0.3),
            Dense(32, activation='relu'),
            Dropout(0.2),
            Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        # Eğit
        history = model.fit(
            X_train, y_train,
            epochs=50,
            batch_size=32,
            validation_split=0.2,
            verbose=1
        )
        
        # Değerlendir
        test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
        print(f"\nDeep Learning Test Accuracy: {test_acc:.4f}")
        
        # Model kaydet
        model.save('similar_case_dl_model.h5')
        
        return model, history, X_test, y_test
    
    def predict_similarity(self, text1: str, text2: str, model_type: str = 'rf'):
        """İki metin arasında benzerlik tahmin et"""
        # Özellik çıkar
        pair = np.array([[text1, text2]])
        features = self.extract_features(pair)
        
        if model_type == 'rf':
            with open('rf_model.pkl', 'rb') as f:
                model = pickle.load(f)
        elif model_type == 'svm':
            with open('svm_model.pkl', 'rb') as f:
                model = pickle.load(f)
        elif model_type == 'dl':
            model = tf.keras.models.load_model('similar_case_dl_model.h5')
        else:
            raise ValueError("Model type must be 'rf', 'svm', or 'dl'")
        
        # Tahmin
        if model_type == 'dl':
            prediction = model.predict(features)[0][0]
        else:
            prediction = model.predict_proba(features)[0][1]
        
        return prediction
    
    def visualize_results(self, y_test, rf_pred, svm_pred):
        """Sonuçları görselleştir"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Confusion Matrix - Random Forest
        cm_rf = confusion_matrix(y_test, rf_pred)
        sns.heatmap(cm_rf, annot=True, fmt='d', cmap='Blues', ax=axes[0])
        axes[0].set_title('Random Forest Confusion Matrix')
        axes[0].set_xlabel('Predicted')
        axes[0].set_ylabel('Actual')
        
        # Confusion Matrix - SVM
        cm_svm = confusion_matrix(y_test, svm_pred)
        sns.heatmap(cm_svm, annot=True, fmt='d', cmap='Greens', ax=axes[1])
        axes[1].set_title('SVM Confusion Matrix')
        axes[1].set_xlabel('Predicted')
        axes[1].set_ylabel('Actual')
        
        plt.tight_layout()
        plt.savefig('model_results.png', dpi=300, bbox_inches='tight')
        plt.show()

def main():
    print("=== Similar Case Machine Learning Modeli ===")
    
    # Model oluştur
    ml_model = SimilarCaseMLModel()
    
    # Veri yükle
    df = ml_model.load_and_preprocess_data("output_sft.jsonl", max_samples=500)
    
    # Benzerlik veri seti oluştur
    X_pairs, y_similarity = ml_model.create_similarity_dataset(df)
    
    # Özellik çıkar
    X_features = ml_model.extract_features(X_pairs)
    
    # Klasik modelleri eğit
    rf_model, svm_model, X_test, y_test, rf_pred, svm_pred = ml_model.train_classical_models(X_features, y_similarity)
    
    # Deep Learning modelini eğit
    dl_model, history, _, _ = ml_model.train_deep_learning_model(X_features, y_similarity)
    
    # Görselleştir
    ml_model.visualize_results(y_test, rf_pred, svm_pred)
    
    # Test tahminleri
    print("\n=== TEST TAHMINLERI ===")
    test_cases = [
        ("İş kazası sonucu sürekli iş göremezlik durumu nasıl tespit edilir?", 
         "Sürekli iş göremezlik durumu nasıl belirlenir?"),
        ("Temyiz süreci nasıl işler?", 
         "Tapu iptali davasında hangi belgeler gereklidir?")
    ]
    
    for i, (text1, text2) in enumerate(test_cases, 1):
        print(f"\n{i}. Test Cifti:")
        print(f"   Metin 1: {text1[:50]}...")
        print(f"   Metin 2: {text2[:50]}...")
        
        rf_sim = ml_model.predict_similarity(text1, text2, 'rf')
        svm_sim = ml_model.predict_similarity(text1, text2, 'svm')
        dl_sim = ml_model.predict_similarity(text1, text2, 'dl')
        
        print(f"   Random Forest Benzerlik: {rf_sim:.4f}")
        print(f"   SVM Benzerlik: {svm_sim:.4f}")
        print(f"   Deep Learning Benzerlik: {dl_sim:.4f}")
    
    print("\n=== MODEL EGITIMI TAMAMLANDI ===")

if __name__ == "__main__":
