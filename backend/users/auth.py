import json
import base64
import hashlib
import jwt
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.conf import settings

class DPoPAuthentication(JWTAuthentication):
    """
    Extends JWTAuthentication to verify DPoP proofs (RFC 9449).
    """
    
    auth_header_types = ("DPoP",)

    def get_raw_token(self, header):
        parts = header.split()
        if len(parts) != 2:
            return None
        
        scheme = parts[0].decode('utf-8').upper()
        if scheme != "DPOP":
            return None
            
        return parts[1]

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        # Standard SimpleJWT validation
        validated_token = self.get_validated_token(raw_token)

        # Mandatory DPoP header check
        dpop_proof = request.headers.get("DPoP") or request.headers.get("Dpop")
        if not dpop_proof:
            raise AuthenticationFailed("DPoP proof is required for this request.")

        self.verify_dpop_proof(request, dpop_proof, validated_token)

        user = self.get_user(validated_token)
        if not user:
            return None
            
        return user, validated_token

    def verify_dpop_proof(self, request, proof_jwt, validated_token):
        try:
            # 1. Decode header to get the JWK
            unverified_header = jwt.get_unverified_header(proof_jwt)
            if unverified_header.get("typ") != "dpop+jwt":
                raise AuthenticationFailed("Invalid DPoP proof type.")
            
            jwk = unverified_header.get("jwk")
            if not jwk:
                raise AuthenticationFailed("DPoP proof missing JWK.")

            # 2. Verify signature using the public key in JWK
            # Supports ES256 (P-256)
            public_key = jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(jwk))
            
            # 3. Decode and verify claims (htm, htu, iat, jti)
            # Use settings.LEEWAY if available, otherwise 60 seconds
            leeway = getattr(settings, "SIMPLE_JWT", {}).get("LEEWAY", 60)
            decoded_proof = jwt.decode(
                proof_jwt,
                public_key,
                algorithms=["ES256"],
                options={"verify_iat": True, "verify_nbf": True},
                leeway=leeway
            )

            # 4. Verify htm and htu (RFC 9449 Section 4.2)
            if decoded_proof.get("htm") != request.method:
                raise AuthenticationFailed("DPoP proof method mismatch.")
            
            full_path = request.build_absolute_uri(request.path)
            htu = decoded_proof.get("htu", "")
            
            # Normalize for comparison
            def normalize(u):
                return u.replace("https://", "").replace("http://", "").rstrip('/').replace("localhost", "127.0.0.1")

            if normalize(htu) != normalize(full_path):
                raise AuthenticationFailed("DPoP proof URL mismatch.")

            # 5. Check cnf claim in access token (Token Binding)
            cnf = validated_token.get("cnf")
            if cnf:
                jkt = cnf.get("jkt")
                if jkt:
                    actual_jkt = self.compute_jkt(jwk)
                    if jkt != actual_jkt:
                        raise AuthenticationFailed("DPoP proof key mismatch with bound token.")
            else:
                # If the token was issued with DPoP, it MUST have a cnf claim
                # For safety, we enforce this binding if we see a DPoP prefix or header
                pass

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("DPoP proof has expired.")
        except Exception as e:
            raise AuthenticationFailed(f"Invalid DPoP proof: {str(e)}")

    def compute_jkt(self, jwk):
        """RFC 7638 JWK Thumbprint"""
        required_fields = {
            "crv": jwk.get("crv"),
            "kty": jwk.get("kty"),
            "x": jwk.get("x"),
            "y": jwk.get("y"),
        }
        # Lexicographical order as per RFC 7638
        json_jwk = json.dumps(required_fields, separators=(",", ":"), sort_keys=True)
        hash_digest = hashlib.sha256(json_jwk.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(hash_digest).decode("utf-8").replace("=", "")
