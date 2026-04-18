#!/usr/bin/env python3

import sys
import os

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        print("🔧 Inicializando base de datos...")
        
        # Importar después de agregar al path
        from app.db.database import engine
        # from app.models.models import Base
        from app.db.init_db import init_db
        
        # Crear todas las tablas
        print("📋 Creando tablas...")
        engine.metadata.create_all(bind=engine)
        print("✅ Tablas creadas exitosamente")
        
        # Inicializar datos
        print("📝 Inicializando datos por defecto...")
        init_db()
        
        print("🎉 Base de datos inicializada correctamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
