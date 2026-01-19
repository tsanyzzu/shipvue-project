import re
from typing import List, Dict

class RegexGuardrail:
    def __init__(self):
        self.patterns = {
            "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "PHONE": r"(\+62|62|0)8[1-9][0-9]{6,11}", 
            "NIK": r"\b[0-9]{16}\b" # \b agar tidak menangkap angka 16 digit di tengah text lain
        }

    def scan(self, text: str) -> List[Dict]:
        findings = []
        
        for label, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                findings.append({
                    "text": match.group(),
                    "label": label,
                    "start": match.start(),
                    "end": match.end(),
                    "source": "regex" # 
                })
        
        return findings