#!/usr/bin/env python3
"""
Pre-deployment validation script
Checks deployment configuration and prerequisites
"""

import os
import subprocess
import sys
from pathlib import Path


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_status(message, status):
    """Print a status message with color"""
    if status == "OK":
        print(f"{Colors.GREEN}✓{Colors.END} {message}")
    elif status == "FAIL":
        print(f"{Colors.RED}✗{Colors.END} {message}")
    elif status == "WARN":
        print(f"{Colors.YELLOW}⚠{Colors.END} {message}")
    else:
        print(f"{Colors.BLUE}ℹ{Colors.END} {message}")


def check_command(command):
    """Check if a command is available"""
    try:
        subprocess.run(
            [command, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_file(filepath):
    """Check if a file exists"""
    return Path(filepath).exists()


def get_file_size(filepath):
    """Get file size in MB"""
    return Path(filepath).stat().st_size / (1024 * 1024)


def main():
    print("\n" + "=" * 60)
    print("SAM3 API Deployment Validation")
    print("=" * 60 + "\n")
    
    all_checks_passed = True
    warnings = []
    
    # 1. Check Required Commands
    print(f"{Colors.BLUE}Checking Prerequisites...{Colors.END}\n")
    
    if check_command("gcloud"):
        print_status("gcloud CLI installed", "OK")
    else:
        print_status("gcloud CLI not found", "FAIL")
        print("  Install: https://cloud.google.com/sdk/docs/install")
        all_checks_passed = False
    
    if check_command("docker"):
        print_status("Docker installed", "OK")
    else:
        print_status("Docker not found", "WARN")
        warnings.append("Docker needed for local testing and manual deployment")
    
    # 2. Check Required Files
    print(f"\n{Colors.BLUE}Checking Deployment Files...{Colors.END}\n")
    
    required_files = [
        "Dockerfile",
        "cloudbuild.yaml",
        "deploy_gpu.sh",
        "deploy_manual.sh",
        ".dockerignore",
        "requirements-api.txt",
        "api/main.py",
        "api/services/sam3_service.py",
        "run_api.py",
    ]
    
    for file in required_files:
        if check_file(file):
            print_status(f"{file} exists", "OK")
        else:
            print_status(f"{file} missing", "FAIL")
            all_checks_passed = False
    
    # 3. Check SAM3 Package
    print(f"\n{Colors.BLUE}Checking SAM3 Package...{Colors.END}\n")
    
    sam3_files = [
        "sam3/__init__.py",
        "sam3/model/__init__.py",
        "pyproject.toml",
    ]
    
    for file in sam3_files:
        if check_file(file):
            print_status(f"{file} exists", "OK")
        else:
            print_status(f"{file} missing", "FAIL")
            all_checks_passed = False
    
    # 4. Check Scripts are Executable
    print(f"\n{Colors.BLUE}Checking Script Permissions...{Colors.END}\n")
    
    scripts = ["deploy_gpu.sh", "deploy_manual.sh", "deploy_test.sh"]
    
    for script in scripts:
        if check_file(script):
            if os.access(script, os.X_OK):
                print_status(f"{script} is executable", "OK")
            else:
                print_status(f"{script} not executable", "WARN")
                warnings.append(f"Run: chmod +x {script}")
        else:
            print_status(f"{script} not found", "FAIL")
    
    # 5. Check Documentation
    print(f"\n{Colors.BLUE}Checking Documentation...{Colors.END}\n")
    
    docs = [
        "DEPLOYMENT.md",
        "QUICKSTART.md",
        "README_API.md",
    ]
    
    for doc in docs:
        if check_file(doc):
            print_status(f"{doc} exists", "OK")
        else:
            print_status(f"{doc} missing", "WARN")
            warnings.append(f"Documentation file {doc} is missing")
    
    # 6. Check Docker Build Context Size
    print(f"\n{Colors.BLUE}Checking Build Context...{Colors.END}\n")
    
    # Estimate build context size
    total_size = 0
    large_dirs = []
    
    for root, dirs, files in os.walk("."):
        # Skip hidden and common large directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["outputs", "checkpoints", "weights", "assets"]]
        
        for file in files:
            filepath = Path(root) / file
            if filepath.exists():
                size = filepath.stat().st_size
                total_size += size
                
                # Check for large files
                if size > 100 * 1024 * 1024:  # > 100 MB
                    large_dirs.append((str(filepath), size / (1024 * 1024)))
    
    total_size_mb = total_size / (1024 * 1024)
    
    if total_size_mb < 500:
        print_status(f"Build context size: {total_size_mb:.2f} MB", "OK")
    elif total_size_mb < 1000:
        print_status(f"Build context size: {total_size_mb:.2f} MB", "WARN")
        warnings.append("Build context is large. Consider optimizing .dockerignore")
    else:
        print_status(f"Build context size: {total_size_mb:.2f} MB", "FAIL")
        print("  Build context is very large. Update .dockerignore to exclude unnecessary files.")
        all_checks_passed = False
    
    if large_dirs:
        print(f"\n  Large files found:")
        for filepath, size in large_dirs[:5]:
            print(f"    - {filepath}: {size:.2f} MB")
    
    # 7. GCP Configuration
    print(f"\n{Colors.BLUE}Checking GCP Configuration...{Colors.END}\n")
    
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
            text=True
        )
        project_id = result.stdout.strip()
        
        if project_id and project_id != "(unset)":
            print_status(f"GCP Project: {project_id}", "OK")
        else:
            print_status("No GCP project configured", "WARN")
            warnings.append("Run: gcloud config set project YOUR_PROJECT_ID")
    except subprocess.CalledProcessError:
        print_status("Cannot get GCP project", "WARN")
        warnings.append("Run: gcloud config set project YOUR_PROJECT_ID")
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60 + "\n")
    
    if all_checks_passed and not warnings:
        print(f"{Colors.GREEN}✓ All checks passed!{Colors.END}")
        print("\nYou're ready to deploy:")
        print("  ./deploy_gpu.sh YOUR_PROJECT_ID")
        return 0
    elif all_checks_passed:
        print(f"{Colors.YELLOW}⚠ All critical checks passed with warnings{Colors.END}\n")
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        print("\nYou can proceed with deployment, but address warnings first:")
        print("  ./deploy_gpu.sh YOUR_PROJECT_ID")
        return 0
    else:
        print(f"{Colors.RED}✗ Some checks failed{Colors.END}\n")
        print("Please fix the issues above before deploying.")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  - {warning}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
