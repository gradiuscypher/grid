"""Canonicalization rules per builtin entity type (ARCHITECTURE §3: `canonical_value`
is normalized for structural dedup — lowercased domain, packed IP, …). No spec exists
for custom entity types yet, so they fall through to a plain-strip default.
"""

import ipaddress
from urllib.parse import urlsplit, urlunsplit


def canonicalize(entity_type_name: str, value: str) -> str:
    value = value.strip()
    if entity_type_name in ("domain", "hostname", "username", "hash"):
        return value.lower()
    if entity_type_name == "email":
        # Local-part case sensitivity is technically per-RFC, but treating email
        # as case-insensitive for dedup purposes matches how virtually every
        # real mail provider behaves.
        return value.lower()
    if entity_type_name in ("ipv4", "ipv6"):
        return str(ipaddress.ip_address(value))
    if entity_type_name == "cidr":
        return str(ipaddress.ip_network(value, strict=False))
    if entity_type_name == "asn":
        digits = value.upper().removeprefix("AS").strip()
        return f"AS{int(digits)}"
    if entity_type_name == "url":
        parts = urlsplit(value)
        return urlunsplit(
            (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, "")
        )
    return value
