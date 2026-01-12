"""
加密模块测试
"""

import unittest
import os

from crypto.aes import AESCipher
from crypto.rsa import RSACipher
from crypto.dh import DHKeyExchange, derive_session_keys
from crypto.hmac_auth import HMACAuth
from crypto.kdf import KeyDerivation, PasswordHash


class TestAES(unittest.TestCase):
    """AES 加密测试"""
    
    def test_cbc_encrypt_decrypt(self):
        """测试 CBC 模式"""
        cipher = AESCipher()
        plaintext = b"Hello, World! This is a test message."
        
        ciphertext, iv = cipher.encrypt_cbc(plaintext)
        decrypted = cipher.decrypt_cbc(ciphertext, iv)
        
        self.assertEqual(plaintext, decrypted)
    
    def test_ctr_encrypt_decrypt(self):
        """测试 CTR 模式"""
        cipher = AESCipher()
        plaintext = b"Stream cipher test data"
        
        ciphertext, nonce = cipher.encrypt_ctr(plaintext)
        decrypted = cipher.decrypt_ctr(ciphertext, nonce)
        
        self.assertEqual(plaintext, decrypted)
    
    def test_gcm_encrypt_decrypt(self):
        """测试 GCM 模式"""
        cipher = AESCipher()
        plaintext = b"Authenticated encryption test"
        aad = b"additional data"
        
        ciphertext, nonce, tag = cipher.encrypt_gcm(plaintext, aad)
        decrypted = cipher.decrypt_gcm(ciphertext, nonce, tag, aad)
        
        self.assertEqual(plaintext, decrypted)


class TestRSA(unittest.TestCase):
    """RSA 加密测试"""
    
    def test_encrypt_decrypt(self):
        """测试加解密"""
        private_key, public_key = RSACipher.generate_keypair()
        cipher = RSACipher(private_key=private_key)
        
        plaintext = b"RSA encryption test"
        ciphertext = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(ciphertext)
        
        self.assertEqual(plaintext, decrypted)
    
    def test_sign_verify(self):
        """测试签名验证"""
        private_key, public_key = RSACipher.generate_keypair()
        cipher = RSACipher(private_key=private_key)
        
        message = b"Message to sign"
        signature = cipher.sign(message)
        
        self.assertTrue(cipher.verify(message, signature))
        self.assertFalse(cipher.verify(b"Wrong message", signature))


class TestDH(unittest.TestCase):
    """DH 密钥交换测试"""
    
    def test_key_exchange(self):
        """测试密钥交换"""
        alice = DHKeyExchange()
        bob = DHKeyExchange()
        
        alice_pub = alice.generate_keypair()
        bob_pub = bob.generate_keypair()
        
        alice_secret = alice.compute_shared_secret(bob_pub)
        bob_secret = bob.compute_shared_secret(alice_pub)
        
        self.assertEqual(alice_secret, bob_secret)


class TestHMAC(unittest.TestCase):
    """HMAC 测试"""
    
    def test_hmac(self):
        """测试 HMAC 生成和验证"""
        key = os.urandom(32)
        message = b"Test message"
        
        auth = HMACAuth(key)
        mac = auth.generate(message)
        
        self.assertTrue(auth.verify(message, mac))
        self.assertFalse(auth.verify(b"Wrong", mac))


class TestKDF(unittest.TestCase):
    """密钥派生测试"""
    
    def test_derive_key(self):
        """测试密钥派生"""
        password = "test_password"
        salt = KeyDerivation.generate_salt()
        
        key1 = KeyDerivation.derive_key(password, salt)
        key2 = KeyDerivation.derive_key(password, salt)
        
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)


if __name__ == '__main__':
    unittest.main()
