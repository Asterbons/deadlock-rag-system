-- Patches reference table
CREATE TABLE IF NOT EXISTS patches (
    patch_id        SERIAL PRIMARY KEY,
    patch_date      DATE NOT NULL UNIQUE,
    patch_name      VARCHAR(100),
    is_balance_patch BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Matches
CREATE TABLE IF NOT EXISTS matches (
    match_id        BIGINT PRIMARY KEY,
    start_time      TIMESTAMPTZ NOT NULL,
    duration_s      INTEGER,
    match_mode      VARCHAR(20) NOT NULL,
    match_outcome   VARCHAR(20),
    winning_team    VARCHAR(10),
    badge_team0     INTEGER,
    badge_team1     INTEGER,
    badge_avg       INTEGER GENERATED ALWAYS AS
                    ((badge_team0 + badge_team1) / 2) STORED,
    patch_date      DATE REFERENCES patches(patch_date),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matches_patch
    ON matches(patch_date);
CREATE INDEX IF NOT EXISTS idx_matches_mode_patch
    ON matches(match_mode, patch_date);
CREATE INDEX IF NOT EXISTS idx_matches_start_time
    ON matches(start_time DESC);

-- Players (one row per player per match)
CREATE TABLE IF NOT EXISTS players (
    id              BIGSERIAL PRIMARY KEY,
    match_id        BIGINT NOT NULL REFERENCES matches(match_id),
    player_slot     INTEGER NOT NULL,
    hero_id         INTEGER NOT NULL,
    team            VARCHAR(10),
    won             BOOLEAN NOT NULL,
    kills           INTEGER DEFAULT 0,
    deaths          INTEGER DEFAULT 0,
    assists         INTEGER DEFAULT 0,
    net_worth       INTEGER DEFAULT 0,
    player_level    INTEGER DEFAULT 0,
    match_mode      VARCHAR(20),
    patch_date      DATE REFERENCES patches(patch_date),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (match_id, player_slot)
);

CREATE INDEX IF NOT EXISTS idx_players_hero_patch
    ON players(hero_id, patch_date);
CREATE INDEX IF NOT EXISTS idx_players_match
    ON players(match_id);
CREATE INDEX IF NOT EXISTS idx_players_mode_patch
    ON players(match_mode, patch_date);

-- Item purchases (one row per item per player per match)
CREATE TABLE IF NOT EXISTS item_purchases (
    id              BIGSERIAL PRIMARY KEY,
    match_id        BIGINT NOT NULL REFERENCES matches(match_id),
    hero_id         INTEGER NOT NULL,
    item_id         BIGINT NOT NULL,
    game_time_s     INTEGER NOT NULL,
    sold            BOOLEAN DEFAULT false,
    won             BOOLEAN NOT NULL,
    match_mode      VARCHAR(20),
    patch_date      DATE REFERENCES patches(patch_date),
    UNIQUE (match_id, hero_id, item_id, game_time_s)
);

CREATE INDEX IF NOT EXISTS idx_items_hero_item_patch
    ON item_purchases(hero_id, item_id, patch_date);
CREATE INDEX IF NOT EXISTS idx_items_hero_patch
    ON item_purchases(hero_id, patch_date);
CREATE INDEX IF NOT EXISTS idx_items_match
    ON item_purchases(match_id);

-- Pre-computed meta (updated by aggregator, read by API)
CREATE TABLE IF NOT EXISTS hero_meta (
    id              BIGSERIAL PRIMARY KEY,
    patch_date      DATE NOT NULL REFERENCES patches(patch_date),
    match_mode      VARCHAR(20) NOT NULL,
    hero_id         INTEGER NOT NULL,
    total_matches   INTEGER NOT NULL,
    win_rate        NUMERIC(5,4),
    pick_rate       NUMERIC(5,4),
    avg_kills       NUMERIC(5,2),
    avg_deaths      NUMERIC(5,2),
    avg_assists     NUMERIC(5,2),
    avg_net_worth   NUMERIC(10,2),
    avg_duration_s  NUMERIC(8,2),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (patch_date, match_mode, hero_id)
);

CREATE TABLE IF NOT EXISTS item_meta (
    id              BIGSERIAL PRIMARY KEY,
    patch_date      DATE NOT NULL REFERENCES patches(patch_date),
    match_mode      VARCHAR(20) NOT NULL,
    hero_id         INTEGER NOT NULL,
    item_id         BIGINT NOT NULL,
    total_picks     INTEGER NOT NULL,
    pick_rate       NUMERIC(5,4),
    win_rate        NUMERIC(5,4),
    avg_purchase_min NUMERIC(6,2),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (patch_date, match_mode, hero_id, item_id)
);
