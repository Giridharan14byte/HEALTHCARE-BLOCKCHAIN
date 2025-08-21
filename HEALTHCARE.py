
from __future__ import annotations
import hashlib
import datetime as dt
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


# ----------------------------- Blockchain Core ----------------------------- #

@dataclass
class Block:
    index: int
    timestamp: str
    patient_id: str
    record: Dict[str, Any]
    previous_hash: str
    hash: str

    @staticmethod
    def compute_hash(index: int, timestamp: str, patient_id: str,
                     record: Dict[str, Any], previous_hash: str) -> str:
        """Compute a SHA-256 hash of the block contents.
        Sort keys when serializing `record` to keep hashes stable.
        """
        payload = {
            "index": index,
            "timestamp": timestamp,
            "patient_id": patient_id,
            "record": record,
            "previous_hash": previous_hash,
        }
        # Ensure deterministic serialization
        block_string = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    @classmethod
    def create(cls, index: int, patient_id: str, record: Dict[str, Any],
               previous_hash: str) -> "Block":
        timestamp = dt.datetime.now().isoformat(timespec="seconds")
        block_hash = cls.compute_hash(index, timestamp, patient_id, record, previous_hash)
        return cls(index=index, timestamp=timestamp, patient_id=patient_id,
                   record=record, previous_hash=previous_hash, hash=block_hash)


class Blockchain:
    def __init__(self) -> None:
        self.chain: List[Block] = [self._create_genesis_block()]
        # Simple index for quick patient lookups: patient_id -> indices in chain
        self._patient_index: Dict[str, List[int]] = {}

    def _create_genesis_block(self) -> Block:
        return Block.create(0, patient_id="0", record={"note": "Genesis Block"}, previous_hash="0")

    # ----------------------------- Write Path ----------------------------- #
    def add_record(self, patient_id: str, record: Dict[str, Any]) -> Block:
        """Append a new patient record as a block."""
        latest_hash = self.chain[-1].hash
        new_block = Block.create(index=len(self.chain), patient_id=patient_id,
                                 record=record, previous_hash=latest_hash)
        self.chain.append(new_block)
        self._patient_index.setdefault(patient_id, []).append(new_block.index)
        return new_block

    # ----------------------------- Read Path ------------------------------ #
    def get_all_records(self, patient_id: str) -> List[Block]:
        """Retrieve all blocks that belong to a given patient (chronological)."""
        indices = self._patient_index.get(patient_id)
        if not indices:
            return []
        return [self.chain[i] for i in indices]

    def get_latest_record(self, patient_id: str) -> Optional[Block]:
        blocks = self.get_all_records(patient_id)
        return blocks[-1] if blocks else None

    # --------------------------- Chain Integrity -------------------------- #
    def validate(self) -> (bool, Optional[str]):
        """Validate the entire chain, returning (is_ok, error_message)."""
        for i in range(1, len(self.chain)):
            prev = self.chain[i - 1]
            cur = self.chain[i]
            # Check linkage
            if cur.previous_hash != prev.hash:
                return False, f"Broken link at index {i}: previous_hash mismatch"
            # Recompute hash to detect tampering
            recalculated = Block.compute_hash(cur.index, cur.timestamp, cur.patient_id, cur.record, cur.previous_hash)
            if cur.hash != recalculated:
                return False, f"Hash mismatch at index {i}: data was modified"
        return True, None

    # --------------------------- Utility / Print -------------------------- #
    @staticmethod
    def _print_block(block: Block) -> None:
        print("Index:         ", block.index)
        print("Timestamp:     ", block.timestamp)
        print("Patient ID:    ", block.patient_id)
        print("Record:        ", json.dumps(block.record, ensure_ascii=False))
        print("Hash:          ", block.hash)
        print("Previous Hash: ", block.previous_hash)
        print("-" * 60)

    def print_chain(self) -> None:
        for b in self.chain:
            self._print_block(b)


# ------------------------------- CLI Program ------------------------------ #

def menu() -> None:
    bc = Blockchain()

    while True:
        print("\n===== Healthcare Blockchain Menu =====")
        print("1) Add patient record")
        print("2) Retrieve ALL records by Patient ID")
        print("3) Retrieve LATEST record by Patient ID")
        print("4) Print full chain")
        print("5) Validate blockchain")
        print("6) (Demo) Tamper with a block")
        print("7) Exit")

        choice = input("Enter choice (1-7): ").strip()

        if choice == "1":
            pid = input("Patient ID: ").strip()
            diagnosis = input("Diagnosis: ").strip()
            treatment = input("Treatment: ").strip()
            notes = input("Notes (optional): ").strip()
            record = {"diagnosis": diagnosis, "treatment": treatment}
            if notes:
                record["notes"] = notes
            new_block = bc.add_record(pid, record)
            print("Record added in block index:", new_block.index)

        elif choice == "2":
            pid = input("Patient ID to retrieve: ").strip()
            ok, err = bc.validate()
            if not ok:
                print("WARNING: Chain invalid ?", err)
            blocks = bc.get_all_records(pid)
            if not blocks:
                print("No records found for:", pid)
            else:
                print(f"\nAll records for patient {pid}:")
                for b in blocks:
                    bc._print_block(b)

        elif choice == "3":
            pid = input("Patient ID to retrieve latest: ").strip()
            ok, err = bc.validate()
            if not ok:
                print("WARNING: Chain invalid ?", err)
            latest = bc.get_latest_record(pid)
            if not latest:
                print("No records found for:", pid)
            else:
                print(f"\nLatest record for patient {pid}:")
                bc._print_block(latest)

        elif choice == "4":
            bc.print_chain()

        elif choice == "5":
            ok, err = bc.validate()
            print("Blockchain valid:", ok)
            if err:
                print("Reason:", err)

        elif choice == "6":
            try:
                idx = int(input("Enter block index to tamper (>=1): ").strip())
                if idx <= 0 or idx >= len(bc.chain):
                    print("Invalid index.")
                    continue
                field = input("Field to change (diagnosis/treatment/notes): ").strip().lower()
                value = input("New value: ").strip()
                if field not in {"diagnosis", "treatment", "notes"}:
                    print("Unsupported field.")
                    continue
                # Mutate the stored dict directly (simulating an attack)
                bc.chain[idx].record[field] = value
                print(f"Tampered block {idx}. Now validate to see failure.")
            except ValueError:
                print("Please enter a valid integer index.")

        elif choice == "7":
            print("Exiting. Bye!")
            break
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    menu()
