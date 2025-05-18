from pydantic import BaseModel
from typing import Optional

class NonceResponse(BaseModel):
    nonce: str

class VerifySignatureRequest(BaseModel):
    address: str  # User-friendly TON address (e.g., EQ..., UQ...)
    public_key: str  # Hex-encoded Ed25519 public key
    nonce: str # The nonce string that was signed
    signature: str  # Base64-encoded signature of the nonce

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    # This model can be used to represent the data encoded in the JWT
    # For example, to verify token scope or extract user information
    address: Optional[str] = None