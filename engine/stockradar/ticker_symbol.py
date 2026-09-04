from __future__ import annotations


def normalize_hose_ticker(value: object) -> str:
    """Normalize a HOSE ticker without dropping valid numeric characters."""
    return str(value or "").strip().upper()


def is_valid_hose_ticker(value: object) -> bool:
    """Return True for three-character HOSE equity symbols such as FPT, C32, HT1 and PC1."""
    ticker = normalize_hose_ticker(value)
    return (
        len(ticker) == 3
        and ticker.isascii()
        and ticker.isalnum()
        and any(character.isalpha() for character in ticker)
    )
