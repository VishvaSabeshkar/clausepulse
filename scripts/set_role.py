"""Grant or remove the admin role. LOCAL ONLY: uses the master Firebase key.

Usage:
    python scripts/set_role.py EMAIL admin  --key PATH
    python scripts/set_role.py EMAIL viewer --key PATH
    python scripts/set_role.py --list-admins --key PATH

The master key never goes to Vercel or into the repo (security.md §4).
"""

import argparse
import os
import sys

import firebase_admin
from firebase_admin import auth, credentials

KEY_ENV_VAR = "FIREBASE_ADMIN_KEY_PATH"


def init_firebase(key_path: str) -> None:
    if not os.path.isfile(key_path):
        sys.exit(f"Key file not found: {key_path}")
    firebase_admin.initialize_app(credentials.Certificate(key_path))


def set_role(email: str, role: str) -> None:
    try:
        user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        sys.exit(f"No Firebase user with email {email}. Sign up first.")

    # "viewer" means NO claim at all, matching the backend rule
    # "missing claim = viewer", so there is only one way to be a viewer.
    claims = {"role": "admin"} if role == "admin" else None
    auth.set_custom_user_claims(user.uid, claims)
    print(f"{email} ({user.uid}) is now: {role}")
    print("They must sign in again (or refresh their token) to get the new role.")


def list_admins() -> None:
    count = 0
    for user in auth.list_users().iterate_all():
        if (user.custom_claims or {}).get("role") == "admin":
            print(f"admin: {user.email} ({user.uid})")
            count += 1
    print(f"{count} admin(s) total")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set a ClausePulse user's role.")
    parser.add_argument("email", nargs="?", help="the user's sign-in email")
    parser.add_argument("role", nargs="?", choices=["admin", "viewer"])
    parser.add_argument("--list-admins", action="store_true")
    parser.add_argument(
        "--key",
        default=os.environ.get(KEY_ENV_VAR),
        help=f"path to the master key JSON (or set {KEY_ENV_VAR})",
    )
    args = parser.parse_args()

    if not args.key:
        parser.error(f"pass --key PATH or set {KEY_ENV_VAR}")
    init_firebase(args.key)

    if args.list_admins:
        list_admins()
    elif args.email and args.role:
        set_role(args.email, args.role)
    else:
        parser.error("give EMAIL and ROLE, or use --list-admins")


if __name__ == "__main__":
    main()
