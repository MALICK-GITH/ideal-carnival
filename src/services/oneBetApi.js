const axios = require('axios');
const logger = require('../config/logger');

class OneBetApiService {
  constructor() {
    this.baseUrl = process.env.API_BASE_URL || 'https://1xbet.com';
    this.language = process.env.API_LANGUAGE || 'fr';
    this.country = process.env.API_COUNTRY || '96';
    this.group = process.env.API_GROUP || '455';
    this.sportId = 146; // TwentyOne game ID
  }

  async getSportsShort() {
    try {
      const url = `${this.baseUrl}/service-api/LiveFeed/GetSportsShortZip`;
      const params = {
        lng: this.language,
        gr: this.group,
        withCountries: true,
        country: this.country,
        virtualSports: true,
        groupChamps: true
      };

      logger.info('🔍 Récupération des sports depuis LiveFeed...');
      const response = await axios.get(url, { 
        params,
        timeout: 10000,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          'Accept': 'application/json, text/plain, */*',
          'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        }
      });

      return response.data;
    } catch (error) {
      logger.error('❌ Erreur lors de la récupération des sports:', error.message);
      throw error;
    }
  }

  filterTwentyOneEvents(data) {
    const events = [];
    
    try {
      // La structure de l'API 1xBet est correcte
      if (data && data.Value && Array.isArray(data.Value)) {
        for (const sport of data.Value) {
          // Chercher le sport avec I === 146 (TwentyOne)
          if (sport.I === 146) {
            logger.info(`🎮 Sport TwentyOne trouvé: ${sport.N || 'Jeu 21'} (${sport.C} événements)`);
            
            if (sport.E && Array.isArray(sport.E)) {
              for (const event of sport.E) {
                events.push({
                  eventId: event.I,
                  sportId: sport.I,
                  eventName: event.N || 'TwentyOne Game',
                  startTime: event.S,
                  roundState: {
                    isLive: event.LI || false,
                    currentScore: event.SC,
                    timeInSeconds: event.TI
                  }
                });
              }
            } else {
              logger.info(`ℹ️ Le sport TwentyOne (ID: 146) est disponible mais n'a pas d'événements actifs`);
            }
          }
        }
      }

      logger.info(`🎯 ${events.length} événements TwentyOne trouvés`);
      return events;
    } catch (error) {
      logger.error('❌ Erreur lors du filtrage des événements TwentyOne:', error.message);
      return [];
    }
  }

  async getGameDetails(eventId) {
    try {
      const url = `${this.baseUrl}/service-api/LineFeed/GetGameZip`;
      const params = {
        id: eventId,
        lng: this.language
      };

      logger.debug(`📊 Récupération détails pour l'événement ${eventId}`);
      const response = await axios.get(url, { 
        params,
        timeout: 8000,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          'Accept': 'application/json, text/plain, */*',
          'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        }
      });

      return response.data;
    } catch (error) {
      logger.error(`❌ Erreur lors de la récupération des détails de l'événement ${eventId}:`, error.message);
      throw error;
    }
  }

  extractBettingOptions(gameData) {
    const options = [];
    
    try {
      // La structure correcte pour l'API 1xBet
      if (gameData && gameData.Value && gameData.Value.E) {
        const events = gameData.Value.E;
        
        if (Array.isArray(events)) {
          for (const event of events) {
            if (event && Array.isArray(event.E)) {
              for (const option of event.E) {
                options.push({
                  optionType: option.T || option.type || 'Unknown',
                  group: option.G || option.group || '',
                  odd: option.C || option.odd || 0,
                  optionName: option.N || option.name || '',
                  optionId: option.I || option.id
                });
              }
            }
          }
        }
      }

      return options;
    } catch (error) {
      logger.error('❌ Erreur lors de l\'extraction des options de pari:', error.message);
      return [];
    }
  }

  async retryOperation(operation, maxAttempts = 3, delay = 1000) {
    let lastError;
    
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        logger.warn(`⚠️ Tentative ${attempt}/${maxAttempts} échouée: ${error.message}`);
        
        if (attempt < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, delay * attempt));
        }
      }
    }
    
    throw lastError;
  }
}

module.exports = OneBetApiService;
