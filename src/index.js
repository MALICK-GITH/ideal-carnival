require('dotenv').config();
const express = require('express');
const path = require('path');
const logger = require('./config/logger');
const { router: collectorRouter, collector } = require('./routes/collector');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Servir les fichiers statiques de l'interface web
app.use(express.static(path.join(__dirname, '../web')));

// CORS pour le développement
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.sendStatus(200);
  } else {
    next();
  }
});

// Routes
app.use('/api/collect', collectorRouter);

// Route de santé
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: '21x-win-collector',
    timestamp: new Date().toISOString(),
    collector: collector.getStatus()
  });
});

// Route racine - Rediriger vers l'interface web
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../web/index.html'));
});

// Gestion des erreurs
app.use((error, req, res, next) => {
  logger.error('❌ Erreur serveur:', error);
  res.status(500).json({
    success: false,
    message: 'Erreur interne du serveur',
    error: process.env.NODE_ENV === 'development' ? error.message : 'Erreur interne'
  });
});

// Démarrage du serveur
const startServer = async () => {
  try {
    // Création du répertoire de données si nécessaire
    const CsvStorageService = require('./services/csvStorage');
    const csvStorage = new CsvStorageService();
    await csvStorage.ensureDataDirectory();
    
    logger.info('📁 Répertoire de données vérifié');
    
    // Démarrage du serveur
    app.listen(PORT, () => {
      logger.info(`🚀 Serveur démarré sur le port ${PORT}`);
      logger.info(`🌐 Interface web: http://localhost:${PORT}`);
      logger.info('📊 Collecteur TwentyOne prêt pour 21x win (stockage CSV)');
      
      // Démarrage automatique de la collecte si configuré
      if (process.env.AUTO_START_COLLECTOR === 'true') {
        const intervalMs = parseInt(process.env.COLLECTOR_INTERVAL_MS) || 2000;
        logger.info(`🔄 Démarrage automatique de la collecte (intervalle: ${intervalMs}ms)`);
        collector.startCollection(intervalMs);
      }
    });
  } catch (error) {
    logger.error('❌ Erreur critique au démarrage:', error);
    process.exit(1);
  }
};

// Gestion de l'arrêt gracieux
process.on('SIGTERM', () => {
  logger.info('🛑 Signal SIGTERM reçu, arrêt en cours...');
  collector.stopCollection();
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('🛑 Signal SIGINT reçu, arrêt en cours...');
  collector.stopCollection();
  process.exit(0);
});

// Export pour tests
module.exports = { app, collector };

// Démarrage si exécuté directement
if (require.main === module) {
  startServer();
}
