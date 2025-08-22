#!/usr/bin/env python3
"""
Health Check Script for PDF to HTML Converter

This script performs basic validation of the project structure
and can be run to verify the application is properly set up.
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and report status."""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (MISSING)")
        return False

def check_directory_exists(dirpath, description):
    """Check if a directory exists and report status."""
    if Path(dirpath).is_dir():
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description}: {dirpath} (MISSING)")
        return False

def main():
    """Run comprehensive health checks."""
    print("🔍 PDF to HTML Converter - Health Check")
    print("=" * 50)
    
    checks_passed = 0
    total_checks = 0
    
    # Core structure checks
    print("\n📁 Project Structure:")
    structure_checks = [
        ("backend/", "Backend directory"),
        ("frontend/", "Frontend directory"),
        ("backend/app/", "Backend app directory"),
        ("frontend/src/", "Frontend source directory"),
    ]
    
    for path, desc in structure_checks:
        total_checks += 1
        if check_directory_exists(path, desc):
            checks_passed += 1
    
    # Core files check
    print("\n📄 Core Files:")
    file_checks = [
        ("README.md", "Project documentation"),
        ("docker-compose.yml", "Docker composition"),
        (".gitignore", "Git ignore rules"),
        ("backend/requirements.txt", "Backend dependencies"),
        ("backend/Dockerfile", "Backend Docker image"),
        ("frontend/package.json", "Frontend dependencies"),
        ("frontend/Dockerfile", "Frontend Docker image"),
        ("frontend/nginx.conf", "Nginx configuration"),
    ]
    
    for filepath, desc in file_checks:
        total_checks += 1
        if check_file_exists(filepath, desc):
            checks_passed += 1
    
    # Backend modules check
    print("\n🐍 Backend Modules:")
    backend_modules = [
        ("backend/app/__init__.py", "Backend package init"),
        ("backend/app/main.py", "FastAPI main application"),
        ("backend/app/pdf_processor.py", "PDF processing module"),
        ("backend/app/gemini_client.py", "Gemini AI client"),
        ("backend/app/html_renderer.py", "HTML renderer with Playwright"),
        ("backend/app/refinement_engine.py", "Iterative refinement engine"),
        ("backend/app/websocket_manager.py", "WebSocket manager"),
    ]
    
    for filepath, desc in backend_modules:
        total_checks += 1
        if check_file_exists(filepath, desc):
            checks_passed += 1
    
    # Frontend components check
    print("\n⚛️ Frontend Components:")
    frontend_components = [
        ("frontend/src/App.jsx", "Main React app"),
        ("frontend/src/components/FileUpload.jsx", "File upload component"),
        ("frontend/src/components/ConversionProgress.jsx", "Progress tracking component"),
        ("frontend/src/components/HtmlPreview.jsx", "HTML preview component"),
        ("frontend/vite.config.js", "Vite configuration"),
    ]
    
    for filepath, desc in frontend_components:
        total_checks += 1
        if check_file_exists(filepath, desc):
            checks_passed += 1
    
    # Environment check
    print("\n🔧 Configuration:")
    config_checks = [
        ("backend/.env", "Backend environment variables"),
    ]
    
    for filepath, desc in config_checks:
        total_checks += 1
        if check_file_exists(filepath, desc):
            checks_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Health Check Summary:")
    print(f"   Checks passed: {checks_passed}/{total_checks}")
    
    if checks_passed == total_checks:
        print("🎉 All checks passed! Project is ready for deployment.")
        return 0
    elif checks_passed >= total_checks * 0.8:
        print("⚠️  Most checks passed. Minor issues detected.")
        return 1
    else:
        print("❌ Multiple issues detected. Please review the project structure.")
        return 2

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
