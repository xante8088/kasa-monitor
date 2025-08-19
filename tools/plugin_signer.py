#!/usr/bin/env python3
"""Plugin Signing CLI Tool

Command-line tool for signing and verifying Kasa Monitor plugins.

Usage:
    python plugin_signer.py generate-keys --name developer_name
    python plugin_signer.py sign plugin.zip --key private_key.pem
    python plugin_signer.py verify plugin_signed.zip
    python plugin_signer.py info plugin_signed.zip

Copyright (C) 2025 Kasa Monitor Contributors
"""

import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from plugin_security import PluginSigner, PluginVerifier, TrustLevel


def generate_keys(args):
    """Generate a new key pair for plugin signing."""
    signer = PluginSigner()
    
    # Generate key pair
    private_pem, public_pem = signer.generate_key_pair(args.key_size)
    
    # Create output directory
    output_dir = Path(args.output or ".")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save private key
    private_key_path = output_dir / f"{args.name}_private.pem"
    with open(private_key_path, 'wb') as f:
        f.write(private_pem)
    
    # Save public key
    public_key_path = output_dir / f"{args.name}_public.pem"
    with open(public_key_path, 'wb') as f:
        f.write(public_pem)
    
    # Set secure permissions
    private_key_path.chmod(0o600)
    public_key_path.chmod(0o644)
    
    print(f"✅ Key pair generated successfully!")
    print(f"📁 Private key: {private_key_path}")
    print(f"📁 Public key: {public_key_path}")
    print()
    print("⚠️  Keep your private key secure and never share it!")
    print("📤 Share your public key with users who need to verify your plugins.")


def sign_plugin(args):
    """Sign a plugin package."""
    try:
        # Initialize signer
        signer = PluginSigner(args.key)
        
        # Prepare metadata
        metadata = {
            "signer": args.signer or "Unknown",
            "contact": args.contact,
            "organization": args.organization,
            "description": args.description
        }
        
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        # Sign plugin
        signed_path = signer.sign_plugin(
            args.plugin,
            args.output,
            metadata
        )
        
        print(f"✅ Plugin signed successfully!")
        print(f"📦 Original: {args.plugin}")
        print(f"🔐 Signed: {signed_path}")
        print()
        print("📋 Signature metadata:")
        for key, value in metadata.items():
            print(f"   {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error signing plugin: {e}")
        sys.exit(1)


def verify_plugin(args):
    """Verify a plugin's signature."""
    try:
        verifier = PluginVerifier(args.trusted_keys_dir)
        result = verifier.verify_plugin(args.plugin)
        
        # Display verification result
        if result["verified"]:
            print(f"✅ Plugin signature is VALID")
            print(f"🔐 Trust level: {result['trust_level'].value.upper()}")
            print(f"👤 Signer: {result['signer'] or 'Unknown'}")
            print(f"📅 Signed: {result['timestamp']}")
            if "verified_by" in result:
                print(f"🔑 Verified by key: {result['verified_by']}")
        else:
            print(f"❌ Plugin signature is INVALID or MISSING")
            print(f"⚠️  Trust level: {result['trust_level'].value.upper()}")
            if result["signer"]:
                print(f"👤 Claims to be signed by: {result['signer']}")
        
        if result["errors"]:
            print("\n🚨 Errors:")
            for error in result["errors"]:
                print(f"   • {error}")
        
        if not args.quiet:
            print(f"\n📄 Full verification result:")
            print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Error verifying plugin: {e}")
        sys.exit(1)


