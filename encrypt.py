import tarfile
import io
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import getpass

def get_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_files(files: list, output: str, password: str):
    # Create tar archive in memory
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        for file in files:
            tar.add(file)
    
    # Encrypt
    salt = b'dimensional_salt'  # Fixed salt for consistency
    key = get_key(password, salt)
    f = Fernet(key)
    encrypted = f.encrypt(tar_buffer.getvalue())
    
    with open(output, 'wb') as out:
        out.write(encrypted)
    print(f"✓ Encrypted {len(files)} files to {output}")

def decrypt_files(input_file: str, password: str):
    # Decrypt
    salt = b'dimensional_salt'
    key = get_key(password, salt)
    f = Fernet(key)
    
    with open(input_file, 'rb') as file:
        encrypted = file.read()
    
    try:
        decrypted = f.decrypt(encrypted)
    except:
        print("❌ Wrong password!")
        return
    
    # Extract tar
    tar_buffer = io.BytesIO(decrypted)
    with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
        tar.extractall()
    print(f"✓ Decrypted and extracted files")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Encrypt: python encrypt.py -e file1 file2 file3")
        print("  Decrypt: python encrypt.py -d secrets.enc")
        sys.exit(1)
    
    if sys.argv[1] == '-e':
        files = sys.argv[2:]
        password = getpass.getpass("Password: ")
        encrypt_files(files, 'secrets.enc', password)
    elif sys.argv[1] == '-d':
        password = getpass.getpass("Password: ")
        decrypt_files(sys.argv[2], password)