-- Script d'initialisation pour la base de données ORACXPRED MÉTAPHORE
-- TwentyOne Data Collector

-- Création de la base de données si nécessaire
-- CREATE DATABASE oracxpred_twentyone;

-- Extension pour les types JSONB
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table principale pour les données TwentyOne
CREATE TABLE IF NOT EXISTS twentyone_rounds (
    id SERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    option_type VARCHAR(50),
    odd DECIMAL(10, 4),
    round_state JSONB,
    raw_payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour optimiser les performances
CREATE INDEX IF NOT EXISTS idx_twentyone_rounds_event_collected 
    ON twentyone_rounds(event_id, collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_twentyone_rounds_collected_at 
    ON twentyone_rounds(collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_twentyone_rounds_event_id 
    ON twentyone_rounds(event_id);

CREATE INDEX IF NOT EXISTS idx_twentyone_rounds_option_type 
    ON twentyone_rounds(option_type);

-- Index pour les requêtes JSONB
CREATE INDEX IF NOT EXISTS idx_twentyone_rounds_state_gin 
    ON twentyone_rounds USING GIN(round_state);

-- Trigger pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_twentyone_rounds_updated_at 
    BEFORE UPDATE ON twentyone_rounds 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Table de statistiques pour monitoring
CREATE TABLE IF NOT EXISTS collection_stats (
    id SERIAL PRIMARY KEY,
    collection_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    events_found INTEGER DEFAULT 0,
    events_processed INTEGER DEFAULT 0,
    options_saved INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    collection_duration_ms INTEGER,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_collection_stats_time 
    ON collection_stats(collection_time DESC);

-- Vue pour les données récentes
CREATE OR REPLACE VIEW recent_twentyone_data AS
SELECT 
    event_id,
    collected_at,
    option_type,
    odd,
    round_state,
    created_at
FROM twentyone_rounds 
ORDER BY collected_at DESC 
LIMIT 1000;

-- Fonction de nettoyage (optionnel)
CREATE OR REPLACE FUNCTION cleanup_old_data(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM twentyone_rounds 
    WHERE collected_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adapter selon votre utilisateur)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;

COMMENT ON TABLE twentyone_rounds IS 'Données collectées pour le jeu TwentyOne - ORACXPRED MÉTAPHORE';
COMMENT ON COLUMN twentyone_rounds.event_id IS 'Identifiant unique de l''événement TwentyOne';
COMMENT ON COLUMN twentyone_rounds.collected_at IS 'Timestamp de collecte des données';
COMMENT ON COLUMN twentyone_rounds.option_type IS 'Type d''option de pari (Player, Banker, Tie, etc.)';
COMMENT ON COLUMN twentyone_rounds.odd IS 'Cote associée à l''option';
COMMENT ON COLUMN twentyone_rounds.round_state IS 'État du round au moment de la collecte';
COMMENT ON COLUMN twentyone_rounds.raw_payload IS 'Payload JSON brut de l''API 1xBet';

COMMENT ON TABLE collection_stats IS 'Statistiques de collecte pour monitoring';
COMMENT ON VIEW recent_twentyone_data IS 'Vue des 1000 dernières entrées TwentyOne';
