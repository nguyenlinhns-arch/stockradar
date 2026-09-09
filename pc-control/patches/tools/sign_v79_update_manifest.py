#!/usr/bin/env python3
"""Offline signer for ThayLinh PC Control update-feed v2.

This utility performs no network access. It signs only the canonical JSON value
stored in the input file using an ECDSA P-256 private key. Production private
keys must never be committed to the repository or copied into PC Control data.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

SCHEMA = "thaylinh.pc.update-feed.v2"
KEY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def _validate_canonical_value(value: Any, path: str = "signed") -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise ValueError(f"floats are forbidden in signed metadata: {path}")
    if isinstance(value, str):
        try:
            value.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(f"non-ASCII signed string is forbidden: {path}") from exc
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_canonical_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"non-string object key: {path}")
            try:
                key.encode("ascii")
            except UnicodeEncodeError as exc:
                raise ValueError(f"non-ASCII object key: {path}") from exc
            _validate_canonical_value(item, f"{path}.{key}")
        return
    raise ValueError(f"unsupported signed JSON type at {path}: {type(value).__name__}")


def canonical_bytes(signed: dict[str, Any]) -> bytes:
    _validate_canonical_value(signed)
    return json.dumps(
        signed,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def load_p256_private_key(path: pathlib.Path):
    raw = path.read_bytes()
    key = serialization.load_pem_private_key(raw, password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
        raise ValueError("publisher key must be an unencrypted ECDSA P-256 PEM private key")
    return key


def sign_p1363(key: ec.EllipticCurvePrivateKey, data: bytes) -> bytes:
    der = key.sign(data, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    if len(raw) != 64:
        raise ValueError("unexpected P-256 signature length")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signed-json", required=True, type=pathlib.Path)
    parser.add_argument("--private-key", required=True, type=pathlib.Path)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    if not KEY_ID_RE.fullmatch(args.key_id):
        raise ValueError("invalid key id")

    source = json.loads(args.signed_json.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise ValueError("signed metadata must be a JSON object")

    data = canonical_bytes(source)
    key = load_p256_private_key(args.private_key)
    signature = sign_p1363(key, data)
    envelope = {
        "schema": SCHEMA,
        "key_id": args.key_id,
        "signed": source,
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    encoded = (json.dumps(envelope, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)

    print(f"signed_sha256={hashlib.sha256(data).hexdigest()}")
    print(f"envelope_sha256={hashlib.sha256(encoded).hexdigest()}")
    print(f"signature_bytes={len(signature)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
