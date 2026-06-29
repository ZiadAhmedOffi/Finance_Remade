import base64
import hashlib
import json
import time
from urllib.parse import urlsplit, urlunsplit

import jwt
from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed


def compute_jkt(jwk):
    if not isinstance(jwk, dict):
        raise AuthenticationFailed("DPoP proof missing JWK.")

    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise AuthenticationFailed("Unsupported DPoP key type.")

    if jwk.get("d"):
        raise AuthenticationFailed("DPoP proof JWK must not include private key material.")

    required_fields = {
        "crv": jwk.get("crv"),
        "kty": jwk.get("kty"),
        "x": jwk.get("x"),
        "y": jwk.get("y"),
    }
    if not all(required_fields.values()):
        raise AuthenticationFailed("DPoP proof JWK is incomplete.")

    json_jwk = json.dumps(required_fields, separators=(",", ":"), sort_keys=True)
    hash_digest = hashlib.sha256(json_jwk.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(hash_digest).decode("utf-8").replace("=", "")


def compute_token_ath(raw_token):
    digest = hashlib.sha256(raw_token.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").replace("=", "")


def normalize_htu(url):
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        raise AuthenticationFailed("DPoP proof URL is invalid.")

    path = parsed.path or "/"
    netloc = parsed.netloc.lower()

    if parsed.scheme.lower() == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]
    if parsed.scheme.lower() == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]

    return urlunsplit((parsed.scheme.lower(), netloc, path, "", ""))


def validate_dpop_proof(request, proof_jwt, *, expected_jkt=None, expected_ath=None):
    if not proof_jwt:
        raise AuthenticationFailed("DPoP proof is required for this request.")

    try:
        unverified_header = jwt.get_unverified_header(proof_jwt)
        if unverified_header.get("typ") != "dpop+jwt":
            raise AuthenticationFailed("Invalid DPoP proof type.")
        if unverified_header.get("alg") != "ES256":
            raise AuthenticationFailed("Invalid DPoP proof algorithm.")

        jwk = unverified_header.get("jwk")
        actual_jkt = compute_jkt(jwk)
        public_key = jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(jwk))

        leeway = int(getattr(settings, "SIMPLE_JWT", {}).get("LEEWAY", 30))
        max_age = int(getattr(settings, "DPOP_PROOF_MAX_AGE_SECONDS", 300))
        decoded_proof = jwt.decode(
            proof_jwt,
            public_key,
            algorithms=["ES256"],
            options={"require": ["jti", "htm", "htu", "iat"], "verify_signature": True},
            leeway=leeway,
        )

        now = int(time.time())
        issued_at = int(decoded_proof["iat"])
        if issued_at > now + leeway:
            raise AuthenticationFailed("DPoP proof is not yet valid.")
        if issued_at < now - max_age:
            raise AuthenticationFailed("DPoP proof is too old.")

        if decoded_proof.get("htm") != request.method.upper():
            raise AuthenticationFailed("DPoP proof method mismatch.")

        expected_htu = normalize_htu(request.build_absolute_uri(request.path))
        actual_htu = normalize_htu(decoded_proof.get("htu", ""))
        if actual_htu != expected_htu:
            raise AuthenticationFailed("DPoP proof URL mismatch.")

        if expected_jkt and actual_jkt != expected_jkt:
            raise AuthenticationFailed("DPoP proof key mismatch with bound token.")

        if expected_ath:
            if decoded_proof.get("ath") != expected_ath:
                raise AuthenticationFailed("DPoP proof access-token hash mismatch.")

        cache_key = f"dpop:jti:{actual_jkt}:{decoded_proof['jti']}"
        if not cache.add(cache_key, "1", timeout=max_age):
            raise AuthenticationFailed("DPoP proof replay detected.")

        return {"claims": decoded_proof, "jkt": actual_jkt}
    except AuthenticationFailed:
        raise
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationFailed("DPoP proof has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationFailed("Invalid DPoP proof.") from exc
    except ValueError as exc:
        raise AuthenticationFailed("Invalid DPoP proof.") from exc
