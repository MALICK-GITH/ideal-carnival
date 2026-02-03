const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'oracxpred_twentyone',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Création de la table twentyone_rounds
const createTables = async () => {
  const createTableQuery = `
    CREATE TABLE IF NOT EXISTS twentyone_rounds (
      id SERIAL PRIMARY KEY,
      event_id BIGINT NOT NULL,
      collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      option_type VARCHAR(50),
      odd DECIMAL(10, 4),
      round_state JSONB,
      raw_payload JSONB,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_twentyone_rounds_event_collected ON twentyone_rounds(event_id, collected_at);
    CREATE INDEX IF NOT EXISTS idx_twentyone_rounds_collected_at ON twentyone_rounds(collected_at);
  `;

  try {
    await pool.query(createTableQuery);
    console.log('✅ Tables twentyone_rounds créées avec succès');
  } catch (error) {
    console.error('❌ Erreur lors de la création des tables:', error);
    throw error;
  }
};

module.exports = {
  pool,
  createTables
};
