import json
import spacy
import random
from spacy.training.example import Example
from spacy.util import minibatch, compounding
from spacy.scorer import Scorer
from pathlib import Path

# Konfigurasi Path
DATA_PATH = "data/raw/shipvue_dataset.json"
MODEL_OUTPUT_DIR = "services/ner-service/models/shipvue_ner"

def load_data(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def train_ner_model(training_data, iterations=50):
    # Buat Blank Model Bahasa Indonesia
    print("Membuat blank model 'id'...")
    nlp = spacy.blank("id") 

    # Tambahkan Pipeline NER jika belum ada
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    
    # Tambahkan Label ke NER
    for _, annotations in training_data:
        for ent in annotations.get("entities"):
            ner.add_label(ent[2])

    print(f"Memulai training untuk {iterations} iterasi...")
    optimizer = nlp.begin_training()

    # Loop Iterasi
    for itn in range(iterations):
        random.shuffle(training_data)
        losses = {}
        
        # Batching data 
        batches = minibatch(training_data, size=compounding(4.0, 32.0, 1.001))

        for batch in batches:
            texts, annotations = zip(*batch)
            examples = [] # Object Example 
            for i in range(len(texts)):
                doc = nlp.make_doc(texts[i])
                example = Example.from_dict(doc, annotations[i])
                examples.append(example)
            
            # Update bobot model
            nlp.update(
                examples,
                drop=0.5, 
                losses=losses,
            )
        
        # Print loss setiap 5 iterasi
        if (itn + 1) % 5 == 0:
            print(f"Iterasi {itn+1}/{iterations} - Losses: {losses}")

    return nlp

def evaluate_model(nlp, test_data):
    scorer = Scorer()
    examples = []
    
    print(f"\nMengevaluasi model pada {len(test_data)} data uji...")
    for text, annotations in test_data:
        doc_pred = nlp(text)
        example = Example.from_dict(doc_pred, annotations)
        examples.append(example)
        
    scores = scorer.score(examples)
    return scores

if __name__ == "__main__":
    raw_data = load_data(DATA_PATH)
    train_data = []
    for item in raw_data:
        train_data.append((item[0], item[1]))

    ner_model = train_ner_model(train_data)
    
    # Test Prediksi
    REAL_TEST_DATA = [
    ("Halo min, posisi paket Andi Saputra sekarang dimana ya?", {"entities": [(23, 35, "PERSON")]}),
    ("antar ke jl. mawar no 5 malang, penerimanya siti aminah", {"entities": [(9, 31, "ADDRESS"), (45, 56, "PERSON")]}), # Lowercase extreme
    ("paket an. Budi Gunawan belum sampe ke Surabaya", {"entities": [(10, 22, "PERSON"), (38, 46, "ADDRESS")]}), # Struktur beda
    ("rumah saya di Komp. Griya Indah Blok A1", {"entities": [(14, 39, "ADDRESS")]}), # Alamat tanpa nama
    ("pagi, saya mau lapor barang rusak atas nama Dewi Sartika", {"entities": [(44, 56, "PERSON")]})
]

    print("\n" + "="*40)
    print("LAPORAN EVALUASI MODEL NER (Test Set)")
    print("="*40)

    metrics = evaluate_model(ner_model, REAL_TEST_DATA)
    ents_per_type = metrics.get('ents_per_type', {}) # Ambil nilai per entitas
    
    print(f"{'ENTITY':<10} | {'PRECISION':<10} | {'RECALL':<10} | {'F1-SCORE':<10}")
    print("-" * 46)
    
    for label, scores in ents_per_type.items():
        p = scores['p'] * 100
        r = scores['r'] * 100
        f = scores['f'] * 100
        print(f"{label:<10} | {p:.2f}%      | {r:.2f}%      | {f:.2f}%")
    
    print("-" * 46)
    overall_f1 = metrics.get('ents_f', 0) * 100
    print(f"OVERALL F1 : {overall_f1:.2f}%")
    print("="*40)

    #Preview test
    doc = ner_model(random.choice(REAL_TEST_DATA)[0])
    print("\n--- Test Prediksi ---")
    print(f"Kalimat: {doc.text}")
    for ent in doc.ents:
        print(f"Deteksi: {ent.text} ({ent.label_})")

    # Simpan Model
    output_dir = Path(MODEL_OUTPUT_DIR)
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        
    ner_model.to_disk(output_dir)
    print(f"\nModel tersimpan di: {output_dir}")