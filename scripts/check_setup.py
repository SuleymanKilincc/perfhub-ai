"""
Setup checker - verifies all components are properly configured
"""
import os
import sys
from pathlib import Path

def check_python_packages():
    """Check if required Python packages are installed"""
    required = [
        'fastapi', 'uvicorn', 'google-genai', 'python-dotenv',
        'pydantic', 'wmi', 'psutil', 'GPUtil', 'requests'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing Python packages: {', '.join(missing)}")
        print(f"   Install with: pip install {' '.join(missing)}")
        return False
    else:
        print("✅ All Python packages installed")
        return True

def check_env_file():
    """Check if .env file exists and has API key"""
    env_path = Path(__file__).parent.parent / '.env'
    
    if not env_path.exists():
        print("❌ .env file not found")
        print("   Create .env file with: GEMINI_API_KEY=your_key_here")
        return False
    
    with open(env_path) as f:
        content = f.read()
        if 'GEMINI_API_KEY' not in content:
            print("⚠️  .env file exists but GEMINI_API_KEY not set")
            return False
        if 'your_key_here' in content or 'GEMINI_API_KEY=' in content.split('\n')[0]:
            print("⚠️  GEMINI_API_KEY appears to be placeholder")
            return False
    
    print("✅ .env file configured")
    return True

def check_database():
    """Check if database exists and is populated"""
    db_path = Path(__file__).parent.parent / 'data' / 'hardware_db.sqlite'
    
    if not db_path.exists():
        print("⚠️  Database not found (will be created on first run)")
        return True
    
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM cpus")
    cpu_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM gpus")
    gpu_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games")
    game_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"✅ Database found: {cpu_count} CPUs, {gpu_count} GPUs, {game_count} games")
    return True

def check_frontend():
    """Check if frontend dependencies are installed"""
    node_modules = Path(__file__).parent.parent / 'frontend' / 'node_modules'
    
    if not node_modules.exists():
        print("❌ Frontend dependencies not installed")
        print("   Run: cd frontend && npm install")
        return False
    
    print("✅ Frontend dependencies installed")
    return True

def main():
    print("="*60)
    print("PerfHub AI - Setup Checker")
    print("="*60)
    print()
    
    checks = [
        ("Python Packages", check_python_packages),
        ("Environment File", check_env_file),
        ("Database", check_database),
        ("Frontend", check_frontend),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        results.append(check_func())
    
    print("\n" + "="*60)
    if all(results):
        print("✅ All checks passed! You're ready to run PerfHub AI")
        print("\nTo start:")
        print("  Backend:  python backend/main.py")
        print("  Frontend: cd frontend && npm run dev")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
    print("="*60)

if __name__ == "__main__":
    main()
