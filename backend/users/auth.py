from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

from users.dpop import compute_token_ath, validate_dpop_proof

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

        dpop_proof = request.headers.get("DPoP") or request.headers.get("Dpop")
        cnf = validated_token.get("cnf") or {}
        expected_jkt = cnf.get("jkt")
        if not expected_jkt:
            raise AuthenticationFailed("DPoP-bound token is required for this request.")

        token_value = raw_token.decode("utf-8") if isinstance(raw_token, bytes) else raw_token
        validate_dpop_proof(
            request,
            dpop_proof,
            expected_jkt=expected_jkt,
            expected_ath=compute_token_ath(token_value),
        )

        user = self.get_user(validated_token)
        if not user:
            return None
            
        return user, validated_token
