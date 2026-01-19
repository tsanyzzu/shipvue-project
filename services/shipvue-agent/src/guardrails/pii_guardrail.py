from typing import List, Dict, Tuple
from regex_pattern import RegexGuardrail
from ner_connector import NERConnector

class PIIGuardrail:
    def __init__(self, ner_url="http://localhost:8000"):
        self.regex_engine = RegexGuardrail()
        self.ner_engine = NERConnector(service_url=ner_url)

    def _is_overlap(self, new_ent: Dict, existing_ranges: List[Tuple[int, int]]) -> bool:
        """Cek apakah entity baru bertabrakan dengan area yang sudah diklaim."""
        new_start, new_end = new_ent['start'], new_ent['end']
        for exist_start, exist_end in existing_ranges:
            if (new_start < exist_end) and (new_end > exist_start):
                return True
        return False

    def scan(self, text: str) -> Tuple[str, List[Dict]]:
        findings = []
        claimed_ranges = [] # Menyimpan area text yang sudah "diklaim" oleh Regex

        # REGEX 
        regex_results = self.regex_engine.scan(text)
        
        for ent in regex_results:
            findings.append(ent)
            claimed_ranges.append((ent['start'], ent['end']))

        # NER 
        ner_results = self.ner_engine.scan(text)
        
        for ent in ner_results:
            if not self._is_overlap(ent, claimed_ranges):
                findings.append(ent)

        # SORT & REPLACE 
        findings.sort(key=lambda x: x['start'], reverse=True)# Sort desc berdasarkan start index untuk replacement 

        sanitized_text = text
        audit_log = []
        last_replaced_start = float('inf')

        for ent in findings:
            start = ent['start']
            end = ent['end']
            label = ent['label']

            # Double check overlap internal saat replacement
            if end > last_replaced_start:
                continue

            replacement = f"[{label}_REDACTED]"
            sanitized_text = sanitized_text[:start] + replacement + sanitized_text[end:]
            
            last_replaced_start = start
            
            audit_log.append({
                "original": ent['text'],
                "label": label,
                "source": ent['source']
            })

        audit_log.reverse()
        return sanitized_text, audit_log

# Tes manual
# if __name__ == "__main__":
#     guard = PIIGuardrail()
#     input_text = "Nama saya Budi Santoso, minta tolong cek resi JP888999 dong"
#     print(f"Input Asli: {input_text}\n")
    
#     clean_text, logs = guard.scan(input_text)
    
#     print(f"Sanitized : {clean_text}")
#     print(f"Audit Log : {logs}")