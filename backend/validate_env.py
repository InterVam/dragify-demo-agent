#!/usr/bin/env python3
"""
Environment validation script for Dragify Demo Agent Backend
Run this script to validate all required environment variables and configurations.
"""

import os
import sys
from dotenv import load_dotenv

def validate_environment():
    """Validate all required environment variables and configurations."""
    load_dotenv()
    
    errors = []
    warnings = []
    
    # Required environment variables
    required_vars = {
        'DATABASE_URL': 'Database connection URL',
        'SLACK_SIGNING_SECRET': 'Slack app signing secret',
        'SLACK_CLIENT_ID': 'Slack app client ID',
        'SLACK_CLIENT_SECRET': 'Slack app client secret',
        'SLACK_REDIRECT_URI': 'Slack OAuth redirect URI',
        'GROQ_API_KEY': 'Groq LLM API key'
    }
    
    # Optional but recommended
    optional_vars = {
        'ZOHO_CLIENT_ID': 'Zoho CRM client ID',
        'ZOHO_CLIENT_SECRET': 'Zoho CRM client secret',
        'ZOHO_REDIRECT_URI': 'Zoho OAuth redirect URI'
    }
    
    print("🔍 Validating environment configuration...")
    print()
    
    # Check required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            errors.append(f"❌ {var}: {description} - MISSING")
        else:
            # Mask sensitive values
            display_value = value[:8] + "..." if len(value) > 8 else value
            print(f"✅ {var}: {display_value}")
    
    print()
    
    # Check optional variables
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if not value:
            warnings.append(f"⚠️  {var}: {description} - NOT SET")
        else:
            display_value = value[:8] + "..." if len(value) > 8 else value
            print(f"✅ {var}: {display_value}")
    
    print()
    
    # Database URL validation
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        if not db_url.startswith('postgresql+asyncpg://'):
            errors.append("❌ DATABASE_URL: Must use 'postgresql+asyncpg://' for async support")
    
    # Print results
    if errors:
        print("❌ ERRORS FOUND:")
        for error in errors:
            print(f"  {error}")
        print()
    
    if warnings:
        print("⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    if not errors and not warnings:
        print("🎉 All environment variables are properly configured!")
    elif not errors:
        print("✅ All required environment variables are set.")
        print("   Some optional configurations are missing but the app should work.")
    else:
        print("💥 Configuration errors found. Please fix them before starting the application.")
        return False
    
    return True

if __name__ == "__main__":
    success = validate_environment()
    sys.exit(0 if success else 1) 