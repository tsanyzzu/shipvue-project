import json
import random

# MOCK DATABASE
MOCK_DB_RESI = {
    "JP123456": {"status": "DELIVERED", "loc": "Surabaya", "receiver": "Budi"},
    "JP888999": {"status": "ON_PROCESS", "loc": "Gudang Jakarta", "receiver": "Siti"},
    "JP555666": {"status": "PENDING", "loc": "Drop Point Bandung", "receiver": "Andi"},
}

class ShipvueTools:
    """
    Class wrapper untuk tools. Menerima context (vault) jika diperlukan untuk operasi sensitif.
    """
    def __init__(self):
        self.context = {}

    def set_context(self, vault: dict):
        """Menyuntikkan data asli (unmasked) ke dalam tool"""
        self.context = vault

    def check_receipt_status(self, resi_number: str):
        """
        Mengecek status pengiriman paket berdasarkan nomor resi.
        """
        # Bersihkan input
        resi_clean = resi_number.strip().upper().replace(".", "")
        
        if "REDACTED" in resi_clean and self.context:
            # Cari apakah ada value asli di vault yang cocok (Simplifikasi)
            pass 

        data = MOCK_DB_RESI.get(resi_clean)
        
        if data:
            return {
                "resi": resi_clean,
                "status": data['status'],
                "current_location": data['loc'],
                "receiver_name": data['receiver'] 
            }
        else:
            return {"error": "Nomor resi tidak ditemukan (Format: JPxxxx)."}

shipvue_tools_instance = ShipvueTools()