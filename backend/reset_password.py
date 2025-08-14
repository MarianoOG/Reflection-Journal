#!/usr/bin/env python3
"""
Password reset script for existing users.

This script allows you to manually reset a user's password when they can't remember it.
Use this for administrative password resets.

Usage:
    python reset_password.py user@example.com
    python reset_password.py --email user@example.com --password newpassword123
"""

import sys
import argparse
import getpass
from sqlmodel import Session, create_engine, select
from config import Settings
from models import User
from auth import get_password_hash

def reset_user_password(email: str, new_password: str = None):
    """Reset password for a user by email."""
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    
    with Session(engine) as session:
        # Find the user
        user = session.exec(select(User).where(User.email == email)).first()
        
        if not user:
            print(f"❌ User with email '{email}' not found.")
            return False
        
        print(f"👤 Found user: {user.name} ({user.email})")
        print(f"📅 Created: {user.created_at}")
        print(f"🕐 Last login: {user.last_login}")
        
        # Get new password if not provided
        if not new_password:
            print("\n🔐 Enter new password for this user:")
            new_password = getpass.getpass("New password: ")
            
            if len(new_password) < 8:
                print("❌ Password must be at least 8 characters long.")
                return False
            
            confirm_password = getpass.getpass("Confirm password: ")
            
            if new_password != confirm_password:
                print("❌ Passwords don't match.")
                return False
        
        # Hash and update password
        try:
            password_hash = get_password_hash(new_password)
            user.password_hash = password_hash
            
            session.add(user)
            session.commit()
            
            print(f"✅ Password updated successfully for {user.email}")
            print("💡 User can now log in with the new password.")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update password: {e}")
            session.rollback()
            return False

def list_users():
    """List all users in the database."""
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        
        if not users:
            print("📭 No users found in the database.")
            return
        
        print(f"👥 Found {len(users)} users:")
        print("-" * 60)
        
        for user in users:
            print(f"📧 {user.email}")
            print(f"   Name: {user.name}")
            print(f"   ID: {user.id}")
            print(f"   Created: {user.created_at}")
            print(f"   Last login: {user.last_login}")
            print()

def main():
    parser = argparse.ArgumentParser(
        description="Reset user password in Reflexion Journal",
        epilog="Examples:\n"
               "  python reset_password.py --list\n"
               "  python reset_password.py user@example.com\n"
               "  python reset_password.py --email user@example.com --password newpass123",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("email", nargs="?", help="User email address")
    parser.add_argument("--email", help="User email address")
    parser.add_argument("--password", help="New password (will prompt if not provided)")
    parser.add_argument("--list", action="store_true", help="List all users")
    
    args = parser.parse_args()
    
    # Determine email from positional or named argument
    email = args.email or args.email
    
    if args.list:
        list_users()
        return
    
    if not email:
        print("❌ Please provide a user email address.")
        print("Use --help for usage information.")
        sys.exit(1)
    
    print("🔄 Resetting password for user...")
    print("=" * 40)
    
    success = reset_user_password(email, args.password)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()