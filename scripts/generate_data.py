import json
import random
from faker import Faker
from tqdm import tqdm

# Inisialisasi Faker 
fake = Faker('id_ID')
Faker.seed(42) 

NUM_SAMPLES = 150 

# Template kalimat w/ {entity} 
TEMPLATES = [
    "Paket saya atas nama {name} yang dikirim ke {addr} kok belum sampai?",
    "Tolong cek resi untuk penerima {name} di {addr}.",
    "Kurir bilang alamat {addr} tidak ditemukan, padahal {name} ada di rumah.",
    "Saya {name}, mau komplain pengiriman ke {addr} yang rusak.",
    "Apakah bisa jemput paket dari {addr} atas nama {name}?",
    "Alamat tujuan di {addr} apakah tercover layanan Shipvue? Penerima {name}.",
    "Barang milik {name} di {addr} statusnya stuck di gudang.",
    "Halo admin, saya {name} dari {addr}, mau tanya ongkir.",
]

def generate_training_data():
    training_data = []
    
    print(f"Membuat {NUM_SAMPLES} data latih sintetis...")

    for _ in tqdm(range(NUM_SAMPLES)):
        # Generate Entity Palsu
        name = fake.name()
        address = fake.address().replace('\n', ', ')
        template = random.choice(TEMPLATES)
        text = template.format(name=name, addr=address)
        
        entities = []
        
        # Cari posisi nama
        start_name = text.find(name)
        if start_name != -1:
            end_name = start_name + len(name)
            entities.append((start_name, end_name, "PERSON"))
            
        # Cari posisi alamat
        start_addr = text.find(address)
        if start_addr != -1:
            end_addr = start_addr + len(address)
            entities.append((start_addr, end_addr, "ADDRESS"))
            
        # JSON Format: [text, {"entities": [[start, end, label], ...]}]
        training_data.append([text, {"entities": entities}])

    output_path = "data/raw/shipvue_dataset.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(training_data, f, indent=2)
        
    print(f"\n[SUKSES] Dataset tersimpan di: {output_path}")
    print(f"Preview: {training_data[0]}")

if __name__ == "__main__":
    generate_training_data()