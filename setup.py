#!/usr/bin/env python3
"""Setup script for Telly Chat"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a shell command"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True


def setup_backend(install_optional=False):
    """Setup backend dependencies"""
    print("\n=== Setting up Backend ===")
    
    backend_dir = Path(__file__).parent / "backend"
    
    # Create virtual environment if it doesn't exist
    venv_path = backend_dir / "venv"
    if not venv_path.exists():
        print("Creating virtual environment...")
        if not run_command([sys.executable, "-m", "venv", "venv"], cwd=backend_dir):
            return False
    
    # Determine pip path
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip"
    else:
        pip_path = venv_path / "bin" / "pip"
    
    # Upgrade pip
    print("Upgrading pip...")
    run_command([str(pip_path), "install", "--upgrade", "pip"], cwd=backend_dir)
    
    # Install core requirements
    print("Installing core dependencies...")
    if not run_command([str(pip_path), "install", "-r", "requirements-core.txt"], cwd=backend_dir):
        print("Failed to install core dependencies!")
        return False
    
    # Install optional requirements if requested
    if install_optional:
        print("Installing optional dependencies...")
        if not run_command([str(pip_path), "install", "-r", "requirements-optional.txt"], cwd=backend_dir):
            print("Warning: Some optional dependencies failed to install")
            print("The app will still work but some features may be unavailable")
    
    print("✓ Backend setup complete!")
    return True


def setup_frontend():
    """Setup frontend dependencies"""
    print("\n=== Setting up Frontend ===")
    
    frontend_dir = Path(__file__).parent / "frontend"
    
    # Check if npm is available
    npm_check = subprocess.run(["npm", "--version"], capture_output=True)
    if npm_check.returncode != 0:
        print("Error: npm not found. Please install Node.js first.")
        return False
    
    # Install dependencies
    print("Installing frontend dependencies...")
    if not run_command(["npm", "install"], cwd=frontend_dir):
        return False
    
    print("✓ Frontend setup complete!")
    return True


def create_env_files():
    """Create example environment files"""
    print("\n=== Creating Environment Files ===")
    
    # Backend .env
    backend_env = Path(__file__).parent / "backend" / ".env.example"
    backend_env.write_text("""# Backend Environment Variables

# AI Model API Keys (at least one required)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here

# Model Provider (anthropic or openai)
MODEL_PROVIDER=anthropic

# Supadata API Key for YouTube transcripts
SUPADATA_API_KEY=your_supadata_key_here

# Optional: Redis URL for session storage
# REDIS_URL=redis://localhost:6379

# Optional: Vector Database Keys
# PINECONE_API_KEY=your_pinecone_key_here
# PINECONE_ENV=us-east-1
""")
    print(f"✓ Created {backend_env}")
    
    # Frontend .env.local
    frontend_env = Path(__file__).parent / "frontend" / ".env.local.example"
    frontend_env.write_text("""# Frontend Environment Variables

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
""")
    print(f"✓ Created {frontend_env}")
    
    print("\nIMPORTANT: Copy the .env.example files to .env and add your API keys!")
    return True


def main():
    """Main setup function"""
    print("Telly Chat Setup")
    print("=" * 50)
    
    # Parse arguments
    install_optional = "--with-optional" in sys.argv
    
    if install_optional:
        print("Installing with optional dependencies...")
    else:
        print("Installing core dependencies only...")
        print("Use '--with-optional' to install all features")
    
    # Setup steps
    success = True
    
    # Backend setup
    if not setup_backend(install_optional):
        success = False
    
    # Frontend setup
    if not setup_frontend():
        success = False
    
    # Create env files
    create_env_files()
    
    # Summary
    print("\n" + "=" * 50)
    if success:
        print("✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Copy .env.example files to .env and add your API keys")
        print("2. Start the backend: cd backend && ./venv/bin/python main.py")
        print("3. Start the frontend: cd frontend && npm run dev")
        print("4. Visit http://localhost:3000")
        
        if not install_optional:
            print("\nNote: Only core features are available.")
            print("To enable advanced features (memory, workflows, etc.), run:")
            print("  python setup.py --with-optional")
    else:
        print("❌ Setup failed! Please check the errors above.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())