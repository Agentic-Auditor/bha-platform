-- BHA Platform Database Schema v2.0
-- SQLite for MVP.
--
-- v2 changes vs v1:
--   - narrative_cache table added (AI narrative caching)
--   - context_json column added to assessments (onboarding C1/C2/C3, not scored)
--   - answers.step column retained but unused in v2 flow (all answers step=1)
--   - assessments.step2_completed_at retained for backward compat
--
-- v3 changes (Membership System):
--   - users table: email-based identity, membership status + expiry, user_token
--   - membership_payments table: 890 THB/year PromptPay slip + admin approve flow

CREATE TABLE IF NOT EXISTS assessments (
  id                   TEXT PRIMARY KEY,
  session_token        TEXT NOT NULL,
  business_type        TEXT NOT NULL,
  business_name        TEXT,
  email                TEXT,
  context_json         TEXT,
  status               TEXT NOT NULL DEFAULT 'STARTED',
  step1_completed_at   TEXT,
  step2_completed_at   TEXT,
  created_at           TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_assessments_email ON assessments(email);
CREATE INDEX IF NOT EXISTS idx_assessments_token ON assessments(session_token);

CREATE TABLE IF NOT EXISTS answers (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  assessment_id   TEXT NOT NULL REFERENCES assessments(id),
  question_id     TEXT NOT NULL,
  score           INTEGER NOT NULL CHECK(score BETWEEN 0 AND 3),
  step            INTEGER NOT NULL DEFAULT 1,
  answered_at     TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(assessment_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_answers_assessment ON answers(assessment_id);

CREATE TABLE IF NOT EXISTS results (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  assessment_id   TEXT NOT NULL UNIQUE REFERENCES assessments(id),
  d1_raw INTEGER, d2_raw INTEGER, d3_raw INTEGER, d4_raw INTEGER,
  d5_raw INTEGER, d6_raw INTEGER, d7_raw INTEGER,
  d1_pct REAL, d2_pct REAL, d3_pct REAL, d4_pct REAL,
  d5_pct REAL, d6_pct REAL, d7_pct REAL,
  d1_light TEXT, d2_light TEXT, d3_light TEXT, d4_light TEXT,
  d5_light TEXT, d6_light TEXT, d7_light TEXT,
  overall_score   REAL NOT NULL,
  overall_grade   TEXT NOT NULL,
  red_flags       TEXT,
  red_flag_count  INTEGER NOT NULL DEFAULT 0,
  calculated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payments (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  assessment_id    TEXT NOT NULL REFERENCES assessments(id),
  amount           REAL NOT NULL DEFAULT 499.00,
  slip_url         TEXT,
  slip_uploaded_at TEXT,
  status           TEXT NOT NULL DEFAULT 'pending',
  verified_at      TEXT,
  verified_by      TEXT,
  reject_reason    TEXT,
  notes            TEXT,
  created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- narrative_cache: AI-generated narrative prose cached by pattern signature.
-- pattern_hash = sha256[:16] of (dim + sorted_pattern_codes + business_type
--                                + age_bucket + revenue_bucket).
-- Same inputs always produce same hash, same cached narrative returned.

CREATE TABLE IF NOT EXISTS narrative_cache (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  pattern_hash   TEXT NOT NULL UNIQUE,
  dim            TEXT NOT NULL,
  patterns       TEXT NOT NULL,
  business_type  TEXT NOT NULL,
  age_bucket     TEXT,
  revenue_bucket TEXT,
  narrative      TEXT NOT NULL,
  model          TEXT NOT NULL DEFAULT 'claude-haiku-4-5',
  hit_count      INTEGER NOT NULL DEFAULT 0,
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  last_hit_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_narrative_cache_hash ON narrative_cache(pattern_hash);
CREATE INDEX IF NOT EXISTS idx_narrative_cache_dim  ON narrative_cache(dim);

-- ── Membership System (v3) ──────────────────────────────────────────────────

-- users: email-based identity, no password.
-- user_token is a UUID issued on login/register, stored as httpOnly cookie.
-- membership_status: 'free' | 'member'
-- membership_expires_at: NULL for free users, ISO datetime for paid members.

CREATE TABLE IF NOT EXISTS users (
  id                    TEXT PRIMARY KEY,
  email                 TEXT NOT NULL UNIQUE,
  name                  TEXT,
  user_token            TEXT NOT NULL UNIQUE,
  membership_status     TEXT NOT NULL DEFAULT 'free',
  membership_expires_at TEXT,
  created_at            TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_users_email      ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_token      ON users(user_token);

-- membership_payments: PromptPay QR slip submission for 890 THB/year.
-- On admin approve: users.membership_status = 'member', membership_expires_at = now+365d.

CREATE TABLE IF NOT EXISTS membership_payments (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id          TEXT NOT NULL REFERENCES users(id),
  amount           REAL NOT NULL DEFAULT 890.00,
  slip_url         TEXT,
  slip_uploaded_at TEXT,
  status           TEXT NOT NULL DEFAULT 'pending',
  verified_at      TEXT,
  verified_by      TEXT,
  reject_reason    TEXT,
  notes            TEXT,
  created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_membership_payments_user   ON membership_payments(user_id);
CREATE INDEX IF NOT EXISTS idx_membership_payments_status ON membership_payments(status);
