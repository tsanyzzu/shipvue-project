import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types 

# Path Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from src.guardrails.pii_guardrail import PIIGuardrail
from src.core.tools import shipvue_tools_instance

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("ShipvueADK")

load_dotenv()

class ShipvueAgent:
    """
    Implementasi Agent menggunakan Google ADK Framework.
    """

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.error("GOOGLE_API_KEY Missing!")

        # Inisialisasi Tools
        self.tools_instance = shipvue_tools_instance
        self.my_tools = [self.tools_instance.check_receipt_status]

        # Inisialisasi Internal Guardrail 
        self.guardrail = PIIGuardrail()

        # System Prompt 
        self.system_prompt = """
        Identitas Anda adalah Shipvue, asisten AI resmi dari perusahaan ekspedisi Shipi. 
        PROTOKOL KEAMANAN (PRIORITAS UTAMA):
        1. User data telah disensor menjadi tag seperti [PERSON_REDACTED], [ADDRESS_REDACTED].
        2. GUNAKAN TAG TERSEBUT APA ADANYA. JANGAN menebak isi aslinya.
        
        PANDUAN INTERAKSI:
        1. JIKA USER BERTANYA TUGAS (Cek Resi/Ongkir):
           - Pastikan data lengkap (Nomor Resi).
           - Jika lengkap, panggil tool `check_receipt_status`.
           - Jika tidak lengkap, minta data kekurangannya dengan sopan.
           
        2. JIKA USER BASA-BASI (Sapaan/Terima Kasih/Penutup):
           - JANGAN meminta data resi.
           - Balaslah dengan ramah, singkat, dan natural.
           - Contoh: "Sama-sama! Senang bisa membantu.", "Halo! Ada yang bisa dibantu?"
           
        3. GAYA BAHASA:
           - Gunakan Bahasa Indonesia yang sopan.
           - Hindari pengulangan kalimat "Mohon maaf" jika tidak ada error.
        """

        # Inisialisasi Google ADK Agent
        self.adk_agent = Agent(
            model='gemini-2.5-flash',
            name='shipvue_agent',
            instruction=self.system_prompt,
            tools=self.my_tools
        )

        # Setup Execution Runner
        self.app_name = "shipvue_app"
        self.runner = InMemoryRunner(
            agent=self.adk_agent,
            app_name=self.app_name
        )
        
        # Session Configuration
        self.session_id = "user_session_v1"
        self.user_id = "demo_user"
        self.session_ready = False

    async def ensure_session(self):
        """Memastikan session terbentuk sebelum chat dimulai"""
        if not self.session_ready:
            try:
                # Coba create session 
                await self.runner.session_service.create_session(
                    app_name=self.app_name, 
                    session_id=self.session_id,
                    user_id=self.user_id
                )
                logger.info(f"Session Created: {self.session_id}")
            except Exception as e:
                # Handle jika session sudah ada
                logger.info(f"Session info: {str(e)}")
            
            self.session_ready = True

    def call_guardrail_internal(self, text: str):
        """
        Memanggil PIIGuardrail lokal dan mengembalikan format dict (cleaned_text & vault).
        """
        try:
            # Scan menggunakan class PIIGuardrail 
            clean_text, audit_logs, perf_metrics = self.guardrail.scan(text)
            
            # Vault 
            vault = {}
            for log in audit_logs:
                unique_tag = log.get('tag')  # Ambil tag unik ([PERSON_REDACTED]_2)
                original_text = log.get('original')

                if unique_tag and original_text:
                    vault[unique_tag] = original_text

            return {
                "cleaned_text": clean_text,
                "vault": vault,
                "audit_logs": audit_logs,
                "performance": perf_metrics 
            }
        
        except Exception as e:
            logger.error(f"Guardrail Error: {e}")
            return {"cleaned_text": text, "vault": {}, "audit_logs": []} # return text asli jika error

    async def chat(self, user_message: str):
        """
        Main Pipeline: Guardrail -> Inject Context -> ADK Runner -> Return
        """
        # Guardrail Process
        guard_data = self.call_guardrail_internal(user_message)
        cleaned_text = guard_data.get("cleaned_text", user_message)
        session_vault = guard_data.get("vault", {})
        audit_logs = guard_data.get("audit_logs", [])

        # Inject Context
        self.tools_instance.set_context(session_vault)

        reply_text = ""
        try:
            await self.ensure_session()
            # Bungkus pesan untuk ADK
            msg_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=cleaned_text)]
            )

            logger.info(f" Running ADK Runner... Input Sanitized: {cleaned_text}")

            # Run ADK Async
            async for event in self.runner.run_async(
                session_id=self.session_id,
                user_id=self.user_id,
                new_message=msg_content
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            reply_text += part.text
            
            if not reply_text:
                reply_text = "Maaf, tidak ada respon (Empty Response)."

        except Exception as e:
            reply_text = f"Error ADK Execution: {str(e)}"
            logger.error(reply_text)

        # Return Data 
        return {
            "reply": reply_text,
            "audit_logs": audit_logs, 
            "debug_info": {
                "original": user_message,
                "final_clean": cleaned_text,
                "session_data": session_vault,
                "performance": guard_data.get("performance", {})
            }
        }

# wrapper sync
def run_agent_sync(agent, message):
    return asyncio.run(agent.chat(message))

# Test Manual
# if __name__ == "__main__":
#     agent = ShipvueAgent()
#     res = asyncio.run(agent.chat("Paket atas nama Siti Aminah rusak parah pas sampai di Surabaya. Saya juga mau cek resi JP888999 dong."))
#     print("Reply:", res['reply'])
#     print("Debug:", res['debug_info'])