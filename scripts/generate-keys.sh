#!/usr/bin/env bash
# Generate a dev RS256 keypair for JWT signing/verification.
# Writes keys/jwt_private.pem and keys/jwt_public.pem at the repo root.
# The private key is gitignored — never commit real keys.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/keys"

openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out "$ROOT/keys/jwt_private.pem"
openssl rsa -in "$ROOT/keys/jwt_private.pem" -pubout \
  -out "$ROOT/keys/jwt_public.pem"

echo "Wrote keys/jwt_private.pem and keys/jwt_public.pem"
