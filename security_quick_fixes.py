#!/usr/bin/env python3
"""
Quick Security Fixes for kasa-monitor
Addresses Priority 1 & 2 security vulnerabilities
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

def generate_secure_jwt_secret():
    """Generate and store secure JWT secret"""
    print("🔑 Generating secure JWT secret...")
    
    # Generate 64-byte URL-safe secret
    secret = secrets.token_urlsafe(64)
    
    # Add to .env file
    env_file = Path(".env")
    with open(env_file, "a") as f:
        f.write(f"\nJWT_SECRET_KEY={secret}\n")
    
    print("✅ JWT secret generated and added to .env")
    return secret

def fix_hardcoded_secrets():
    """Fix hardcoded secrets in websocket_manager.py"""
    print("🔒 Fixing hardcoded secrets...")
    
    file_path = Path("backend/websocket_manager.py")
    if not file_path.exists():
        print("⚠️  websocket_manager.py not found")
        return
    
    content = file_path.read_text()
    
    # Replace hardcoded secret fallback
    old_code = 'secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key")'
    new_code = '''secret_key = os.getenv("JWT_SECRET_KEY")
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY environment variable not set")'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        file_path.write_text(content)
        print("✅ Fixed hardcoded secret in websocket_manager.py")
    else:
        print("ℹ️  No hardcoded secret pattern found")

def fix_sql_injection():
    """Fix SQL injection in db_maintenance.py"""
    print("🛡️  Fixing SQL injection vulnerabilities...")
    
    file_path = Path("backend/scripts/database/db_maintenance.py")
    if not file_path.exists():
        print("⚠️  db_maintenance.py not found")
        return
    
    content = file_path.read_text()
    
    # Add import for parameterized queries
    if "from sqlalchemy import text" not in content:
        content = "from sqlalchemy import text\n" + content
    
    # Fix table count query
    old_pattern = 'cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")'
    new_pattern = 'cursor = conn.execute(text("SELECT COUNT(*) FROM :table_name").bindparams(table_name=table_name))'
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        file_path.write_text(content)
        print("✅ Fixed SQL injection in db_maintenance.py")

def update_dependencies():
    """Update critical dependencies"""
    print("📦 Updating dependencies...")
    
    try:
        # Update Python dependencies
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--upgrade",
            "fastapi", "uvicorn", "cryptography", "pyjwt", "sqlalchemy"
        ], check=True)
        print("✅ Python dependencies updated")
        
        # Update Node dependencies
        if Path("package.json").exists():
            subprocess.run(["npm", "audit", "fix"], check=True)
            print("✅ Node dependencies updated")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error updating dependencies: {e}")

def add_security_headers():
    """Add security headers to main.py"""
    print("🛡️  Adding security headers...")
    
    file_path = Path("backend/main.py")
    if not file_path.exists():
        file_path = Path("backend/server.py")
    
    if not file_path.exists():
        print("⚠️  Main server file not found")
        return
    
    content = file_path.read_text()
    
    # Security headers middleware
    security_middleware = '''
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
'''
    
    # Add security headers if not already present
    if "X-Content-Type-Options" not in content:
        # Find where to insert (after app creation)
        if "app = FastAPI(" in content:
            insertion_point = content.find("app = FastAPI(")
            # Find end of FastAPI initialization
            next_function = content.find("\n\n", insertion_point)
            content = content[:next_function] + security_middleware + content[next_function:]
            file_path.write_text(content)
            print("✅ Security headers added")
    else:
        print("ℹ️  Security headers already present")

def main():
    """Run all quick security fixes"""
    print("🚀 Starting security quick fixes for kasa-monitor")
    print("=" * 50)
    
    try:
        # Priority 1 fixes
        generate_secure_jwt_secret()
        fix_hardcoded_secrets()
        fix_sql_injection()
        
        # Priority 2 fixes
        add_security_headers()
        update_dependencies()
        
        print("\n" + "=" * 50)
        print("✅ Security quick fixes completed!")
        print("\n📋 Manual steps remaining:")
        print("1. Review and test the changes")
        print("2. Update CORS configuration with proper origins")
        print("3. Test JWT authentication with new secret")
        print("4. Run security scan to verify fixes")
        print("5. Commit changes to version control")
        
    except Exception as e:
        print(f"❌ Error during security fixes: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()