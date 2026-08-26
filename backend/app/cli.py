"""Small operational CLI -- currently just seeding the first admin user.
There is no self-registration (spec Section 21/48), so an operator needs a
way to create the first account. Run inside the backend container/pod:

    python -m app.cli create-admin --username root --password <pw>
"""

import argparse
import sys

from app.auth.security import hash_password
from app.database import SessionLocal
from app.models import User


def create_admin(username: str, password: str) -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            print(f"User '{username}' already exists.", file=sys.stderr)
            sys.exit(1)
        user = User(username=username, password_hash=hash_password(password), is_admin=True)
        db.add(user)
        db.commit()
        print(f"Created admin user '{username}'.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin_parser = subparsers.add_parser("create-admin", help="Create the first admin user")
    create_admin_parser.add_argument("--username", required=True)
    create_admin_parser.add_argument("--password", required=True)

    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.username, args.password)


if __name__ == "__main__":
    main()
