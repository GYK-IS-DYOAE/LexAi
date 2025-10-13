#!/usr/bin/env python3
"""
LexAI Main Full-Stack Application Launcher
PostgreSQL ile entegre LexAI Main uygulamasını başlatır
"""

import uvicorn
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path.parent))

if __name__ == "__main__":
    print("\n" + "="*70)
    print(" LexAI Main - Hukuk Asistanı")
    print(" PostgreSQL ile Entegre Full-Stack Uygulama")
    print("="*70)
    print("\n[Endpoints]")
    print("   - Frontend:     http://localhost:3001")
    print("   - Backend API:  http://localhost:8000")
    print("   - API Docs:     http://localhost:8000/docs")
    print("   - Health Check: http://localhost:8000/api/health")
    print("\n[Default Admin]")
    print("   - Email:    admin@lexai.com")
    print("   - Password: admin123")
    print("\n[Gereksinimler]")
    print("   - PostgreSQL: localhost:5432/lexai_main")
    print("   - Frontend: npm run dev (port 3001)")
    print("\n" + "="*70 + "\n")
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

