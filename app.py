# app.py
import streamlit as st
import os, json, time
from blockchain import Blockchain, Block
from wallet import create_keypair, export_wallet, import_wallet, sign_message
from utils import generate_qr, export_blockchain_pdf, save_encrypted_chain, load_encrypted_chain, timestamped, DATA_DIR
import pandas as pd

# ---------- Page config ----------
st.set_page_config(page_title="Ultimate Blockchain — Decentralized Transactions (CT Project)", layout="wide")

# ---------- Dark Mode Toggle (sidebar) ----------
if "dark" not in st.session_state:
    st.session_state.dark = False

def dark_css():
    st.markdown("""
    <style>
      .stApp { background-color: #0e1117; color: #f1f5f9; }
      .css-1d391kg, .css-145kmo2 { color: #f1f5f9 !important; }
      .stButton>button { background-color: #1f2937; color: #fff; }
    </style>
    """, unsafe_allow_html=True)

if st.sidebar.button("Toggle Dark / Light Mode"):
    st.session_state.dark = not st.session_state.dark
if st.session_state.dark:
    dark_css()

# ---------- Ensure data dir ----------
os.makedirs(DATA_DIR, exist_ok=True)

# ---------- Load or init blockchain ----------
if "bc" not in st.session_state:
    st.session_state.bc = Blockchain(difficulty=3)
    loaded = load_encrypted_chain()
    if loaded:
        try:
            st.session_state.bc.load_from_json(loaded)
        except Exception:
            # ignore load failure
            pass
bc = st.session_state.bc

# ---------- Wallet in session ----------
if "wallet" not in st.session_state:
    st.session_state.wallet = {}

st.sidebar.header("🔐 Wallet")
if st.sidebar.button("Create New Wallet"):
    priv, pub, addr = create_keypair()
    st.session_state.wallet = {"priv": priv, "pub": pub, "addr": addr}
    st.sidebar.success(f"Created wallet {addr}")

if st.sidebar.button("Show Wallet"):
    if st.session_state.wallet:
        st.sidebar.code(st.session_state.wallet.get("addr"))
    else:
        st.sidebar.info("No wallet created")

# Wallet Import / Export
st.sidebar.markdown("---")
st.sidebar.subheader("Wallet Import / Export")
if st.sidebar.button("Export Wallet"):
    if st.session_state.wallet:
        wallet_path = os.path.join(DATA_DIR, f"wallet_{st.session_state.wallet['addr']}.json")
        export_wallet(st.session_state.wallet, wallet_path)
        with open(wallet_path, "rb") as f:
            st.sidebar.download_button("Download Wallet JSON", f, file_name=os.path.basename(wallet_path))
    else:
        st.sidebar.info("No wallet available")

uploaded_wallet = st.sidebar.file_uploader("Import Wallet (JSON)", type=["json"])
if uploaded_wallet:
    try:
        data = json.load(uploaded_wallet)
        st.session_state.wallet = data
        st.sidebar.success("Wallet imported")
    except Exception as e:
        st.sidebar.error("Import failed: " + str(e))

