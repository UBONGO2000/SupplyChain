"""Operational CLI
=================
Small command-line helpers that do not belong in the HTTP API:

    python -m cli seed-demo            # populate demo warehouses/products/orders
    python -m cli create-demo-user     # create or rotate the read/write demo account

The commands are also used by the Docker entrypoint, so a fresh
`docker compose up` gives a usable demo without any manual SQL.
"""

import argparse
import os
import secrets
import string
import sys

from pydantic import ValidationError
from sqlalchemy import or_
from sqlalchemy.orm import Session

import database
import models
from auth import get_password_hash
from schema import UserCreate

DEFAULT_DEMO_EMAIL = "demo@example.com"
DEFAULT_DEMO_USERNAME = "demo"
DEFAULT_DEMO_ROLE = models.UserRole.STAFF
PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"


def generate_password(length: int = 20) -> str:
    """Generate a strong random password that satisfies the API policy."""
    if length < 12:
        raise ValueError("A demo password must be at least 12 characters long")

    while True:
        password = "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))
        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
        ):
            return password


def validate_password(password: str) -> None:
    """Reject weak passwords using the same rules as public registration."""
    try:
        UserCreate(
            email=DEFAULT_DEMO_EMAIL,
            username=DEFAULT_DEMO_USERNAME,
            password=password,
        )
    except ValidationError as exc:
        messages = "; ".join(error["msg"] for error in exc.errors())
        raise SystemExit(f"Invalid password: {messages}") from exc


def create_demo_user(
    db: Session,
    *,
    email: str = DEFAULT_DEMO_EMAIL,
    username: str = DEFAULT_DEMO_USERNAME,
    role: models.UserRole = DEFAULT_DEMO_ROLE,
    password: str | None = None,
    rotate: bool = True,
) -> tuple[models.User, str | None]:
    """Create the demo account, or rotate its password when it exists.

    Returns ``(user, password)``. The password is ``None`` when the account
    already existed and ``rotate`` is False.
    """
    password = password or generate_password()
    validate_password(password)

    existing = (
        db.query(models.User)
        .filter(
            or_(
                models.User.email == email,
                models.User.username == username,
            )
        )
        .first()
    )

    if existing:
        if not rotate:
            return existing, None

        existing.email = email
        existing.username = username
        existing.hashed_password = get_password_hash(password)
        existing.role = role
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing, password

    user = models.User(
        email=email,
        username=username,
        hashed_password=get_password_hash(password),
        full_name="Demo Account",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, password


def _cmd_seed_demo(_args: argparse.Namespace) -> int:
    from seed_data import seed_demo_data

    return 0 if seed_demo_data() else 1


def _cmd_create_demo_user(args: argparse.Namespace) -> int:
    email = args.email or os.getenv("DEMO_USER_EMAIL", DEFAULT_DEMO_EMAIL)
    username = args.username or os.getenv("DEMO_USER_USERNAME", DEFAULT_DEMO_USERNAME)
    password = args.password or os.getenv("DEMO_USER_PASSWORD")
    role = models.UserRole[args.role.upper()]

    db = database.SessionLocal()
    try:
        user, new_password = create_demo_user(
            db,
            email=email,
            username=username,
            role=role,
            password=password,
        )
    finally:
        db.close()

    print(f"Demo account ready: {user.username} <{user.email}> ({user.role.value})")
    if new_password:
        print(f"Password: {new_password}")
    else:
        print("Password unchanged.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cli",
        description="Operational commands for the Supply Chain API.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser(
        "seed-demo",
        help="Insert the idempotent demo dataset (no-op if data exists).",
    )
    seed.set_defaults(func=_cmd_seed_demo)

    demo_user = subparsers.add_parser(
        "create-demo-user",
        help="Create the demo account or rotate its password.",
    )
    demo_user.add_argument(
        "--email",
        default=None,
        help=f"Account email (default: $DEMO_USER_EMAIL or {DEFAULT_DEMO_EMAIL}).",
    )
    demo_user.add_argument(
        "--username",
        default=None,
        help=f"Account username (default: $DEMO_USER_USERNAME or {DEFAULT_DEMO_USERNAME}).",
    )
    demo_user.add_argument(
        "--password",
        default=None,
        help="Explicit password (default: $DEMO_USER_PASSWORD or random).",
    )
    demo_user.add_argument(
        "--role",
        default=DEFAULT_DEMO_ROLE.name,
        choices=[role.name.lower() for role in models.UserRole],
        help=f"Role to grant (default: {DEFAULT_DEMO_ROLE.name.lower()}).",
    )
    demo_user.set_defaults(func=_cmd_create_demo_user)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
