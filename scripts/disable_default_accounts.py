"""Disable the historical demo accounts that shipped with published passwords.

The application no longer creates these accounts, but an existing database
(production included) still contains them. This script only deactivates an
account when its *current* password still matches the published default, so
an account whose password was already rotated is left untouched.

Accounts are disabled rather than deleted because orders keep a foreign key
to their user.

Usage:
    python scripts/disable_default_accounts.py           # dry run (default)
    python scripts/disable_default_accounts.py --apply   # actually disable
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import verify_password  # noqa: E402
from database import SessionLocal  # noqa: E402
from models import User, UserRole  # noqa: E402

PUBLISHED_DEFAULTS = {
    "admin": "Admin123!",
    "manager": "Manager123!",
    "staff": "Staff123!",
    "viewer": "Viewer123!",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="disable the accounts (default is a dry run)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="apply even if no active administrator would remain",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        to_disable = []

        for username, default_password in PUBLISHED_DEFAULTS.items():
            user = db.query(User).filter(User.username == username).first()
            if user is None:
                print(f"- {username:8s} absent")
                continue
            if not verify_password(default_password, user.hashed_password):
                print(f"- {username:8s} password already changed, left untouched")
                continue
            to_disable.append(user)
            print(f"- {username:8s} still uses the published default password")

        if not to_disable:
            print("Nothing to do.")
            return 0

        # Never lock the instance out: check the administrators that would
        # remain active once the vulnerable accounts are disabled.
        disabled_ids = {user.id for user in to_disable}
        remaining_admins = (
            db.query(User)
            .filter(
                User.role == UserRole.ADMIN,
                User.is_active.is_(True),
                User.id.notin_(disabled_ids),
            )
            .count()
        )

        if remaining_admins == 0 and not args.force:
            print(
                "\nRefusing to continue: no active administrator would remain.\n"
                "Create a new admin first (set BOOTSTRAP_ADMIN_EMAIL and\n"
                "BOOTSTRAP_ADMIN_PASSWORD, restart the API), then run this script again."
            )
            return 1

        if not args.apply:
            print(f"\nDry run: {len(to_disable)} account(s) would be disabled.")
            print("Re-run with --apply to disable them.")
            return 0

        for user in to_disable:
            user.is_active = False
        db.commit()
        print(f"\n{len(to_disable)} account(s) disabled.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
