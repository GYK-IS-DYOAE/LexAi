#!/usr/bin/env python3
"""
Kullanıcıyı admin yapmak için script
"""

import os
import sys
sys.path.insert(0, 'src')

# Database URL'i ayarla
os.environ['DATABASE_URL'] = 'postgresql://lexuser:lexpass@localhost:5432/lexai'

try:
    from src.core.db import SessionLocal
    from src.models.auth.user_model import User
    
    db = SessionLocal()
    try:
        # Kullanıcıyı bul
        user_email = 'aasliasutay@gmail.com'
        user = db.query(User).filter(User.email == user_email).first()
        
        if user:
            print(f'Kullanıcı bulundu: {user.email}')
            print(f'Mevcut admin durumu: {user.is_admin}')
            
            # Admin yap
            user.is_admin = True
            db.commit()
            db.refresh(user)
            
            print(f'✅ {user.email} kullanıcısı admin yapıldı!')
            print(f'Yeni admin durumu: {user.is_admin}')
        else:
            print(f'❌ {user_email} kullanıcısı bulunamadı!')
            
        # Tüm admin kullanıcıları listele
        admin_users = db.query(User).filter(User.is_admin == True).all()
        print(f'\nToplam admin kullanıcı sayısı: {len(admin_users)}')
        for admin in admin_users:
            print(f'  - {admin.email} (ID: {admin.id})')
            
    finally:
        db.close()
        
except Exception as e:
    print(f'Hata: {e}')
    print('PostgreSQL bağlantısı kurulamadı. Docker Compose çalıştırıldı mı?')





