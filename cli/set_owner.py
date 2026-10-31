"""Make one user the household owner (the only person who sees Admin).

Run once inside the app container:
    python -m cli.set_owner <email>
Undo with:
    python -m cli.set_owner <email> --remove
"""
import argparse
import sys

from data.db.db import SessionLocal
from data.db.models.models import User


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email")
    parser.add_argument("--remove", action="store_true", help="take the owner flag away")
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email.strip()).first()
        if not user:
            print("No user with that email.", file=sys.stderr)
            return 1
        user.is_owner = not args.remove
        db.commit()
        owners = db.query(User).filter(User.is_owner.is_(True)).count()
        print(f"User {user.id} is {'no longer' if args.remove else 'now'} the owner. Owners: {owners}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
