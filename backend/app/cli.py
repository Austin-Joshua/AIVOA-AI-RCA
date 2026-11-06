import sys
import os
import argparse
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_engine
from app.services.admin_provisioning import provision_admin_account
from app.models.investigation import Investigation
from app.models.audit import AuditLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aivoa-rca.cli")

def get_session_factory():
    get_engine()
    from app.core.database import AsyncSessionLocal
    return AsyncSessionLocal

async def run_provision_admin(args):
    username = args.username or settings.INITIAL_ADMIN_USERNAME
    password = args.password or settings.INITIAL_ADMIN_PASSWORD
    email = args.email or settings.INITIAL_ADMIN_EMAIL
    full_name = args.full_name or settings.INITIAL_ADMIN_FULL_NAME

    if not username or not password:
        sys.stderr.write(
            "ADMIN provisioning error: Both username and password are required. "
            "Provide --username and --password CLI options or set INITIAL_ADMIN_USERNAME and "
            "INITIAL_ADMIN_PASSWORD in environment variables.\n"
        )
        return 1

    SessionLocal = get_session_factory()
    async with SessionLocal() as db:
        result = await provision_admin_account(
            db=db,
            username=username,
            password=password,
            email=email,
            full_name=full_name
        )

        if result.get("success"):
            sys.stdout.write(
                f"Success: Administrator account '{result['username']}' provisioned successfully "
                f"with role ADMIN (User ID #{result['user_id']}).\n"
            )
            return 0
        elif result.get("already_exists"):
            sys.stdout.write(
                f"Notice: Administrator account '{result['username']}' already exists. "
                "Existing credentials preserved without modification.\n"
            )
            return 0
        else:
            sys.stderr.write(f"Provisioning failed: {result.get('error', 'Unknown error')}\n")
            return 1

async def run_reset_demo(args):
    """
    Safely reset demo investigations:
    - Strictly refuses to run in production environments
    - Soft-archives all non-archived investigations (never performs destructive SQL deletes)
    - Creates an attributable audit trail entry for each archived record
    - Leaves the database clean for demo recording runs
    """
    env = (getattr(settings, "ENVIRONMENT", "") or "").lower()
    if env in ("production", "prod"):
        sys.stderr.write("ERROR: Demo reset is forbidden in production environments.\n")
        return 1

    SessionLocal = get_session_factory()
    async with SessionLocal() as db:
        stmt = select(Investigation).where(Investigation.status != "ARCHIVED")
        result = await db.execute(stmt)
        active_invs = result.scalars().all()

        archived_count = 0
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        for inv in active_invs:
            inv.status = "ARCHIVED"
            inv.updated_at = now_utc
            audit = AuditLog(
                investigation_id=inv.id,
                user_id=None,
                user_name="CLI Admin (Demo Reset)",
                action="ARCHIVED",
                entity_type="INVESTIGATION",
                entity_id=str(inv.id),
                change_summary=f"Investigation archived by CLI demo reset for clean scenario run",
                timestamp=now_utc
            )
            db.add(audit)
            archived_count += 1

        await db.commit()
        sys.stdout.write(
            f"Success: Archived {archived_count} active investigation(s). "
            f"Zero records deleted. Database is clean for demo recording.\n"
        )
        return 0

def main():
    parser = argparse.ArgumentParser(
        prog="aivoa-cli",
        description="AIVOA.AI RCA Intelligence Administrative CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: provision-admin
    admin_parser = subparsers.add_parser(
        "provision-admin",
        help="Securely provision an initial administrator account"
    )
    admin_parser.add_argument("--username", "-u", type=str, help="Administrator username")
    admin_parser.add_argument("--password", "-p", type=str, help="Administrator password (min 10 characters)")
    admin_parser.add_argument("--email", "-e", type=str, help="Administrator email address")
    admin_parser.add_argument("--full-name", "-n", type=str, help="Full display name")

    # Command: reset-demo
    reset_parser = subparsers.add_parser(
        "reset-demo",
        help="Archive prior demo investigations for clean scenario demonstration"
    )

    parsed = parser.parse_args()

    if parsed.command == "provision-admin":
        exit_code = asyncio.run(run_provision_admin(parsed))
        sys.exit(exit_code)
    elif parsed.command == "reset-demo":
        exit_code = asyncio.run(run_reset_demo(parsed))
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
