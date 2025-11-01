import os, sys
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, AESGCMSIV
from cryptography.exceptions import InvalidTag

KEY_LENGTH = 256  # AES key length in bits

# --- Core AES-GCM Functions (変更なし) ---
def aesgcm_gen_key():
    """Generates a secure 256-bit (32-byte) AES key."""
    return AESGCM.generate_key(bit_length=KEY_LENGTH)
def aesgcmsiv_gen_key():
    # AESGCMSIVクラスのメソッドを呼び出す
    return AESGCMSIV.generate_key(bit_length=KEY_LENGTH)

def b64_dec(s):
    s_utf8 = s.encode('utf-8')
    # Append padding
    padding_needed = 4 - (len(s_utf8) % 4)
    if padding_needed != 4:
        s_utf8 += b'=' * padding_needed
    bytes = base64.urlsafe_b64decode(s_utf8)
    return bytes

def b64_enc(bytes):
    return base64.urlsafe_b64encode(bytes).decode('ascii')

def aesgcm_enc(key, plaintext, associated_data=b''):
    """
    Encrypts plaintext using AES-GCM.
    The authentication tag is automatically appended to the ciphertext.
    Returns: A tuple of (nonce, ciphertext).
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # A 96-bit nonce is standard for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    return (nonce, ciphertext)

def aesgcm_dec(key, nonce, ciphertext, associated_data=b''):
    """
    Decrypts AES-GCM ciphertext and verifies its authenticity.    
    Returns: The plaintext if successful, otherwise None.
    """
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
        return plaintext
    except InvalidTag:
        # This occurs if the key is wrong or the data has been tampered with.
        return None

def aesgcmsiv_gen_key():
    """Generates a secure 256-bit (32-byte) AES-GCM-SIV key."""
    return AESGCMSIV.generate_key(bit_length=KEY_LENGTH)

def aesgcmsiv_enc(key, plaintext, associated_data=b''):
    """Encrypts plaintext using AES-GCM-SIV."""
    aesgcmsiv = AESGCMSIV(key)
    nonce = os.urandom(12)  # SIVでも96-bit nonceが使用可能
    ciphertext = aesgcmsiv.encrypt(nonce, plaintext, associated_data)
    return (nonce, ciphertext)

def aesgcmsiv_dec(key, nonce, ciphertext, associated_data=b''):
    """Decrypts AES-GCM-SIV ciphertext and verifies its authenticity."""
    aesgcmsiv = AESGCMSIV(key)
    try:
        return aesgcmsiv.decrypt(nonce, ciphertext, associated_data)
    except InvalidTag:
        return None

# --- Base64 Encoding/Decoding Functions for QR Code ---
def aesgcm_enc_b64(nonce, ciphertext):
    """
    Combines nonce and ciphertext, then Base64 encodes the result for a QR code.    
    Returns: A Base64 encoded ASCII string.
    """
    # Simple concatenation is a common and effective method
    binary_payload = nonce + ciphertext
    return b64_enc(binary_payload)

def aesgcm_dec_b64(b64_str):
    """
    Decodes a Base64 string from a QR code and splits it back into nonce and ciphertext.
    Returns: A tuple of (nonce, ciphertext).
    """
    try:
        binary_payload = b64_dec(b64_str)
        if len(binary_payload) < 12:
            return None, None # データがノンス長より短い
        # The first 12 bytes are the nonce, the rest is the ciphertext+tag
        nonce = binary_payload[:12]
        ciphertext = binary_payload[12:]
        return (nonce, ciphertext)
    except (ValueError, TypeError):
        # Handles incorrect Base64 padding or characters
        return None, None

# --- Main Example ---

if __name__ == "__main__":
    # 1. Generate a secret key (must be shared between sender and receiver)
    if len(sys.argv) > 2:
        secret_key = b64_dec(sys.argv[2])
        if len(secret_key) * 8 != KEY_LENGTH:
            print(f"Error: Secret key is {len(secret_key)} bytes and must be {KEY_LENGTH} bits long.")
            sys.exit(1)
    else:
        secret_key = aesgcmsiv_gen_key()

    # 2. Define the plaintext to be encrypted
    # plaintext = b"my_secret_keyword"
    plaintext = sys.argv[1].encode('utf-8') if len(sys.argv) > 1 else b"my_secret_keyword"

    print(f"Secret Key (Base64)    : {b64_enc(secret_key)}")
    print(f"Plaintext              : {plaintext.decode('utf-8')}")
    print("")
    # 3. Encrypt the plaintext
    nonce, ciphertext = aesgcmsiv_enc(secret_key, plaintext)
    print(f"Nonce (Base64)         : {b64_enc(nonce)}")
    print(f"Ciphertext+Tag (Base64): {b64_enc(ciphertext)}")
    print("")
    # 4. Encode for QR code
    qr_data_string = aesgcm_enc_b64(nonce, ciphertext)
    print(f"QR Code Data (Base64)  : {qr_data_string}")
    print("")
    # 5. Decode from QR code
    decoded_nonce, decoded_ciphertext = aesgcm_dec_b64(qr_data_string)
    if decoded_nonce is None or decoded_ciphertext is None:
        print("Failed to decode QR code data.")
        sys.exit(1)
    # 6. Decrypt the ciphertext
    decrypted_plaintext = aesgcmsiv_dec(secret_key, decoded_nonce, decoded_ciphertext)
    if decrypted_plaintext is None:
        print("Decryption failed or data integrity check failed.")
        sys.exit(1)
    print(f"Decrypted Plaintext    : {decrypted_plaintext.decode('utf-8')}")
    # Verify that the decrypted plaintext matches the original
    assert decrypted_plaintext == plaintext, "Decrypted plaintext does not match the original!"
    print("Decryption successful and data integrity verified.")
