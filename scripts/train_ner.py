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
    TEST_DATA = [
    ("Halo min, posisi paket Andi Saputra sekarang dimana ya?", {"entities": [(23, 35, "PERSON")]}),
    ("antar ke jl. mawar no 5 malang, penerimanya siti aminah", {"entities": [(9, 31, "ADDRESS"), (45, 56, "PERSON")]}), 
    ("paket an. Budi Gunawan belum sampe ke Surabaya", {"entities": [(10, 22, "PERSON"), (38, 46, "ADDRESS")]}), 
    ("rumah saya di Komp. Griya Indah Blok A1", {"entities": [(14, 39, "ADDRESS")]}), 
    ("pagi, saya mau lapor barang rusak atas nama Dewi Sartika", {"entities": [(44, 56, "PERSON")]}),
    ("Bapak Budi Santoso tinggal di Jalan Melati Nomor 15, Kelurahan Menteng, Jakarta Pusat.", {"entities": [(6, 18, "PERSON"), (30, 85, "ADDRESS")]}),
    ("Siti Aminah mengirimkan paket ke Jl. Ahmad Yani No. 12B, RT 003/RW 005, Bandung.", {"entities": [(0, 11, "PERSON"), (33, 79, "ADDRESS")]}),
    ("Kemarin saya bertemu Andi Wijaya saat dia sedang berjalan di sekitar Komplek Perumahan Griya Indah Blok C4, Bogor.", {"entities": [(21, 32, "PERSON"), (69, 113, "ADDRESS")]}),
    ("Dewi Lestari bekerja di Gedung Cyber 2, Kuningan, Jakarta.", {"entities": [(0, 12, "PERSON"), (24, 57, "ADDRESS")]}),
    ("Surat keputusan tersebut ditandatangani oleh Dr. Ir. H. Agus Setiawan, M.Sc. di kantornya.", {"entities": [(45, 75, "PERSON")]}),
    ("Tolong kirimkan dokumen ini kepada Rina Permata yang beralamat di Dusun Krajan, Desa Sumbersekar, Kecamatan Dau, Kabupaten Malang, Jawa Timur 65151.", {"entities": [(35, 47, "PERSON"), (66, 147, "ADDRESS")]}),
    ("Solo adalah sahabat lama Yogyakarta yang tinggal di Jalan Slamet Riyadi, Surakarta.", {"entities": [(52, 82, "ADDRESS")]}),
    ("penerima paket ini adalah joko susilo yang berlokasi di perumahan taman palem regency blok a1 no 5, surabaya.", {"entities": [(26, 37, "PERSON"), (56, 108, "ADDRESS")]}),
    ("Anita Rahmawati menunggu di depan Toko Kelontong Berkah, Gg. Haji Umar, Depok.", {"entities": [(0, 15, "PERSON"), (34, 77, "ADDRESS")]}),
    ("Muhammad Rizky Pratama Putra baru saja pindah ke Apartemen Green Pramuka City Tower Chrysant Lantai 12, Jakarta Timur.", {"entities": [(0, 28, "PERSON"), (49, 117, "ADDRESS")]})
]

    print("\n" + "="*40)
    print("LAPORAN EVALUASI MODEL NER (Test Set)")
    print("="*40)

    metrics = evaluate_model(ner_model, TEST_DATA)
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
    doc = ner_model(random.choice(TEST_DATA)[0])
    print("\n--- Test Prediksi ---")
    print(f"Kalimat: {doc.text}")
    for ent in doc.ents:
        print(f"Deteksi: {ent.text} ({ent.label_})")

    # Simpan Model
    # output_dir = Path(MODEL_OUTPUT_DIR)
    # if not output_dir.exists():
    #     output_dir.mkdir(parents=True)
        
    # ner_model.to_disk(output_dir)
    # print(f"\nModel tersimpan di: {output_dir}")