"""
Script to create or update an administrator or operator user account.
Prompts securely for password via getpass (minimum 12 characters).
Password is NEVER accepted as a CLI parameter.
"""
import argparse
import getpass
import sys
from sqlalchemy import select

from backend.app.core.security import hash_password
from backend.app.db.session import SessionLocal
from backend.app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update an administrative user")
    parser.add_argument("--username", required=True, help="Username for the account")
    parser.add_argument("--role", default="ADMIN", choices=["ADMIN", "OPERATOR"], help="User role (ADMIN or OPERATOR)")
    parser.add_argument("--email", default=None, help="Optional email address")
    args = parser.parse_args()

    username = args.username.strip()
    if not username:
        print("Error: Username cannot be empty", file=sys.stderr)
        sys.exit(1)

    # Prompt securely for password
    print(f"Creating/updating user '{username}' with role '{args.role}'.")
    password = getpass.getpass("Enter password (minimum 12 characters): ")
    if len(password) < 12:
        print("Error: Password must be at least 12 characters long", file=sys.stderr)
        sys.exit(1)

    confirm_password = getpass.getpass("Confirm password: ")
    if password != confirm_password:
        print("Error: Passwords do not match", file=sys.stderr)
        sys.exit(1)

    pw_hash = hash_password(password)

    db = SessionLocal()
    try:
        existing_user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if existing_user:
            existing_user.password_hash = pw_hash
            existing_user.role = args.role
            if args.email:
                existing_user.email = args.email
            existing_user.is_active = True
            db.commit()
            print(f"Successfully updated user '{username}' (role: {args.role}).")
        else:
            new_user = User(
                username=username,
                email=args.email,
                password_hash=pw_hash,
                role=args.role,
                is_active=True,
            )
            db.add(new_user)
            db.commit()
            print(f"Successfully created user '{username}' (role: {args.role}).")
    except Exception as e:
        db.rollback()
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
