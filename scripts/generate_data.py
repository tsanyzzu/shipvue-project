import json
import random
import spacy
from faker import Faker
from tqdm import tqdm

# Load blank model 
nlp = spacy.blank("id")

fake = Faker('id_ID')
Faker.seed(42)

NUM_SAMPLES = 400  

# Template POSITIF 
POSITIVE_TEMPLATES = [
    "Paket saya atas nama {name} yang dikirim ke {addr} kok belum sampai?",
    "Tolong cek resi untuk penerima {name} di {addr}.",
    "Kurir bilang alamat {addr} tidak ditemukan, padahal {name} ada di rumah.",
    "Saya {name}, mau komplain pengiriman ke {addr} yang rusak.",
    "Apakah bisa jemput paket dari {addr} atas nama {name}?",
    "{name} disini. Paket ke {addr} aman?",
    "Alamat: {addr}. Penerima: {name}. Cek dong.",
    "Kirim ke {addr} ya min, titip ke {name}.",
    "Woy paket {name} nyasar ke {addr} nih!",
    "Min, {addr} bisa cod gak? an {name}.",
    "Posisi paket {name} sekarang dimana ya? tujuannya ke {addr}",
    "antar ke {addr} ya, penerimanya {name}",
    "paket an. {name} belum sampe ke {addr}",
    "rumah saya di {addr}, tolong dicek a.n {name}",
    "pagi, saya mau lapor barang rusak atas nama {name} di {addr}"
]

# Template NEGATIF (Tanpa Entity)
NEGATIVE_TEMPLATES = [
    "Halo admin, saya mau tanya resi saya kok tidak bergerak?",
    "Saya mau lapor barang rusak, gimana caranya?",
    "Saya kecewa sekali dengan pelayanan kurirnya.",
    "Pagi, saya sudah menunggu 3 hari.",
    "Apakah saya bisa ambil paket sendiri di gudang?",
    "Saya tidak terima kalau barangnya pecah.",
    "Permisi, paket saya statusnya gagal kirim.",
    "Min, tolong cek DM saya ya.",
    "Kurir tidak sopan saat antar barang.",
    "Kenapa ongkir ke tempat saya mahal sekali?",
    "Saya mau refund uang saya segera.",
    "Barang saya hancur lebur saat sampai."
]

def get_messy_address():
    """Membuat variasi alamat kotor/pendek"""
    r = random.random()
    addr = fake.address().replace('\n', ', ').replace(',,', ',').strip()
    
    if r < 0.2: return fake.city_name() # Kota only
    elif r < 0.5: return f"{fake.street_name()} No. {fake.building_number()}" # Jalan Pendek
    elif r < 0.7: return f"{fake.street_name()} No. {fake.building_number()}, {fake.city_name()}" # hampir lengkap
    else: return addr # Lengkap

def generate_training_data():
    training_data = []
    skipped_count = 0
    
    print(f"Sedang men-generate {NUM_SAMPLES} data latih...")

    pbar = tqdm(total=NUM_SAMPLES)
    while len(training_data) < NUM_SAMPLES:
        
        # Random logic agar sekitar 20% Data adalah NEGATIF 
        is_negative = random.random() < 0.2
        
        if is_negative:
            # Generate Data Negatif (Tanpa Entity)
            text = random.choice(NEGATIVE_TEMPLATES)
            entities = [] 
            
        else:
            # Generate Data Positif
            name = fake.name()
            address = get_messy_address()
            template = random.choice(POSITIVE_TEMPLATES)
            text = template.format(name=name, addr=address)
            
            # Augmentasi Lowercase
            if random.random() < 0.5:
                text = text.lower()
                name = name.lower()
                address = address.lower()

            entities = []
            start_name = text.find(name)
            if start_name != -1:
                entities.append((start_name, start_name + len(name), "PERSON"))
            
            start_addr = text.find(address)
            if start_addr != -1:
                entities.append((start_addr, start_addr + len(address), "ADDRESS"))

        # Validasi Alignment 
        doc = nlp.make_doc(text)
        valid_entities = []
        is_misaligned = False
        
        for start, end, label in entities:
            span = doc.char_span(start, end, label=label)
            if span is None:
                is_misaligned = True
                break
            else:
                valid_entities.append([start, end, label])
        
        # Simpan
        if not is_misaligned:
            training_data.append([text, {"entities": valid_entities}])
            pbar.update(1)
        else:
            skipped_count += 1

    pbar.close()
    
    output_path = "data/raw/backup_shipvue_dataset.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(training_data, f, indent=2)
        
    print(f"\n[SUKSES] Dataset dengan Negative Sampling tersimpan.")
    print(f"[INFO] Data Valid: {len(training_data)}")

if __name__ == "__main__":
    generate_training_data()