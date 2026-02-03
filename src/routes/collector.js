const express = require('express');
const DataCollectorService = require('../services/dataCollector');
const logger = require('../config/logger');

const router = express.Router();
const collector = new DataCollectorService();

// Endpoint interne pour déclencher la collecte
router.post('/21', async (req, res) => {
  try {
    logger.info('📡 Endpoint /api/collect/21 appelé');
    const result = await collector.collectTwentyOne();
    
    res.json({
      success: true,
      message: 'Collecte TwentyOne terminée',
      data: result,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('❌ Erreur endpoint /api/collect/21:', error.message);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de la collecte',
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// Endpoint pour démarrer la collecte automatique
router.post('/21/start', async (req, res) => {
  try {
    const intervalMs = req.body.intervalMs || parseInt(process.env.COLLECTOR_INTERVAL_MS) || 2000;
    
    collector.startCollection(intervalMs);
    
    res.json({
      success: true,
      message: `Collecte automatique démarrée (intervalle: ${intervalMs}ms)`,
      status: collector.getStatus(),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('❌ Erreur démarrage collecte:', error.message);
    res.status(500).json({
      success: false,
      message: 'Erreur lors du démarrage de la collecte',
      error: error.message
    });
  }
});

// Endpoint pour arrêter la collecte automatique
router.post('/21/stop', async (req, res) => {
  try {
    collector.stopCollection();
    
    res.json({
      success: true,
      message: 'Collecte automatique arrêtée',
      status: collector.getStatus(),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('❌ Erreur arrêt collecte:', error.message);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de l\'arrêt de la collecte',
      error: error.message
    });
  }
});

// Endpoint pour obtenir le statut du collecteur
router.get('/21/status', async (req, res) => {
  try {
    res.json({
      success: true,
      status: collector.getStatus(),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('❌ Erreur statut collecteur:', error.message);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de la récupération du statut',
      error: error.message
    });
  }
});

// Endpoint pour récupérer les données récentes
router.get('/21/data', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 100;
    const data = await collector.getRecentData(limit);
    
    res.json({
      success: true,
      count: data.length,
      data: data,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('❌ Erreur récupération données:', error.message);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de la récupération des données',
      error: error.message
    });
  }
});

// Endpoint pour récupérer les statistiques
router.get('/21/stats', async (req, res) => {
  try {
    const stats = await collector.getStatistics();
    
    res.json({
      success: true,
      statistics: stats,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error('❌ Erreur récupération statistiques:', error.message);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de la récupération des statistiques',
      error: error.message
    });
  }
});

// Endpoint pour récupérer les données d'un événement spécifique
router.get('/21/event/:eventId', async (req, res) => {
  try {
    const eventId = req.params.eventId;
    const limit = parseInt(req.query.limit) || 50;
    const data = await collector.getDataByEventId(eventId, limit);
    
    res.json({
      success: true,
      eventId: eventId,
      count: data.length,
      data: data,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error(`❌ Erreur récupération données événement ${req.params.eventId}:`, error.message);
    res.status(500).json({
      success: false,
      message: 'Erreur lors de la récupération des données de l\'événement',
      error: error.message
    });
  }
});

// Export pour utilisation externe
module.exports = {
  router,
  collector,
  collectTwentyOne: () => collector.collectTwentyOne()
};
