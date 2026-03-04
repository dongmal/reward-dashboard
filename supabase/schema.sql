-- ============================================================
-- Supabase 스키마 정의
-- E프로젝트 대시보드 - Google Sheets 대체 DB
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- 1. 포인트클릭 DB (MySQL 동기화)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pointclick_db (
    id              BIGSERIAL PRIMARY KEY,
    date            DATE        NOT NULL,
    ad_category     TEXT,
    media_type      TEXT,
    publisher_type  TEXT,
    ad_name         TEXT,
    media_name      TEXT,
    cd              TEXT,
    advertiser      TEXT,
    os              TEXT,
    ad_type         TEXT,
    unit_price      NUMERIC,
    clicks          INTEGER,
    conversions     INTEGER,
    ad_revenue      NUMERIC,
    media_cost      NUMERIC,
    media_rate      NUMERIC,
    margin          NUMERIC,
    margin_rate     NUMERIC,
    cvr             NUMERIC,
    week            TEXT,
    month           TEXT
);

CREATE INDEX IF NOT EXISTS idx_pointclick_db_date ON pointclick_db(date);

-- ─────────────────────────────────────────────────────────────
-- 2. 캐시플레이 DB (Google Sheets 동기화)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cashplay_db (
    date                    DATE    PRIMARY KEY,
    reward_paid             NUMERIC DEFAULT 0,
    reward_free             NUMERIC DEFAULT 0,
    reward_total            NUMERIC DEFAULT 0,
    game_direct             NUMERIC DEFAULT 0,
    game_dsp                NUMERIC DEFAULT 0,
    game_rs                 NUMERIC DEFAULT 0,
    game_acquisition        NUMERIC DEFAULT 0,
    game_total              NUMERIC DEFAULT 0,
    gathering_pointclick    NUMERIC DEFAULT 0,
    iaa_levelplay           NUMERIC DEFAULT 0,
    iaa_adwhale             NUMERIC DEFAULT 0,
    iaa_hubble              NUMERIC DEFAULT 0,
    iaa_total               NUMERIC DEFAULT 0,
    offerwall_adpopcorn     NUMERIC DEFAULT 0,
    offerwall_pointclick    NUMERIC DEFAULT 0,
    offerwall_ive           NUMERIC DEFAULT 0,
    offerwall_adforus       NUMERIC DEFAULT 0,
    offerwall_addison       NUMERIC DEFAULT 0,
    offerwall_adjo          NUMERIC DEFAULT 0,
    offerwall_total         NUMERIC DEFAULT 0
);

-- ─────────────────────────────────────────────────────────────
-- 3. 포인트클릭 GA4 이벤트 데이터
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pointclick_ga (
    id                          BIGSERIAL PRIMARY KEY,
    date                        DATE    NOT NULL,
    "eventName"                 TEXT,
    "pageTitle"                 TEXT,
    "pagePath"                  TEXT,
    page_name                   TEXT,
    page_type                   TEXT,
    media_key                   TEXT,
    media_name                  TEXT,
    "eventCount"                NUMERIC,
    sessions                    NUMERIC,
    "screenPageViews"           NUMERIC,
    "averageSessionDuration"    NUMERIC,
    "engagementRate"            NUMERIC,
    "userEngagementDuration"    NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_pointclick_ga_date ON pointclick_ga(date);

-- ─────────────────────────────────────────────────────────────
-- 4. 포인트클릭 GA4 사용자 지표 (DAU/WAU/MAU)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pointclick_ga_user (
    date                DATE    PRIMARY KEY,
    "activeUsers"       NUMERIC,
    "active7DayUsers"   NUMERIC,
    "active28DayUsers"  NUMERIC,
    "newUsers"          NUMERIC,
    sessions            NUMERIC
);

-- ─────────────────────────────────────────────────────────────
-- 5. 캐시플레이 GA4 이벤트 데이터
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cashplay_ga (
    id                          BIGSERIAL PRIMARY KEY,
    date                        DATE    NOT NULL,
    "eventName"                 TEXT,
    "pageTitle"                 TEXT,
    "pagePath"                  TEXT,
    page                        TEXT,
    page_type                   TEXT,
    button_id                   TEXT,
    "eventCount"                NUMERIC,
    sessions                    NUMERIC,
    "screenPageViews"           NUMERIC,
    "averageSessionDuration"    NUMERIC,
    "engagementRate"            NUMERIC,
    "userEngagementDuration"    NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_cashplay_ga_date ON cashplay_ga(date);

-- ─────────────────────────────────────────────────────────────
-- 6. 캐시플레이 GA4 사용자 지표 (DAU/WAU/MAU)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cashplay_ga_user (
    date                DATE    PRIMARY KEY,
    "activeUsers"       NUMERIC,
    "active7DayUsers"   NUMERIC,
    "active28DayUsers"  NUMERIC,
    "newUsers"          NUMERIC,
    sessions            NUMERIC
);

-- ─────────────────────────────────────────────────────────────
-- 7. 매체 마스터 (MySQL media 테이블 동기화)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS media_master (
    media_key   TEXT PRIMARY KEY,
    media_name  TEXT NOT NULL
);

-- ─────────────────────────────────────────────────────────────
-- RLS (Row Level Security) - 대시보드는 service_role key 사용으로
-- 별도 정책 없이 접근 가능. 필요 시 아래 주석 해제하여 설정.
-- ─────────────────────────────────────────────────────────────
-- ALTER TABLE pointclick_db ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cashplay_db ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE pointclick_ga ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE pointclick_ga_user ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cashplay_ga ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cashplay_ga_user ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE media_master ENABLE ROW LEVEL SECURITY;
