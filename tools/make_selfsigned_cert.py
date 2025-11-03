# Generate a self-signed certificate for localhost (PEM key + cert).

from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import ipaddress, pathlib

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
])

alt_names = x509.SubjectAlternativeName([
    x509.DNSName(u"localhost"),
    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
])

cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.utcnow() - timedelta(minutes=1))
    .not_valid_after(datetime.utcnow() + timedelta(days=30))
    .add_extension(alt_names, critical=False)
    .sign(private_key=key, algorithm=hashes.SHA256())
)

out_dir = pathlib.Path(".")
(out_dir / "key.pem").write_bytes(
    key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,  # PKCS#1
        encryption_algorithm=serialization.NoEncryption(),
    )
)
(out_dir / "cert.pem").write_bytes(
    cert.public_bytes(serialization.Encoding.PEM)
)

print("Wrote key.pem and cert.pem")
