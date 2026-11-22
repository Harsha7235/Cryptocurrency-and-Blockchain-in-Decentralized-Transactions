# utils.py
import qrcode
from fpdf import FPDF
from cryptography.fernet import Fernet
import os, json
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
KEY_PATH = os.path.join(DATA_DIR, "secret.key")
CHAIN_PATH_ENC = os.path.join(DATA_DIR, "chain.enc")

# --- encryption helpers ---
def ensure_key():
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
    else:
        with open(KEY_PATH, "rb") as f:
            key = f.read()
    return key

def encrypt_data_bytes(b: bytes):
    key = ensure_key()
    f = Fernet(key)
    token = f.encrypt(b)
    with open(CHAIN_PATH_ENC, "wb") as fw:
        fw.write(token)
    return CHAIN_PATH_ENC

def decrypt_data_bytes():
    if not os.path.exists(CHAIN_PATH_ENC):
        return None
    with open(KEY_PATH, "rb") as f:
        key = f.read()
    f = Fernet(key)
    with open(CHAIN_PATH_ENC, "rb") as fr:
        token = fr.read()
    data = f.decrypt(token)
    return data

# --- QR & PDF helpers ---
def generate_qr(text: str, out_filename: str = None):
    if not out_filename:
        out_filename = os.path.join(DATA_DIR, f"qr_{int(datetime.now().timestamp())}.png")
    img = qrcode.make(text)
    img.save(out_filename)
    return out_filename

def export_blockchain_pdf(chain_list, out_filename: str = None):
    if not out_filename:
        out_filename = os.path.join(DATA_DIR, f"ledger_{int(datetime.now().timestamp())}.pdf")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, "Blockchain Ledger Export", ln=True)
    pdf.ln(4)
    for b in chain_list:
        pdf.cell(0, 7, f"Block #{b.get('index')}  Time: {b.get('timestamp')}", ln=True)
        pdf.multi_cell(0, 6, f"Hash: {b.get('hash')}")
        pdf.multi_cell(0, 6, f"PrevHash: {b.get('previous_hash')}")
        pdf.multi_cell(0, 6, f"Transactions: {json.dumps(b.get('transactions'), ensure_ascii=False)}")
        pdf.ln(3)
    pdf.output(out_filename)
    return out_filename

# --- persistence helpers (encrypted) ---
def save_encrypted_chain(chain_list):
    b = json.dumps(chain_list, ensure_ascii=False).encode()
    return encrypt_data_bytes(b)

def load_encrypted_chain():
    b = decrypt_data_bytes()
    if b is None:
        return None
    return json.loads(b.decode(), strict=False)

# small helper for timestamped filenames
def timestamped(prefix: str, ext: str):
    t = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(DATA_DIR, f"{prefix}_{t}.{ext}")
