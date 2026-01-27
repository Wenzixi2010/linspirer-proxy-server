from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
import os


class Cryptor:
    def __init__(self, key: bytes, iv: bytes):
        self.key = key
        self.iv = iv
    
    def encrypt(self, plaintext: str) -> str:
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode()) + padder.finalize()
        
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        return base64.b64encode(ciphertext).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        try:
            ciphertext_bytes = base64.b64decode(ciphertext)
            
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(ciphertext_bytes) + decryptor.finalize()
            
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            
            return data.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
