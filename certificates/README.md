# TCS Public Publisher Certificate

This directory contains the **public** self-signed code-signing certificate for The Choco Studios.

- Subject / Issuer: `CN=The Choco Studios`
- Certificate type: Self-signed code-signing certificate
- Validity: 2026-10-30 through 2046-10-30
- SHA-1 thumbprint: `7C28085E23B23E163D66C6F3E0BB948F61D5ECFD`
- Public certificate: `TCS-Publisher.cer`

## Security and trust notes

- This `.cer` file contains public certificate material only. It does not contain the private signing key.
- The matching `.pfx` and its password must remain private. Never commit them to this repository, release packages, issue comments, or public CI logs.
- This self-signed certificate is **not** issued or verified by a public Certificate Authority. Publishing it here does not make Windows SmartScreen trust the application and does not create Microsoft Verified Publisher status.
- Do not instruct customers to add this certificate to Trusted Root Certification Authorities merely to suppress warnings. A customer should only trust a certificate after independently verifying its fingerprint and understanding the security implications.
- The certificate must be used to verify a valid Authenticode signature on a released Windows binary. Adding this file alone does not sign an application.

This file is distributed for public certificate identification and signature verification. The private signing key is controlled separately by the publisher.
