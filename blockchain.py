# blockchain.py
import time
import json
import hashlib
import random
import uuid
from typing import List, Dict

class Block:
    def __init__(self, index:int, timestamp:float, transactions:List[Dict], previous_hash:str, nonce:int=0, forger:str=None):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.forger = forger
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "forger": self.forger
        }
        block_string = json.dumps(block_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "forger": self.forger,
            "hash": self.hash
        }

class Blockchain:
    def __init__(self, difficulty:int=3):
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        self.difficulty = difficulty
        self.stakes: Dict[str, float] = {}
        self.balances: Dict[str, float] = {}      # simple balance map
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(0, time.time(), [], "0", nonce=0, forger="network")
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    # ---- transaction (with fee support + NFT support) ----
    def add_transaction(self, sender: str, receiver: str, amount: float, fee: float = 0.0, tx_type: str = "TRANSFER", metadata: dict = None):
        tx = {
            "id": str(uuid.uuid4()),
            "sender": sender,
            "receiver": receiver,
            "amount": float(amount),
            "fee": float(fee),
            "type": tx_type,      # TRANSFER or NFT
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        self.pending_transactions.append(tx)
        # ensure accounts exist
        self.balances.setdefault(sender, 0.0)
        self.balances.setdefault(receiver, 0.0)
        return tx

    # ---- simple NFT mint helper (creates NFT tx, fee 0) ----
    def mint_nft(self, owner: str, token_id: str, meta: dict = None):
        metadata = {"token_id": token_id}
        if meta:
            metadata["meta"] = meta
        return self.add_transaction("NFT_SYSTEM", owner, 0.0, fee=0.0, tx_type="NFT", metadata=metadata)

    # ---- proof of work ----
    def proof_of_work(self, block: Block) -> str:
        block.nonce = 0
        computed_hash = block.compute_hash()
        target = "0" * self.difficulty
        while not computed_hash.startswith(target):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return computed_hash

    # ---- choose forger (PoS-like weighted random) ----
    def choose_forger(self):
        if not self.stakes:
            return None
        total = sum(self.stakes.values())
        if total <= 0:
            return None
        pick = random.uniform(0, total)
        current = 0.0
        for addr, stake in self.stakes.items():
            current += stake
            if current >= pick:
                return addr
        return None

    # ---- stake tokens (simple) ----
    def stake_tokens(self, address: str, amount: float):
        self.stakes.setdefault(address, 0.0)
        self.stakes[address] += float(amount)
        self.balances.setdefault(address, 0.0)
        self.balances[address] -= float(amount)

    # ---- mine block: rewards + fees distribution + NFT registry update ----
    def mine_block(self, miner_address: str, reward: float = 10.0):
        if not self.pending_transactions:
            return None
        last_block = self.chain[-1]
        forger = self.choose_forger() or miner_address
        block = Block(index=last_block.index + 1,
                      timestamp=time.time(),
                      transactions=self.pending_transactions.copy(),
                      previous_hash=last_block.hash,
                      nonce=0,
                      forger=forger)
        block.hash = self.proof_of_work(block)
        self.chain.append(block)

        total_fees = 0.0
        for tx in block.transactions:
            s = tx["sender"]
            r = tx["receiver"]
            amt = float(tx.get("amount", 0.0))
            fee = float(tx.get("fee", 0.0))
            total_fees += fee
            self.balances.setdefault(s, 0.0)
            self.balances.setdefault(r, 0.0)
            # sender pays both amount and fee (simple model)
            self.balances[s] -= (amt + fee)
            self.balances[r] += amt
            # NFT handling: register ownership
            if tx.get("type") == "NFT":
                token_id = tx.get("metadata", {}).get("token_id")
                if token_id:
                    self.balances.setdefault("_nft_registry", {})
                    self.balances["_nft_registry"][token_id] = r

        # reward to forger includes fees
        self.balances.setdefault(forger, 0.0)
        self.balances[forger] += float(reward) + total_fees

        self.pending_transactions = []
        return block

    # ---- chain validation ----
    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            prev = self.chain[i - 1]
            curr = self.chain[i]
            if curr.previous_hash != prev.hash:
                return False
            if curr.compute_hash() != curr.hash:
                return False
            if not curr.hash.startswith("0" * self.difficulty):
                return False
        return True

    # ---- helper to convert to/from JSON for save/load/sync ----
    def to_json(self):
        return [b.to_dict() for b in self.chain]

    def load_from_json(self, chain_list):
        self.chain = []
        for b in chain_list:
            block = Block(index=b["index"],
                          timestamp=b["timestamp"],
                          transactions=b["transactions"],
                          previous_hash=b["previous_hash"],
                          nonce=b.get("nonce", 0),
                          forger=b.get("forger"))
            block.hash = b.get("hash", block.compute_hash())
            self.chain.append(block)
