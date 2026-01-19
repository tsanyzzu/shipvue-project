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
        Tugas utama Anda adalah membantu pelanggan dalam pelacakan resi dan memberikan informasi pengiriman secara akurat.
        
        Pedoman Operasional:
        1. Gunakan label sensor (seperti [PERSON_REDACTED] atau [NIK_REDACTED]) persis sesuai input yang diterima. Dilarang keras mencoba mendekripsi, menebak, atau memalsukan data di balik label tersebut.
        2. Gunakan label sensor apa adanya dalam pemanggilan fungsi/tools maupun komunikasi dengan pengguna.
        3. Tolak permintaan secara santun jika data yang diperlukan tidak memadai atau tidak lengkap.
        4. Prioritaskan bantuan pada pengecekan status paket dan detail logistik lainnya.
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
            clean_text, audit_logs = self.guardrail.scan(text)
            
            # Simulasi Construct Vault 
            vault = {}
            for log in audit_logs:
                # Mapping: [LABEL_REDACTED] -> Original Text
                # Contoh: [EMAIL_REDACTED] -> budi@gmail.com
                tag = f"[{log['label']}_REDACTED]"
                vault[tag] = log['original']

            return {
                "cleaned_text": clean_text,
                "vault": vault,
                "audit_logs": audit_logs
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
                "session_data": session_vault
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