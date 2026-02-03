const OneBetApiService = require('./oneBetApi');
const CsvStorageService = require('./csvStorage');
const MockDataService = require('./mockData');
const logger = require('../config/logger');

class DataCollectorService {
  constructor() {
    this.apiService = new OneBetApiService();
    this.csvStorage = new CsvStorageService();
    this.mockService = new MockDataService();
    this.isRunning = false;
    this.intervalId = null;
    this.useMockData = process.env.USE_MOCK_DATA === 'true';
  }

  async saveRoundData(eventId, bettingOptions, roundState, rawPayload) {
    try {
      const savedCount = await this.csvStorage.saveRoundData(
        eventId,
        bettingOptions,
        roundState,
        rawPayload
      );
      
      logger.debug(`💾 ${savedCount} options sauvegardées en CSV pour l'événement ${eventId}`);
      return savedCount;
    } catch (error) {
      logger.error(`❌ Erreur lors de la sauvegarde CSV pour l'événement ${eventId}:`, error.message);
      throw error;
    }
  }

  async collectTwentyOne() {
    try {
      logger.info('🚀 Démarrage de la collecte TwentyOne...');
      
      let twentyOneEvents = [];
      
      if (this.useMockData) {
        logger.info('🎭 Utilisation des données de test (mock data)');
        twentyOneEvents = this.mockService.generateMockTwentyOneEvents();
      } else {
        // Étape 1: Découverte des rounds
        const sportsData = await this.apiService.retryOperation(() => 
          this.apiService.getSportsShort()
        );
        
        twentyOneEvents = this.apiService.filterTwentyOneEvents(sportsData);
        
        // Si aucun événement trouvé, utiliser les données de test
        if (twentyOneEvents.length === 0) {
          logger.warn('⚠️ Aucun événement TwentyOne trouvé, utilisation des données de test');
          twentyOneEvents = this.mockService.generateMockTwentyOneEvents();
        }
      }
      
      if (twentyOneEvents.length === 0) {
        logger.info('ℹ️ Aucun événement TwentyOne trouvé');
        return { collected: 0, events: [] };
      }

      const collectedEvents = [];
      
      // Étape 2: Détails et cotes pour chaque événement
      for (const event of twentyOneEvents) {
        try {
          let bettingOptions = [];
          let gameDetails = null;
          
          if (this.useMockData) {
            bettingOptions = this.mockService.generateMockBettingOptions(event.eventId);
            gameDetails = { mock: true, event };
          } else {
            gameDetails = await this.apiService.retryOperation(() => 
              this.apiService.getGameDetails(event.eventId)
            );
            bettingOptions = this.apiService.extractBettingOptions(gameDetails);
            
            // Si aucune option trouvée, utiliser les données de test
            if (bettingOptions.length === 0) {
              logger.warn(`⚠️ Aucune option trouvée pour l'événement ${event.eventId}, utilisation des données de test`);
              bettingOptions = this.mockService.generateMockBettingOptions(event.eventId);
            }
          }
          
          if (bettingOptions.length > 0) {
            // Étape 3: Persistance
            const roundState = this.useMockData ? 
              this.mockService.generateMockRoundState() : 
              event.roundState;
            
            await this.saveRoundData(
              event.eventId,
              bettingOptions,
              roundState,
              {
                event,
                gameDetails,
                bettingOptions,
                collectedAt: new Date().toISOString(),
                isMockData: this.useMockData || !gameDetails || gameDetails.mock
              }
            );
            
            collectedEvents.push({
              eventId: event.eventId,
              eventName: event.eventName,
              optionsCount: bettingOptions.length,
              roundState: roundState,
              isMockData: this.useMockData || !gameDetails || gameDetails.mock
            });
            
            logger.info(`✅ Événement ${event.eventId} collecté: ${bettingOptions.length} options ${this.useMockData ? '(mock)' : ''}`);
          }
        } catch (error) {
          logger.error(`❌ Erreur lors du traitement de l'événement ${event.eventId}:`, error.message);
          continue;
        }
      }
      
      logger.info(`📊 Collecte terminée: ${collectedEvents.length} événements traités`);
      return { collected: collectedEvents.length, events: collectedEvents };
      
    } catch (error) {
      logger.error('❌ Erreur critique lors de la collecte TwentyOne:', error.message);
      throw error;
    }
  }

  startCollection(intervalMs = 2000) {
    if (this.isRunning) {
      logger.warn('⚠️ Le collecteur est déjà en cours d\'exécution');
      return;
    }

    this.isRunning = true;
    logger.info(`🔄 Démarrage de la collecte automatique (intervalle: ${intervalMs}ms)`);
    
    // Première exécution immédiate
    this.collectTwentyOne().catch(error => {
      logger.error('❌ Erreur lors de la première collecte:', error.message);
    });
    
    // Configuration de l'intervalle
    this.intervalId = setInterval(async () => {
      try {
        await this.collectTwentyOne();
      } catch (error) {
        logger.error('❌ Erreur lors de la collecte programmée:', error.message);
      }
    }, intervalMs);
  }

  stopCollection() {
    if (!this.isRunning) {
      logger.warn('⚠️ Le collecteur n\'est pas en cours d\'exécution');
      return;
    }

    this.isRunning = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    
    logger.info('🛑 Collecte automatique arrêtée');
  }

  getStatus() {
    return {
      isRunning: this.isRunning,
      intervalId: this.intervalId ? 'active' : 'inactive'
    };
  }

  async getRecentData(limit = 100) {
    try {
      const data = await this.csvStorage.getRecentData(limit);
      return data;
    } catch (error) {
      logger.error('❌ Erreur lors de la récupération des données récentes:', error.message);
      throw error;
    }
  }

  async getStatistics() {
    try {
      return await this.csvStorage.getStatistics();
    } catch (error) {
      logger.error('❌ Erreur lors de la récupération des statistiques:', error.message);
      throw error;
    }
  }

  async getDataByEventId(eventId, limit = 50) {
    try {
      return await this.csvStorage.getDataByEventId(eventId, limit);
    } catch (error) {
      logger.error(`❌ Erreur lors de la récupération des données pour l'événement ${eventId}:`, error.message);
      throw error;
    }
  }
}

module.exports = DataCollectorService;
