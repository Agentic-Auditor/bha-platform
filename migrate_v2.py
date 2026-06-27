"""
migrate_v2.py — Safe migration from BHA Platform v1 → v2.

Run once on an existing production database:
    python migrate_v2.py

What this does:
  1. Adds narrative_cache table (new in v2)
  2. Adds context_json column to assessments if missing
  3. Adds idx_answers_assessment index if missing
  4. Adds CHECK constraint note (SQLite can't add constraints; documented only)
  5. Verifies the migration completed correctly

Idempotent: safe to run multiple times.
"""

import os
import sys
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "bha.db")


def run():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        print("   Set DB_PATH env var or run from the BHA_Platform directory.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    steps_done = 0
    steps_skipped = 0

    # ── Step 1: Add context_json to assessments ──────────────────────────────
    cols = {row[1] for row in conn.execute("PRAGMA table_info(assessments)")}
    if "context_json" not in cols:
        conn.execute("ALTER TABLE assessments ADD COLUMN context_json TEXT")
        conn.commit()
        print("✅ Added context_json column to assessments")
        steps_done += 1
    else:
        print("⏭  context_json already present in assessments")
        steps_skipped += 1

    # ── Step 2: Create narrative_cache table ─────────────────────────────────
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    if "narrative_cache" not in tables:
        conn.executescript("""
            CREATE TABLE narrative_cache (
              id            INTEGER PRIMARY KEY AUTOINCREMENT,
              pattern_hash  TEXT NOT NULL UNIQUE,
              dim           TEXT NOT NULL,
              patterns      TEXT NOT NULL,
              business_type TEXT NOT NULL,
              age_bucket    TEXT,
              revenue_bucket TEXT,
              narrative     TEXT NOT NULL,
              model         TEXT NOT NULL DEFAULT 'claude-haiku-4-5',
              hit_count     INTEGER NOT NULL DEFAULT 0,
              created_at    TEXT NOT NULL DEFAULT (datetime('now')),
              last_hit_at   TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_narrative_cache_hash
              ON narrative_cache(pattern_hash);

            CREATE INDEX IF NOT EXISTS idx_narrative_cache_dim
              ON narrative_cache(dim);
        """)
        conn.commit()
        print("✅ Created narrative_cache table + indexes")
        steps_done += 1
    else:
        print("⏭  narrative_cache table already exists")
        steps_skipped += 1

    # ── Step 3: Add idx_answers_assessment index if missing ──────────────────
    indexes = {row[1] for row in conn.execute(
        "SELECT * FROM sqlite_master WHERE type='index'"
    )}
    if "idx_answers_assessment" not in indexes:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_answers_assessment ON answers(assessment_id)"
        )
        conn.commit()
        print("✅ Added idx_answers_assessment index")
        steps_done += 1
    else:
        print("⏭  idx_answers_assessment already exists")
        steps_skipped += 1

    # ── Verification ─────────────────────────────────────────────────────────
    print()
    print("── Verification ────────────────────────────────────────")

    # Check narrative_cache exists and has expected columns
    cache_cols = {row[1] for row in conn.execute("PRAGMA table_info(narrative_cache)")}
    expected = {"pattern_hash", "dim", "patterns", "business_type", "narrative",
                "hit_count", "created_at", "age_bucket", "revenue_bucket", "model"}
    missing = expected - cache_cols
    if missing:
        print(f"❌ narrative_cache missing columns: {missing}")
    else:
        print("✅ narrative_cache schema correct")

    # Check assessments has context_json
    assess_cols = {row[1] for row in conn.execute("PRAGMA table_info(assessments)")}
    if "context_json" in assess_cols:
        print("✅ assessments.context_json present")
    else:
        print("❌ assessments.context_json still missing")

    conn.close()

    print()
    print(f"Done. {steps_done} change(s) applied, {steps_skipped} already up to date.")
    print()
    print("Next: restart the Flask server so init_db() picks up the new schema.")


if __name__ == "__main__":
    run()
