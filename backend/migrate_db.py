#!/usr/bin/env python3
"""
Database migration script to add missing columns
"""

import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

async def migrate_database():
    """Add missing columns to existing tables"""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    engine = create_async_engine(DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            print("🔄 Checking database schema...")
            
            # Check if updated_at column exists in zoho_installations
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'zoho_installations' 
                AND column_name = 'updated_at'
            """))
            
            if not result.fetchone():
                print("⚠️  Missing 'updated_at' column in zoho_installations table")
                print("🔧 Adding missing column...")
                
                # Add the missing updated_at column
                await conn.execute(text("""
                    ALTER TABLE zoho_installations 
                    ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE 
                    DEFAULT NOW() NOT NULL
                """))
                
                # Update existing records to have the same updated_at as created_at
                await conn.execute(text("""
                    UPDATE zoho_installations 
                    SET updated_at = created_at 
                    WHERE updated_at IS NULL
                """))
                
                print("✅ Successfully added 'updated_at' column to zoho_installations")
            else:
                print("✅ 'updated_at' column already exists in zoho_installations")
            
            # Check if updated_at column exists in slack_installations
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'slack_installations' 
                AND column_name = 'updated_at'
            """))
            
            if not result.fetchone():
                print("⚠️  Missing 'updated_at' column in slack_installations table")
                print("🔧 Adding missing column...")
                
                # Add the missing updated_at column
                await conn.execute(text("""
                    ALTER TABLE slack_installations 
                    ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE 
                    DEFAULT NOW() NOT NULL
                """))
                
                # Update existing records to have the same updated_at as created_at
                await conn.execute(text("""
                    UPDATE slack_installations 
                    SET updated_at = created_at 
                    WHERE updated_at IS NULL
                """))
                
                print("✅ Successfully added 'updated_at' column to slack_installations")
            else:
                print("✅ 'updated_at' column already exists in slack_installations")
            
            print("🎉 Database migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(migrate_database())
    sys.exit(0 if success else 1) 