def show_info(args):
    """Show detailed information about a plugin."""
    try:
        verifier = PluginVerifier(args.trusted_keys_dir)
        result = verifier.verify_plugin(args.plugin)
        
        print(f"📦 Plugin Information: {args.plugin}")
        print("=" * 50)
        
        # Basic info
        print(f"Signature Status: {'✅ VALID' if result['verified'] else '❌ INVALID/MISSING'}")
        print(f"Trust Level: {result['trust_level'].value.upper()}")
        
        if result["signer"]:
            print(f"Signer: {result['signer']}")
        
        if result["timestamp"]:
            print(f"Signature Date: {result['timestamp']}")
        
        if "verified_by" in result:
            print(f"Verified By: {result['verified_by']}")
        
        # Security recommendation
        print("\n🔒 Security Recommendation:")
        if result["trust_level"] == TrustLevel.OFFICIAL:
            print("   ✅ This is an official plugin - safe to install")
        elif result["trust_level"] == TrustLevel.VERIFIED:
            print("   ✅ This plugin is from a verified developer")
        elif result["trust_level"] == TrustLevel.COMMUNITY:
            print("   ⚠️  Community plugin - verify the source before installing")
        elif result["trust_level"] == TrustLevel.UNSIGNED:
            print("   ⚠️  Unsigned plugin - use caution and verify the source")
        else:
            print("   🚨 INVALID signature - DO NOT INSTALL")
        
        if result["errors"]:
            print("\n🚨 Issues Found:")
            for error in result["errors"]:
                print(f"   • {error}")
        
    except Exception as e:
        print(f"❌ Error reading plugin info: {e}")
        sys.exit(1)


def list_trusted_keys(args):
    """List trusted public keys."""
    try:
        verifier = PluginVerifier(args.trusted_keys_dir)
        
        if not verifier.trusted_keys:
            print("📭 No trusted keys found.")
            print(f"Add public keys to: {verifier.trusted_keys_dir}")
            return
        
        print("🔑 Trusted Public Keys:")
        print("=" * 30)
        
        for key_name, public_key in verifier.trusted_keys.items():
            trust_level = verifier._determine_trust_level(key_name)
            print(f"• {key_name} ({trust_level.value})")
        
        print(f"\nKeys location: {verifier.trusted_keys_dir}")
        
    except Exception as e:
        print(f"❌ Error listing trusted keys: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Kasa Monitor Plugin Signing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate new key pair
  %(prog)s generate-keys --name my_company

  # Sign a plugin
  %(prog)s sign plugin.zip --key my_company_private.pem --signer "My Company"

  # Verify a plugin
  %(prog)s verify plugin_signed.zip

  # Show plugin info
  %(prog)s info plugin_signed.zip

  # List trusted keys
  %(prog)s list-keys
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Generate keys command
    gen_parser = subparsers.add_parser("generate-keys", help="Generate new signing key pair")
    gen_parser.add_argument("--name", required=True, help="Name for the key pair")
    gen_parser.add_argument("--key-size", type=int, default=2048, help="RSA key size (default: 2048)")
    gen_parser.add_argument("--output", "-o", help="Output directory (default: current)")
    
    # Sign command
    sign_parser = subparsers.add_parser("sign", help="Sign a plugin package")
    sign_parser.add_argument("plugin", help="Path to plugin ZIP file")
    sign_parser.add_argument("--key", "-k", required=True, help="Path to private key file")
    sign_parser.add_argument("--output", "-o", help="Output path for signed plugin")
    sign_parser.add_argument("--signer", "-s", help="Signer name/organization")
    sign_parser.add_argument("--contact", "-c", help="Contact information")
    sign_parser.add_argument("--organization", help="Organization name")
    sign_parser.add_argument("--description", "-d", help="Signature description")
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify plugin signature")
    verify_parser.add_argument("plugin", help="Path to plugin ZIP file")
    verify_parser.add_argument("--trusted-keys-dir", default="./keys/trusted", 
                              help="Directory containing trusted public keys")
    verify_parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show plugin information")
    info_parser.add_argument("plugin", help="Path to plugin ZIP file")
    info_parser.add_argument("--trusted-keys-dir", default="./keys/trusted",
                            help="Directory containing trusted public keys")
    
    # List keys command
    list_parser = subparsers.add_parser("list-keys", help="List trusted public keys")
    list_parser.add_argument("--trusted-keys-dir", default="./keys/trusted",
                            help="Directory containing trusted public keys")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route to appropriate function
    if args.command == "generate-keys":
        generate_keys(args)
    elif args.command == "sign":
        sign_plugin(args)
    elif args.command == "verify":
        verify_plugin(args)
    elif args.command == "info":
        show_info(args)
    elif args.command == "list-keys":
        list_trusted_keys(args)


if __name__ == "__main__":
    main()