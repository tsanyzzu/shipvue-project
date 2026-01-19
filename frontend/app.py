import streamlit as st
import asyncio
import sys
import os
import time

# Path Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from services.shipvue_agent.src.core.agent import ShipvueAgent
except ImportError as e:
    st.error(f"Gagal memuat Backend Agent. Error: {e}")
    st.stop()

# PAGE CONFIG 
st.set_page_config(
    page_title="Shipvue Support AI",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CUSTOM CSS
st.markdown("""
<style>
    .stChatMessage {border-radius: 10px; padding: 10px;}
    .stMarkdown {font-family: 'Inter', sans-serif;}
    h1 {color: #004e98;}
</style>
""", unsafe_allow_html=True)

# INIT STATE 
if "messages" not in st.session_state:
    st.session_state.messages = []

# Load Agent sekali saja (Singleton Pattern)
if "agent" not in st.session_state:
    with st.spinner("Menghubungkan ke Neural Engine & Guardrails..."):
        try:
            st.session_state.agent = ShipvueAgent()
            st.success("Sistem Siap!")
            time.sleep(1) # pesan sukses tampil sebentar
            st.rerun()
        except Exception as e:
            st.error(f"Critical Error: {e}")
            st.stop()

# SIDEBAR (DEBUG & AUDIT) 
with st.sidebar:
    st.title("Sidebar Debug & Audit")
    if "last_log" in st.session_state:
        log = st.session_state.last_log
        perf = log['debug_info'].get('performance', {})

        st.subheader("System Performance")

        # kolom metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Latency", f"{perf.get('total_latency_ms', 0)} ms")
            st.metric("NER Latency", f"{perf.get('ner_latency_ms', 0)} ms")
            st.metric("CPU Usage", f"{perf.get('ner_cpu_percent', 0)}%")
        with col2:
            st.metric("Regex Latency", f"{perf.get('regex_latency_ms', 0)} ms")
            st.metric("Memory Usage", f"{perf.get('ner_memory_mb', 0)} MB")
            
        st.divider()
    
    # Placeholder untuk log terakhir
    if "last_log" in st.session_state:
        log = st.session_state.last_log
        
        st.subheader("Input Analysis")
        st.text_area("Original Input", log['debug_info']['original'], height=70, disabled=True)
        st.text_area("Sanitized Input (To LLM)", log['debug_info']['final_clean'], height=70, disabled=True)
        
        st.subheader("Redacted Data")
        if log['audit_logs']:
            st.dataframe(log['audit_logs'])
            st.info(f"Terdeteksi {len(log['audit_logs'])} data sensitif.")
        else:
            st.success("Tidak ada PII terdeteksi.")
            
        st.subheader("Session Vault (Secure Context)")
        st.json(log['debug_info'].get('session_data', {}))

# CHAT INTERFACE 
st.title("Shipvue Support AI")
st.caption("Asisten Virtual dengan Proteksi Privasi (Regex + NER)")

# Render History Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle Input User
if prompt := st.chat_input("Ketik keluhan atau cek resi (Contoh: Cek resi JP888999)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Proses di Backend
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("▌ *Sedang mengetik...*")
        
        try:
            # RUN ASYNC AGENT
            response_data = asyncio.run(st.session_state.agent.chat(prompt))
            reply_text = response_data['reply']
            message_placeholder.markdown(reply_text)
            
            # Update Session State untuk Sidebar
            st.session_state.last_log = response_data
            
            # Simpan ke history
            st.session_state.messages.append({"role": "assistant", "content": reply_text})
            
            # Force Rerun agar Sidebar terupdate otomatis
            st.rerun()
            
        except Exception as e:
            message_placeholder.error(f"Terjadi kesalahan sistem: {str(e)}")