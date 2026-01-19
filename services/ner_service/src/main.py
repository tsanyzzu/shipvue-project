import spacy
import time
import psutil
import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from pathlib import Path

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("NER-Service")

# Inisialisasi App
app = FastAPI(
    title="Shipvue NER Service",
    description="Microservice untuk deteksi PII (Nama & Alamat) menggunakan Custom Spacy Model",
    version="1.0.0"
)

# Load Model
BASE_DIR = Path(__file__).resolve().parent.parent 
MODEL_PATH = BASE_DIR / "models" / "shipvue_ner"
try:
    nlp = spacy.load(MODEL_PATH)
    print("[INIT] Model loaded successfully!")
except Exception as e:
    print(f"[ERROR] Gagal load model. Error: {e}")
    nlp = spacy.blank("id")

# Inisialisasi Process untuk monitoring resource 
process = psutil.Process(os.getpid())

# Skema Input & Output 
class TextRequest(BaseModel):
    text: str

class Entity(BaseModel):
    text: str
    label: str
    start: int
    end: int

class NERResponse(BaseModel):
    entities: List[Entity]
    latency_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float

@app.get("/")
def health_check():
    return {"status": "active", "model": "shipvue_ner"}

@app.post("/scan", response_model=NERResponse)
def scan_text(request: TextRequest):
    if not nlp:
        raise HTTPException(status_code=500, detail="Model NER belum dimuat.")
    
    # Start Timer 
    start_time = time.perf_counter()
    
    # Model Inference 
    doc = nlp(request.text)
    
    # End Timer
    end_time = time.perf_counter()
    latency = (end_time - start_time) * 1000  
    
    # Ambil Metrics Resource
    memory = process.memory_info().rss / 1024 / 1024 
    
    # interval=None berarti non-blocking (membandingkan dengan call sebelumnya)
    cpu = process.cpu_percent(interval=None) 
    
    # Format Output
    entities = []
    for ent in doc.ents:
        entities.append(Entity(
            text=ent.text,
            label=ent.label_,
            start=ent.start_char,
            end=ent.end_char
        ))
    
    logger.info(f"Latency: {latency:.2f}ms | Mem: {memory:.2f}MB | CPU: {cpu}%")
    
    return NERResponse(
        entities=entities,
        latency_ms=round(latency, 2),
        memory_usage_mb=round(memory, 2),
        cpu_usage_percent=round(cpu, 2) 
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)