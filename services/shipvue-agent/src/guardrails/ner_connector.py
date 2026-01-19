import requests
import time
from typing import List, Dict

class NERConnector:
    def __init__(self, service_url: str = "http://localhost:8000"):
        self.url = f"{service_url}/scan"

    def scan(self, text: str) -> List[Dict]:
        payload = {"text": text}
        try:
            #  Request ke NER Service
            response = requests.post(self.url, json=payload, timeout=5)
            response.raise_for_status() # Raise error selain status 200
            
            data = response.json()
            entities = data.get("entities", [])
            
            # Tag source
            formatted_entities = []
            for ent in entities:
                ent["source"] = "ner_model"
                formatted_entities.append(ent)
                
            return formatted_entities

        except requests.exceptions.ConnectionError:
            print("[WARNING] Gagal konek ke NER Service. Pastikan service jalan di port 8000.")
            return [] # Kembalikan kosong jika service mati
        except Exception as e:
            print(f"[ERROR] NER Service Error: {e}")
            return []