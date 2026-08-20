#!/usr/bin/env python
"""
Credential Leakage Scanner
Scans source code for common credential patterns
"""

import re
import pathlib
import sys
from typing import List, Tuple


class CredentialScanner:
    """Scans files for credential leakage patterns"""
    
    PATTERNS = {
        "hardcoded_password": r"password\s*=\s*['\"]([^'\"]+)['\"]",
        "hardcoded_api_key": r"api[_-]?key\s*=\s*['\"]([^'\"]+)['\"]",
        "hardcoded_token": r"token\s*=\s*['\"]([^'\"]+)['\"]",
        "hardcoded_secret": r"secret\s*=\s*['\"]([^'\"]+)['\"]",
        "aws_key": r"AKIA[0-9A-Z]{16}",
        "private_key": r"-----BEGIN (RSA|PRIVATE) KEY-----",
        "dev_credentials": r"(dev|test|demo)[_-]?(password|secret|key|token)\s*=\s*['\"]",
        "bearer_token": r"Bearer\s+[A-Za-z0-9._\-]+",
        "basic_auth": r"Basic\s+[A-Za-z0-9+/]+=*",
    }
    
    EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", ".vscode"}
    EXCLUDE_FILES = {"*.pyc", "*.pyo", "*.pyd", "*.so", "*.egg-info"}
    
    def __init__(self, root_path: str = "."):
        self.root_path = pathlib.Path(root_path)
        self.findings: List[Tuple[str, str, int, str]] = []
    
    def should_scan(self, file_path: pathlib.Path) -> bool:
        """Check if file should be scanned"""
        # Skip excluded directories
        for excluded in self.EXCLUDE_DIRS:
            if excluded in file_path.parts:
                return False
        
        # Skip excluded file patterns
        for excluded_pattern in self.EXCLUDE_FILES:
            if file_path.match(excluded_pattern):
                return False
        
        # Skip binary files
        if file_path.suffix in {".bin", ".exe", ".so", ".dylib", ".dll"}:
            return False
        
        return True
    
    def scan(self) -> List[Tuple[str, str, int, str]]:
        """Scan directory for credential leaks"""
        for file_path in self.root_path.rglob("*"):
            if not file_path.is_file() or not self.should_scan(file_path):
                continue
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        for pattern_name, pattern in self.PATTERNS.items():
                            if re.search(pattern, line, re.IGNORECASE):
                                # Skip some false positives
                                if self._is_false_positive(file_path, pattern_name, line):
                                    continue
                                
                                self.findings.append((
                                    str(file_path),
                                    pattern_name,
                                    line_num,
                                    line.strip()
                                ))
            except (UnicodeDecodeError, IOError):
                # Skip files that can't be read as text
                pass
        
        return self.findings
    
    def _is_false_positive(self, file_path: pathlib.Path, pattern_name: str, line: str) -> bool:
        """Check for false positives"""
        # Allow environment variable definitions in comments
        if line.strip().startswith("#"):
            return True
        
        # Allow documentation/markdown files
        if file_path.suffix in {".md", ".txt", ".rst"}:
            return True
        
        # Allow test files with mock data
        if "test" in file_path.name.lower():
            if "mock" in line.lower() or "fixture" in line.lower():
                return True
        
        # Allow requirements.txt and similar
        if file_path.name in {"requirements.txt", "setup.py", "setup.cfg"}:
            return True
        
        return False
    
    def report(self):
        """Print scan report"""
        if not self.findings:
            print("✅ No credential leaks detected!")
            return 0
        
        print(f"❌ Found {len(self.findings)} potential credential leak(s):\n")
        
        for file_path, pattern, line_num, line in self.findings:
            print(f"  {file_path}:{line_num}")
            print(f"    Pattern: {pattern}")
            print(f"    {line[:100]}")
            print()
        
        return 1


if __name__ == "__main__":
    scanner = CredentialScanner()
    scanner.scan()
    sys.exit(scanner.report())
