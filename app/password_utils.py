from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class PasswordManager:
    """Handles password hashing, verification, and encryption/decryption"""
    
    @staticmethod
    def hash_password(password):
        """
        Hash a password using Werkzeug's secure hashing
        
        Args:
            password (str): Plain text password
            
        Returns:
            str: Hashed password
        """
        return generate_password_hash(password, method='pbkdf2:sha256')
    
    @staticmethod
    def verify_password(hashed_password, password):
        """
        Verify a password against its hash
        
        Args:
            hashed_password (str): Hashed password from database
            password (str): Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(hashed_password, password)
    
    @staticmethod
    def generate_encryption_key(password, salt=None):
        """
        Generate an encryption key from a password using PBKDF2
        
        Args:
            password (str): Password to derive key from
            salt (bytes, optional): Salt for key derivation. If None, generates new salt.
            
        Returns:
            tuple: (encryption_key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    @staticmethod
    def encrypt_data(data, password, salt=None):
        """
        Encrypt data using a password-derived key
        
        Args:
            data (str): Data to encrypt
            password (str): Password to derive encryption key from
            salt (bytes, optional): Salt for key derivation. If None, generates new salt.
            
        Returns:
            tuple: (encrypted_data, salt)
        """
        key, salt = PasswordManager.generate_encryption_key(password, salt)
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data.encode())
        return encrypted_data, salt
    
    @staticmethod
    def decrypt_data(encrypted_data, password, salt):
        """
        Decrypt data using a password-derived key
        
        Args:
            encrypted_data (bytes): Encrypted data
            password (str): Password to derive decryption key from
            salt (bytes): Salt used for key derivation
            
        Returns:
            str: Decrypted data
            
        Raises:
            Exception: If decryption fails (wrong password or corrupted data)
        """
        try:
            key, _ = PasswordManager.generate_encryption_key(password, salt)
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            raise Exception("Decryption failed. Check your password or data integrity.") from e
    
    @staticmethod
    def generate_salt():
        """
        Generate a random salt for key derivation
        
        Returns:
            bytes: Random salt
        """
        return os.urandom(16)
    
    @staticmethod
    def salt_to_string(salt):
        """
        Convert salt bytes to string for storage
        
        Args:
            salt (bytes): Salt bytes
            
        Returns:
            str: Base64 encoded salt string
        """
        return base64.b64encode(salt).decode('utf-8')
    
    @staticmethod
    def string_to_salt(salt_string):
        """
        Convert salt string back to bytes
        
        Args:
            salt_string (str): Base64 encoded salt string
            
        Returns:
            bytes: Salt bytes
        """
        return base64.b64decode(salt_string.encode('utf-8')) 