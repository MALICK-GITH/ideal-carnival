// Données de test pour simuler des événements TwentyOne quand l'API n'en a pas
const logger = require('../config/logger');

class MockDataService {
  constructor() {
    this.mockEventId = 999999;
    this.mockCounter = 0;
  }

  generateMockTwentyOneEvents() {
    this.mockCounter++;
    const events = [];
    
    // Générer 1-3 événements de test
    const eventCount = Math.floor(Math.random() * 3) + 1;
    
    for (let i = 0; i < eventCount; i++) {
      const eventId = this.mockEventId + (this.mockCounter * 10) + i;
      
      // Générer des scores finaux pour simuler des parties terminées
      const playerScore = Math.floor(Math.random() * 25); // 0-24
      const bankerScore = Math.floor(Math.random() * 25); // 0-24
      
      events.push({
        eventId: eventId,
        sportId: 146,
        eventName: `TwentyOne Game #${eventId}`,
        startTime: new Date().toISOString(),
        roundState: {
          isLive: false, // Partie terminée
          roundNumber: Math.floor(Math.random() * 20) + 1,
          playerScore: playerScore,
          bankerScore: bankerScore,
          timeRemaining: 0,
          gamePhase: 'Result' // Phase de résultat
        }
      });
    }
    
    logger.info(`🎭 ${events.length} événements TwentyOne simulés générés (parties terminées)`);
    return events;
  }

  generateMockBettingOptions(eventId) {
    const options = [];
    
    // Options typiques pour TwentyOne
    const optionTypes = [
      { type: 'Player Win', odd: (1.8 + Math.random() * 0.4).toFixed(2) },
      { type: 'Banker Win', odd: (1.8 + Math.random() * 0.4).toFixed(2) },
      { type: 'Tie', odd: (8.0 + Math.random() * 2.0).toFixed(2) },
      { type: 'Player Pair', odd: (11.0 + Math.random() * 3.0).toFixed(2) },
      { type: 'Banker Pair', odd: (11.0 + Math.random() * 3.0).toFixed(2) }
    ];
    
    optionTypes.forEach((opt, index) => {
      options.push({
        optionType: opt.type,
        group: 'Main',
        odd: parseFloat(opt.odd),
        optionName: opt.type,
        optionId: eventId * 100 + index
      });
    });
    
    return options;
  }

  generateMockRoundState() {
    const playerScore = Math.floor(Math.random() * 25); // 0-24
    const bankerScore = Math.floor(Math.random() * 25); // 0-24
    
    return {
      isLive: false, // Partie terminée
      roundNumber: Math.floor(Math.random() * 20) + 1,
      playerScore: playerScore,
      bankerScore: bankerScore,
      timeRemaining: 0,
      gamePhase: 'Result' // Phase de résultat
    };
  }
}

module.exports = MockDataService;
