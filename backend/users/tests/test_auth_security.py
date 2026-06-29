import base64
import hashlib
import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User


def _b64url_from_int(value):
    raw = value.to_bytes(32, "big")
    return base64.urlsafe_b64encode(raw).decode("utf-8").replace("=", "")


def _b64url_from_bytes(value):
    return base64.urlsafe_b64encode(value).decode("utf-8").replace("=", "")


class AuthSecurityTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="security@example.com",
            password="StrongPass!123",
            first_name="Security",
            last_name="Tester",
            is_active=True,
            status="ACTIVE",
        )

    def _generate_key_material(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_numbers = private_key.public_key().public_numbers()
        jwk = {
            "kty": "EC",
            "crv": "P-256",
            "x": _b64url_from_int(public_numbers.x),
            "y": _b64url_from_int(public_numbers.y),
        }
        return private_key, jwk

    def _build_dpop_proof(self, method, absolute_url, private_key, jwk, access_token=None):
        payload = {
            "jti": str(uuid.uuid4()),
            "htm": method.upper(),
            "htu": absolute_url,
            "iat": int(time.time()),
        }
        if access_token:
            payload["ath"] = _b64url_from_bytes(hashlib.sha256(access_token.encode("utf-8")).digest())

        return jwt.encode(
            payload,
            private_key,
            algorithm="ES256",
            headers={"typ": "dpop+jwt", "alg": "ES256", "jwk": jwk},
        )

    def test_apply_access_rejects_weak_password(self):
        response = self.client.post(
            reverse("apply-for-access"),
            {
                "email": "newuser@example.com",
                "password": "12345",
                "first_name": "New",
                "last_name": "User",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_login_requires_valid_dpop_proof(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": self.user.email, "password": "StrongPass!123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_requires_matching_dpop_key(self):
        private_key, jwk = self._generate_key_material()
        login_url = "http://testserver" + reverse("token_obtain_pair")
        login_proof = self._build_dpop_proof("POST", login_url, private_key, jwk)

        login_response = self.client.post(
            reverse("token_obtain_pair"),
            {"email": self.user.email, "password": "StrongPass!123"},
            format="json",
            HTTP_DPOP=login_proof,
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        refresh_token = login_response.data["refresh"]
        access_token = login_response.data["access"]
        refresh_claims = RefreshToken(refresh_token)
        self.assertIn("cnf", refresh_claims)

        refresh_url = "http://testserver" + reverse("token_refresh")

        missing_proof_response = self.client.post(
            reverse("token_refresh"),
            {"refresh": refresh_token},
            format="json",
        )
        self.assertEqual(missing_proof_response.status_code, status.HTTP_401_UNAUTHORIZED)

        wrong_private_key, wrong_jwk = self._generate_key_material()
        wrong_proof = self._build_dpop_proof("POST", refresh_url, wrong_private_key, wrong_jwk)
        wrong_proof_response = self.client.post(
            reverse("token_refresh"),
            {"refresh": refresh_token},
            format="json",
            HTTP_DPOP=wrong_proof,
        )
        self.assertEqual(wrong_proof_response.status_code, status.HTTP_401_UNAUTHORIZED)

        valid_refresh_proof = self._build_dpop_proof("POST", refresh_url, private_key, jwk)
        refresh_response = self.client.post(
            reverse("token_refresh"),
            {"refresh": refresh_token},
            format="json",
            HTTP_DPOP=valid_refresh_proof,
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

        protected_url = reverse("current-user")
        protected_absolute_url = "http://testserver" + protected_url
        protected_proof = self._build_dpop_proof(
            "GET",
            protected_absolute_url,
            private_key,
            jwk,
            access_token=access_token,
        )
        protected_response = self.client.get(
            protected_url,
            HTTP_AUTHORIZATION=f"DPoP {access_token}",
            HTTP_DPOP=protected_proof,
        )
        self.assertEqual(protected_response.status_code, status.HTTP_200_OK)
