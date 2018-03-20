import base64

from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from django.core.cache import cache


def generate_RSA(bits=1024):
    new_key = RSA.generate(bits, e=65537)
    public_key = new_key.publickey().exportKey("PEM")
    private_key = new_key.exportKey("PEM")
    return private_key, public_key


def doRSAFromBytes(key, plaintext):
    # Assuming that the public key is coming from java or javascript,
    # strip off the headers.
    key = key.replace('-----BEGIN PUBLIC KEY-----', '')
    key = key.replace('-----END PUBLIC KEY-----', '')
    # Since it's coming from java/javascript, it's base 64 encoded.
    # Decode before importing.
    pubkey = RSA.importKey(base64.b64decode(key))
    cipher = PKCS1_OAEP.new(pubkey, hashAlgo=SHA256)
    encrypted = cipher.encrypt(plaintext)
    return base64.b64encode(encrypted)


def decryptRSA(ciphertext, private_key):
    rsa_key = RSA.importKey(private_key)
    cipher = PKCS1_OAEP.new(rsa_key, hashAlgo=SHA256)
    decrypted = cipher.decrypt(base64.b64decode(ciphertext))
    return decrypted


def get_keys():
    keys = cache.get("RSA_KEYS")
    if keys is None:
        keys = generate_RSA()
    cache.set("RSA_KEYS", keys, 3600)
    return keys


def get_public_key():
    _, pub = get_keys()
    return pub.decode()