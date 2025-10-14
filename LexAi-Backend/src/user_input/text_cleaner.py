import re
import html
import unicodedata
from typing import Dict, Any

class TextCleaner:
    """
    Kullanıcı girdilerini LLM modeline göndermeden önce temizler.
    Basit, hızlı ve kullanıcı dostu.
    """
    
    # Regex pattern'leri (önceden derlenmiş - performans için)
    EMOJI = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF"
        "\U00002600-\U000026FF\U00002B00-\U00002BFF]+", 
        flags=re.UNICODE
    )
    
    URL = re.compile(r'http[s]?://\S+|www\.\S+', re.IGNORECASE)
    EMAIL = re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b')
    PHONE = re.compile(r'(\+?90\s?)?(\d{3}[\s.-]?)?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}')
    
    # Küçük harfe çevrildikten sonra aranacak zararlı pattern'ler
    MALICIOUS = re.compile(r'<script|javascript:|onerror=|onclick=|<iframe')
    
    EXTRA_SPACE = re.compile(r'\s+')
    
    # HTML tag'lerini tamamen temizlemek için
    HTML_TAGS = re.compile(r'<[^>]+>')
    
    def __init__(self, max_length: int = 5000):
        """
        Args:
            max_length: Maksimum metin uzunluğu (DoS koruması)
        """
        self.max_length = max_length
    
    def clean(self, text: str) -> str:
        """
        Metni temizler ve normalize eder.
        
        İşlem sırası (optimize edilmiş):
        1. Boş kontrol ve tip kontrolü
        2. Uzunluk limiti kontrolü
        3. HTML decode (encoding bypass'larını engeller)
        4. Küçük harfe çevirme (ERKEN - case-based bypass'ları engeller)
        5. Güvenlik kontrolü (XSS, injection)
        6. Unicode normalizasyon (Türkçe karakterler için)
        7. URL, email, telefon temizleme
        8. Emoji temizleme
        9. Özel karakter temizleme
        10. Fazla boşluk temizleme
        
        Args:
            text: Temizlenecek metin
            
        Returns:
            str: Temizlenmiş metin
        """
        # 1. Boş veya geçersiz input kontrolü
        if not text or not isinstance(text, str):
            return ""
        
        # 2. Uzunluk limiti (DoS koruması)
        if len(text) > self.max_length:
            text = text[:self.max_length]
        
        # 3. HTML entity decode (encoding bypass'ları engeller)
        # Örnek: &lt;script&gt; -> <script>
        text = html.unescape(text)
        
        # 4. Küçük harfe çevirme (GÜVENLİK İÇİN ERKEN)
        # <ScRiPt>, <SCRIPT> gibi case-based bypass'ları engeller
        text = text.lower()
        
        # 5. Güvenlik kontrolü - zararlı pattern varsa boş döner
        # Artık sadece küçük harf pattern'leri arıyoruz
        if self.MALICIOUS.search(text):
            return ""
        
        # 6. Unicode normalizasyon (Türkçe karakterler için önemli)
        # NFC: Canonical composition - Türkçe için en uygun
        text = unicodedata.normalize('NFC', text)
        
        # 7. URL temizleme (phishing/spam koruması)
        text = self.URL.sub(' ', text)
        
        # 8. Email temizleme (PII koruması)
        text = self.EMAIL.sub(' ', text)
        
        # 9. Telefon temizleme (PII koruması)
        text = self.PHONE.sub(' ', text)
        
        # 10. Emoji temizleme (model compatibility)
        text = self.EMOJI.sub(' ', text)
        
        # 11. HTML tag'lerini tamamen temizle
        text = self.HTML_TAGS.sub(' ', text)
        
        # 12. Sadece Türkçe karakterler, rakamlar ve temel noktalama bırak
        text = ''.join(c for c in text if c.isalnum() or c.isspace() or c in '.,;:!?()-')
        
        text = self.EXTRA_SPACE.sub(' ', text).strip()
        
        return text
    
    def clean_with_details(self, text: str) -> Dict[str, Any]:
        """
        Metni temizler ve detaylı bilgi döner.
        
        Returns:
            Dict: {
                'cleaned': temizlenmiş metin,
                'original_length': orijinal uzunluk,
                'cleaned_length': temizlenmiş uzunluk,
                'is_safe': güvenli mi
            }
        """
        if not text or not isinstance(text, str):
            return {
                'cleaned': '',
                'original_length': 0,
                'cleaned_length': 0,
                'is_safe': True
            }
        
        original_length = len(text)
        
        text_lower = html.unescape(text).lower()
        is_safe = not bool(self.MALICIOUS.search(text_lower))
        
        cleaned = self.clean(text)
        
        return {
            'cleaned': cleaned,
            'original_length': original_length,
            'cleaned_length': len(cleaned),
            'is_safe': is_safe
        }


_cleaner = TextCleaner()


def clean_text(text: str) -> str:
    """
    Basit kullanım için fonksiyon.
    
    Example:
        clean_text("Merhaba! 🎉 https://test.com")
        # Output: "merhaba"
    """
    return _cleaner.clean(text)


def clean_text_detailed(text: str) -> Dict[str, Any]:
    """
    Detaylı sonuç dönen fonksiyon.
    
    Example:
        result = clean_text_detailed("Test 🎉")
        print(result['cleaned'])
        print(result['is_safe'])
    """
    return _cleaner.clean_with_details(text)


# Test
if __name__ == "__main__":
    test_texts = [
        "Merhaba! 🎉 Bu bir test https://example.com",
        "İletişim: test@email.com veya 0532 123 45 67",
        "Çok    fazla     boşluk!!!",
        "ŞİŞLİ'de çalışıyorum",
        "<ScRiPt>alert('xss')</ScRiPt>",  
        "<SCRIPT>alert('xss')</SCRIPT>",   
    ]
    
    print("Temizleme Testleri:")
    print("=" * 70)
    for text in test_texts:
        result = clean_text_detailed(text)
        print(f"Orijinal:  {text}")
        print(f"Temiz:     {result['cleaned']}")
        print(f"Güvenli:   {result['is_safe']}")
        print(f"Uzunluk:   {result['original_length']} -> {result['cleaned_length']}")
        print("-" * 70)