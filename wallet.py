# wallet.py
import hashlib
import json
import os
import binascii
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes

def create_keypair():
    """
    Create ECDSA keypair (SECP256R1). Returns (priv_pem_str, pub_pem_str, address)
    Address is SHA256 of public key bytes (shortened).
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption())

    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)

    # create an address (sha256 of public key bytes, shorten)
    addr = hashlib.sha256(pub_pem).hexdigest()[:32]
    return priv_pem.decode(), pub_pem.decode(), addr

# sign message with private key PEM (returns hex signature)
def sign_message(priv_pem: str, message: bytes) -> str:
    private_key = serialization.load_pem_private_key(priv_pem.encode(), password=None)
    sig = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    return binascii.hexlify(sig).decode()

# export / import helpers
def export_wallet(wallet: dict, out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(wallet, f, ensure_ascii=False, indent=2)
    return out_path

def import_wallet(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
