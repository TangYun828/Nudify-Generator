#!/usr/bin/env python3
"""
Generate C2PA Certificate and Private Key for legal compliance watermarking
California SB 942 / New York AI Transparency Laws
"""

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
import os

def generate_c2pa_credentials():
    """Generate self-signed certificate for C2PA manifest signing"""
    
    print("=" * 60)
    print("C2PA CERTIFICATE GENERATION FOR LEGAL COMPLIANCE")
    print("=" * 60)
    
    # Certificate details
    org_name = "intimai.cc"
    email = "legal@intimai.cc"
    country = "US"
    state = "California"
    city = "San Francisco"
    
    # Generate private key
    print("\n[1/4] Generating 2048-bit RSA private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Generate certificate
    print("[2/4] Creating self-signed certificate...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, country),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
        x509.NameAttribute(NameOID.LOCALITY_NAME, city),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org_name),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "AI Compliance"),
        x509.NameAttribute(NameOID.COMMON_NAME, org_name),
        x509.NameAttribute(NameOID.EMAIL_ADDRESS, email),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=3650)  # 10 years
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.RFC822Name(email),
            x509.DNSName(org_name),
        ]),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=0),
        critical=True,
    ).sign(
        private_key,
        hashes.SHA256()
    )
    
    # Save private key
    print("[3/4] Saving private key to c2pa_private_key.pem...")
    with open("c2pa_private_key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Save certificate
    print("[4/4] Saving certificate to c2pa_certificate.pem...")
    with open("c2pa_certificate.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print("\n" + "=" * 60)
    print("✓ C2PA CREDENTIALS GENERATED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nCertificate Details:")
    print(f"  Organization: {org_name}")
    print(f"  Email: {email}")
    print(f"  Country: {country}")
    print(f"  Valid for: 10 years")
    print(f"\nFiles Created:")
    print(f"  ✓ c2pa_private_key.pem (KEEP SECRET - used for signing)")
    print(f"  ✓ c2pa_certificate.pem  (public certificate)")
    print(f"\nNEXT STEPS:")
    print(f"  1. Do NOT commit these files to git (add to .gitignore)")
    print(f"  2. Store private key in secure environment variable")
    print(f"  3. Add certificate to deployment configuration")
    print(f"\nLegal Compliance:")
    print(f"  • C2PA Manifest: Cryptographically signed proof of AI generation")
    print(f"  • Required by: California SB 942 / New York AI Transparency Act")
    print(f"  • Penalty for non-compliance: Up to $5,000 per violation")
    print("=" * 60)

if __name__ == "__main__":
    try:
        generate_c2pa_credentials()
    except Exception as e:
        print(f"\n✗ Error generating credentials: {e}")
        exit(1)
