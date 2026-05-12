"""
db/seed.py
One-shot seeder — populates county_profiles in Supabase.

Usage
-----
  # From the project root (with .env loaded):
  python -m db.seed

  # With --dry-run to preview without writing:
  python -m db.seed --dry-run

  # Force re-seed even if rows already exist:
  python -m db.seed --force

What it does
------------
  Reads COUNTY_PROFILES from db/county_data.py and upserts every row
  into the Supabase county_profiles table using ON CONFLICT (county, farm_type).
  Safe to run multiple times — idempotent.
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv
from pathlib import Path

# Load .env before importing settings
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from core.config import settings          # noqa: E402
from db.county_data import COUNTY_PROFILES  # noqa: E402


def _client():
    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase-py not installed. Run: pip install supabase")
        sys.exit(1)

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def seed(dry_run: bool = False, force: bool = False) -> None:
    print(f"[seed] {len(COUNTY_PROFILES)} rows to upsert into county_profiles.")

    if dry_run:
        print("[seed] DRY RUN — nothing will be written.")
        for row in COUNTY_PROFILES:
            print(f"  {row['county']:<20} {row['farm_type']:<10} "
                  f"{row['soil_type']:<8} {row['avg_rainfall']}mm "
                  f"{row['avg_temp']}°C  → {row['recommendation']}")
        return

    client = _client()

    if not force:
        # Quick check: if table already has rows, bail unless --force
        existing = client.table("county_profiles").select("id").limit(1).execute()
        if existing.data:
            print("[seed] county_profiles already has data. Use --force to re-seed.")
            return

    # Upsert all rows (ON CONFLICT (county, farm_type) DO UPDATE SET ...)
    # Supabase upsert with on_conflict resolves to the UNIQUE constraint column list
    result = (
        client
        .table("county_profiles")
        .upsert(COUNTY_PROFILES, on_conflict="county,farm_type")
        .execute()
    )

    inserted = len(result.data) if result.data else 0
    print(f"[seed] Done. {inserted} rows written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed county_profiles table.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print rows without writing to Supabase.")
    parser.add_argument("--force", action="store_true",
                        help="Re-seed even if rows already exist.")
    args = parser.parse_args()

    seed(dry_run=args.dry_run, force=args.force)
