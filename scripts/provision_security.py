#!/usr/bin/env python3
"""
PromoBeacon ESP32 — Hardware Security Provisioning Tool
Manages Secure Boot v2 (RSA-3072) key generation, binary signing,
and Flash Encryption (AES-256) preparation for production deployments.
"""
import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

# Force UTF-8 on stdout for cross-platform safety
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent
FW_DIR = ROOT_DIR / "firmware"
KEY_FILE = FW_DIR / "secure_boot_signing_key.pem"
PUBLIC_KEY_DIGEST = FW_DIR / "secure_boot_digest.bin"

def find_espsecure():
    """Locate espsecure.py in PATH or PlatformIO tool packages."""
    if shutil.which("espsecure.py"):
        return ["espsecure.py"]
    
    # Check PlatformIO packages
    home = Path.home()
    pio_esptool = home / ".platformio" / "packages" / "tool-esptoolpy" / "espsecure.py"
    if pio_esptool.exists():
        return [sys.executable, str(pio_esptool)]
    
    return [sys.executable, "-m", "espsecure"]

def generate_keys():
    """Generate RSA-3072 signing key for Secure Boot v2."""
    espsecure = find_espsecure()
    print("=" * 70)
    print("  [SEC] PROMOBEACON - GERACAO DE CHAVES DE SEGURANCA")
    print("=" * 70)
    
    if KEY_FILE.exists():
        print(f"[!] Chave privada já existe em: {KEY_FILE}")
        confirm = input("Deseja sobrescrever? Isso invalidará dispositivos já gravados! (s/N): ").strip().lower()
        if confirm != "s":
            print("Operação cancelada.")
            return

    cmd = espsecure + ["generate_signing_key", "--version", "2", str(KEY_FILE)]
    print(f"Executando: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("[ERRO] Falha ao gerar chave RSA com espsecure.")
        sys.exit(1)
    
    print(f"[OK] Chave privada RSA-3072 gerada: {KEY_FILE}")
    print("   [!] IMPORTANTE: Guarde este arquivo em local seguro e NUNCA compartilhe no Git!")

    # Extract public key digest for eFuse burning
    digest_cmd = espsecure + ["digest_sbv2_public_key", "--keyfile", str(KEY_FILE), "-o", str(PUBLIC_KEY_DIGEST)]
    res = subprocess.run(digest_cmd)
    if res.returncode == 0:
        print(f"[OK] Digest da chave pública gerado: {PUBLIC_KEY_DIGEST}")

def sign_binary(binary_path: str):
    """Sign a firmware binary with the Secure Boot key."""
    if not KEY_FILE.exists():
        print(f"[ERRO] Chave privada não encontrada em: {KEY_FILE}")
        print("Execute primeiro: python scripts/provision_security.py --generate-keys")
        sys.exit(1)

    bin_file = Path(binary_path).resolve()
    if not bin_file.exists():
        print(f"[ERRO] Arquivo binário não encontrado: {bin_file}")
        sys.exit(1)

    espsecure = find_espsecure()
    signed_output = bin_file.parent / f"{bin_file.stem}_signed.bin"

    cmd = espsecure + [
        "sign_data",
        "--version", "2",
        "--keyfile", str(KEY_FILE),
        "--output", str(signed_output),
        str(bin_file)
    ]
    print(f"Assinando binário com RSA-3072: {bin_file.name}")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("[ERRO] Falha ao assinar binário.")
        sys.exit(1)

    print(f"[OK] Binário assinado com sucesso: {signed_output}")

def verify_binary(binary_path: str):
    """Verify the signature on a firmware binary."""
    bin_file = Path(binary_path).resolve()
    if not bin_file.exists():
        print(f"[ERRO] Arquivo não encontrado: {bin_file}")
        sys.exit(1)

    espsecure = find_espsecure()
    cmd = espsecure + ["verify_signature", "--version", "2", "--keyfile", str(KEY_FILE), str(bin_file)]
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"[OK] Assinatura VÁLIDA: {bin_file.name}")
    else:
        print(f"[FALHA] Assinatura INVÁLIDA ou ausente: {bin_file.name}")

def print_help_guide():
    print("""
==============================================================================
  PROMOBEACON ESP32 — GUIA OPERACIONAL DE SEGURANCA EM PRODUCAO
==============================================================================
1. Gerar Chaves de Producao:
   python scripts/provision_security.py --generate-keys

2. Compilar Ambiente Seguro:
   cd firmware
   pio run -e esp32c3-secure
   (ou pio run -e esp32dev-secure)

3. Assinar Binário para OTA:
   python scripts/provision_security.py --sign firmware/.pio/build/esp32c3-secure/firmware.bin

4. Modo de Criptografia da Flash:
   - Development Mode (Padrão no sdkconfig.secure): permite testes e regravações via UART.
   - Release Mode: Queima irreversível de eFuses (travamento definitivo para produção em massa).
==============================================================================
""")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PromoBeacon Hardware Security Provisioning")
    parser.add_argument("--generate-keys", action="store_true", help="Gera nova chave RSA-3072 de Secure Boot v2")
    parser.add_argument("--sign", metavar="BIN_PATH", help="Assina um arquivo binário com a chave privada")
    parser.add_argument("--verify", metavar="BIN_PATH", help="Verifica a assinatura digital de um binário")
    parser.add_argument("--guide", action="store_true", help="Exibe o guia operacional de segurança")

    args = parser.parse_args()

    if args.generate_keys:
        generate_keys()
    elif args.sign:
        sign_binary(args.sign)
    elif args.verify:
        verify_binary(args.verify)
    else:
        print_help_guide()
