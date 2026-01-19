from typing import List, Dict, Tuple
import os
import time
try:
    from .regex_pattern import RegexGuardrail
    from .ner_connector import NERConnector
except ImportError:
    from regex_pattern import RegexGuardrail
    from ner_connector import NERConnector

class PIIGuardrail:
    def __init__(self, ner_url=None):
        if ner_url is None:
            self.ner_url = os.getenv("NER_SERVICE_URL", "http://localhost:8000")
        else:
            self.ner_url = ner_url
        self.regex_engine = RegexGuardrail()
        self.ner_engine = NERConnector(service_url=self.ner_url)

    def _is_overlap(self, new_ent: Dict, existing_ranges: List[Tuple[int, int]]) -> bool:
        new_start, new_end = new_ent['start'], new_ent['end']
        for exist_start, exist_end in existing_ranges:
            if (new_start < exist_end) and (new_end > exist_start):
                return True
        return False

    def scan(self, text: str) -> Tuple[str, List[Dict], Dict]:
        findings = []
        claimed_ranges = [] 

        perf_metrics = {
            "regex_latency_ms": 0,
            "ner_latency_ms": 0,
            "ner_memory_mb": 0,
            "ner_cpu_percent": 0, 
            "total_latency_ms": 0
        }

        start_total = time.perf_counter()

        # REGEX SCAN
        start_regex = time.perf_counter()
        regex_results = self.regex_engine.scan(text)
        end_regex = time.perf_counter()
        
        regex_latency = (end_regex - start_regex) * 1000
        perf_metrics["regex_latency_ms"] = f"{regex_latency:.4f}" 

        for ent in regex_results:
            findings.append(ent)
            claimed_ranges.append((ent['start'], ent['end']))

        # NER SCAN
        ner_results, ner_perf = self.ner_engine.scan(text)
        
        # Update metrics dari NER Connector
        perf_metrics["ner_latency_ms"] = ner_perf.get("ner_latency_ms", 0)
        perf_metrics["ner_memory_mb"] = ner_perf.get("ner_memory_mb", 0)
        perf_metrics["ner_cpu_percent"] = ner_perf.get("ner_cpu_percent", 0)

        WHITELIST_WORDS = ["shipvue", "min", "admin", "kak", "gan", "sis", "bro"]

        for ent in ner_results:
            # PERBAIKAN: Hapus 'not'. 
            # Artinya: Jika overlap dengan regex, skip (prioritas regex).
            # Jika TIDAK overlap (unik), lanjut ke bawah untuk disimpan.
            if self._is_overlap(ent, claimed_ranges):
                continue

            if ent['text'].lower() in WHITELIST_WORDS:
                continue

            findings.append(ent)       

        # TAGGING & REPLACE PII
        findings.sort(key=lambda x: x['start'])
        label_counts = {}
        for ent in findings:
            lbl = ent['label']
            if lbl not in label_counts:
                label_counts[lbl] = 1
                ent['unique_tag'] = f"[{lbl}_REDACTED]" 
            else:
                label_counts[lbl] += 1
                # Tag kedua dan seterusnya: [PERSON_REDACTED]_2
                ent['unique_tag'] = f"[{lbl}_REDACTED]_{label_counts[lbl]}"

        # REPLACE TEXT
        findings.sort(key=lambda x: x['start'], reverse=True) # Sort Descending agar replace string aman (dari belakang)
        sanitized_text = text
        audit_log = []
        last_replaced_start = float('inf')

        for ent in findings:
            start = ent['start']
            end = ent['end']
            
            if end > last_replaced_start:
                continue

            # Gunakan unique_tag yang sudah dibuat 
            replacement = ent['unique_tag']
            sanitized_text = sanitized_text[:start] + replacement + sanitized_text[end:]
            
            last_replaced_start = start
            
            audit_log.append({
                "original": ent['text'],
                "label": ent['label'],
                "tag": replacement, # Simpan tag unik di log
                "source": ent['source']
            })

        audit_log.reverse()
        
        end_total = time.perf_counter()
        perf_metrics["total_latency_ms"] = round((end_total - start_total) * 1000, 2)
        
        return sanitized_text, audit_log, perf_metrics