# Node simulation (export/import chain)
st.sidebar.markdown("---")
st.sidebar.subheader("Node Sync (local)")
if st.sidebar.button("Export Chain JSON (for Node B)"):
    path = os.path.join(DATA_DIR, "chain_for_node.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bc.to_json(), f, ensure_ascii=False, indent=2)
    with open(path, "rb") as f:
        st.sidebar.download_button("Download chain JSON", f, file_name=os.path.basename(path))
uploaded_chain = st.sidebar.file_uploader("Load Chain JSON from another node", type=["json"])
if uploaded_chain:
    try:
        other = json.load(uploaded_chain)
        bc.load_from_json(other)
        st.sidebar.success("Loaded chain from uploaded node JSON")
    except Exception as e:
        st.sidebar.error("Load failed: " + str(e))

# Save / Load encrypted chain
st.sidebar.markdown("---")
if st.sidebar.button("Save Chain (encrypted)"):
    save_encrypted_chain(bc.to_json())
    st.sidebar.success("Encrypted chain saved")
if st.sidebar.button("Load Chain (encrypted)"):
    loaded = load_encrypted_chain()
    if loaded:
        bc.load_from_json(loaded)
        st.sidebar.success("Encrypted chain loaded")
    else:
        st.sidebar.info("No encrypted chain found")

# ---------- Top page ----------
st.title("🚀 Ultimate Blockchain — Decentralized Transactions (CT Project)")
st.markdown("Wallet, Transactions, Mining, NFT, Node-sync, QR/PDF receipts, encrypted ledger.")

# ---------- Tabs ----------
tabs = st.tabs(["Wallet & Balance","Make Transaction","Mine / Staking","Block Explorer","Search Tx","Analytics & Export","NFT Mint"])
tab_wallet, tab_tx, tab_mine, tab_explorer, tab_search, tab_analytics, tab_nft = tabs

# ---------- Tab: Wallet & Balance ----------
with tab_wallet:
    st.header("Wallet & Balance")
    if st.session_state.wallet:
        addr = st.session_state.wallet.get("addr")
        st.subheader("Address")
        st.code(addr)
        bal = bc.balances.get(addr, 0.0)
        st.metric("Balance", f"{bal:.2f} coins")
        if st.button("Show My Transactions"):
            history = []
            for b in bc.chain:
                for tx in b.transactions:
                    if tx.get("sender") == addr or tx.get("receiver") == addr:
                        history.append({"block": b.index, **tx})
            st.write(history)
    else:
        st.info("Create a wallet to get started (sidebar).")

# ---------- Tab: Make Transaction ----------
with tab_tx:
    st.header("Create / Submit Transaction")
    default_sender = st.session_state.wallet.get("addr","")
    sender = st.text_input("Sender address", value=default_sender)
    receiver = st.text_input("Receiver address")
    amount = st.number_input("Amount", min_value=0.0, step=0.01, value=1.0)
    fee = st.number_input("Fee (miner tip)", min_value=0.0, step=0.01, value=0.10)
    tx_type = st.selectbox("Transaction Type", ["TRANSFER", "NFT"])
    nft_token = ""
    nft_meta = ""
    if tx_type == "NFT":
        nft_token = st.text_input("NFT Token ID (unique)")
        nft_meta = st.text_area("NFT Metadata (optional)")

    if st.button("Add Transaction to Pool"):
        if not sender or not receiver:
            st.error("Sender and receiver required")
        else:
            meta = {"token_id": nft_token} if tx_type=="NFT" else {}
            if tx_type == "NFT" and nft_meta:
                meta["meta"] = nft_meta
            tx = bc.add_transaction(sender, receiver, amount, fee=fee, tx_type=tx_type, metadata=meta)
            st.success("Transaction queued")
            tx_json = json.dumps(tx, ensure_ascii=False)
            qrpath = generate_qr(tx_json, out_filename=timestamped("tx_qr","png"))
            st.image(qrpath, width=220)
            pdfpath = export_blockchain_pdf([{"index":"receipt","timestamp":time.time(),"transactions":[tx],"previous_hash":"","hash":""}], out_filename=timestamped("receipt","pdf"))
            with open(pdfpath,"rb") as f:
                st.download_button("Download Tx PDF", f, file_name=os.path.basename(pdfpath))
    st.subheader("Pending Transactions")
    st.write(bc.pending_transactions)

# ---------- Tab: Mine / Staking ----------
with tab_mine:
    st.header("Mine Block & Stake")
    miner_addr = st.text_input("Miner address", value=st.session_state.wallet.get("addr",""))
    reward = st.number_input("Block reward", min_value=0.0, step=1.0, value=10.0)
    stake_addr = st.text_input("Stake address (optional)", value=st.session_state.wallet.get("addr",""))
    stake_amount = st.number_input("Stake amount", min_value=0.0, step=1.0, value=0.0)

    if st.button("Stake Tokens"):
        if stake_amount > 0 and stake_addr:
            bc.stake_tokens(stake_addr, stake_amount)
            st.success(f"Staked {stake_amount} tokens for {stake_addr}")
        else:
            st.info("Provide stake address and amount")

    if st.button("Mine Block (Proof-of-Work)"):
        if not miner_addr:
            st.error("Provide miner address")
        else:
            # mining animation
            with st.spinner("Mining in progress (simulated)..."):
                progress = st.progress(0)
                for i in range(100):
                    time.sleep(0.02)
                    progress.progress(i + 1)
                block = bc.mine_block(miner_addr, reward=reward)
            if block:
                st.success(f"Block #{block.index} mined by {block.forger}")
                st.json(block.to_dict())
            else:
                st.info("No pending transactions to mine")

    st.subheader("Stakes")
    st.write(bc.stakes)

# ---------- Tab: Block Explorer ----------
with tab_explorer:
    st.header("Block Explorer")
    chain_json = bc.to_json()
    if chain_json:
        df = pd.DataFrame(chain_json)
        # show key columns
        if not df.empty:
            st.dataframe(df[["index","timestamp","forger","hash","previous_hash"]])
            idx = st.number_input("Open block index", min_value=0, max_value=len(bc.chain)-1, value=0)
            st.write(bc.chain[int(idx)].to_dict())
    else:
        st.info("No blocks found")

    # NFT registry
    st.subheader("NFT Registry")
    nft_registry = bc.balances.get("_nft_registry", {})
    st.write(nft_registry)

# ---------- Tab: Search Transaction ----------
with tab_search:
    st.header("Search Transaction by field")
    q = st.text_input("Search string (address, amount, tx id, token id)")
    if st.button("Search"):
        results = []
        for b in bc.chain:
            for tx in b.transactions:
                tx_text = json.dumps(tx, ensure_ascii=False)
                if q and q in tx_text:
                    results.append({"block": b.index, **tx})
        st.write(results)

# ---------- Tab: Analytics & Export ----------
with tab_analytics:
    st.header("Analytics & Export")
    total_blocks = len(bc.chain)
    total_tx = sum(len(b.transactions) for b in bc.chain)
    st.metric("Total Blocks", total_blocks)
    st.metric("Total Transactions", total_tx)

    txs_per_block = [len(b.transactions) for b in bc.chain]
    if txs_per_block:
        df2 = pd.DataFrame({"block":[b.index for b in bc.chain], "txs":txs_per_block})
        st.line_chart(df2.set_index("block"))

    if st.button("Export Encrypted Chain (save)"):
        save_encrypted_chain(bc.to_json())
        st.success("Encrypted chain saved (data/chain.enc)")

    if st.button("Export Ledger as PDF"):
        fname = export_blockchain_pdf(bc.to_json())
        with open(fname,"rb") as f:
            st.download_button("Download Ledger PDF", f, file_name=os.path.basename(fname))

# ---------- Tab: NFT Mint ----------
with tab_nft:
    st.header("Mint an NFT")
    owner = st.text_input("Owner Wallet Address", value=st.session_state.wallet.get("addr",""))
    token_id = st.text_input("NFT Token ID")
    token_meta = st.text_area("NFT Metadata (optional)")
    if st.button("Mint NFT"):
        if not owner or not token_id:
            st.error("Owner and token ID required")
        else:
            tx = bc.mint_nft(owner, token_id, meta=token_meta)
            st.success("NFT mint tx queued")
            st.json(tx)

# ---------- Footer ----------
st.markdown("---")
st.caption("Ultimate Blockchain Demo — features: wallet, txs, fees, mining, NFT, encrypted save/load, node sync via JSON export/import.")
