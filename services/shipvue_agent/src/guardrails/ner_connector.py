import requests
import time
from typing import List, Dict

class NERConnector:
    def __init__(self, service_url: str = "http://localhost:8000"):
        self.url = f"{service_url}/scan"

    def scan(self, text: str) -> List[Dict]:
        payload = {"text": text}
        try:
            # Request ke NER Service
            response = requests.post(self.url, json=payload, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            entities = data.get("entities", [])
             
            performance = {
                "ner_latency_ms": data.get("latency_ms", 0),
                "ner_memory_mb": data.get("memory_usage_mb", 0),
                "ner_cpu_percent": data.get("cpu_usage_percent", 0.0) 
            }

            # Tag source
            formatted_entities = []
            for ent in entities:
                ent["source"] = "ner_model"
                formatted_entities.append(ent)
                
            return formatted_entities, performance

        except requests.exceptions.ConnectionError:
            print("[WARNING] Gagal konek ke NER Service. Pastikan service jalan di port 8000.")
            # Return metrics 0 jika gagal
            return [], {"ner_latency_ms": 0, "ner_memory_mb": 0, "ner_cpu_percent": 0} 
        except Exception as e:
            print(f"[ERROR] NER Service Error: {e}")
            return [], {"ner_latency_ms": 0, "ner_memory_mb": 0, "ner_cpu_percent": 0}