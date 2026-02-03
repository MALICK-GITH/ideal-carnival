/**
 * Exemple d'utilisation du collecteur TwentyOne
 * ORACXPRED MÉTAPHORE
 */

const { collector } = require('../src/routes/collector');

async function demonstrateUsage() {
  console.log('🚀 Démonstration du collecteur TwentyOne\n');

  try {
    // 1. Collecte manuelle unique
    console.log('📊 Collecte manuelle...');
    const result = await collector.collectTwentyOne();
    console.log(`✅ Collecte terminée: ${result.collected} événements traités\n`);

    // 2. Démarrage de la collecte automatique
    console.log('🔄 Démarrage de la collecte automatique (2 secondes)...');
    collector.startCollection(2000);

    // Laisser tourner 10 secondes
    await new Promise(resolve => setTimeout(resolve, 10000));

    // 3. Arrêt de la collecte
    console.log('\n🛑 Arrêt de la collecte automatique...');
    collector.stopCollection();

    // 4. Récupération des données récentes
    console.log('📈 Récupération des 10 dernières entrées...');
    const recentData = await collector.getRecentData(10);
    
    console.log(`\n📋 Dernières entrées (${recentData.length}):`);
    recentData.forEach((entry, index) => {
      console.log(`${index + 1}. Event ${entry.event_id} | ${entry.option_type} | Cote: ${entry.odd} | ${entry.collected_at}`);
    });

    // 5. Statut final
    console.log('\n📊 Statut final:', collector.getStatus());

  } catch (error) {
    console.error('❌ Erreur lors de la démonstration:', error.message);
  }
}

// Fonction pour l'IA Snake 🐍 win
async function getDataForAI(limit = 100) {
  try {
    const data = await collector.getRecentData(limit);
    
    // Formatage pour l'IA
    const formattedData = data.map(entry => ({
      timestamp: entry.collected_at,
      eventId: entry.event_id,
      options: {
        type: entry.option_type,
        odd: parseFloat(entry.odd)
      },
      roundState: entry.round_state,
      raw: entry.raw_payload
    }));

    return formattedData;
  } catch (error) {
    console.error('❌ Erreur récupération données IA:', error.message);
    return [];
  }
}

// Export pour utilisation dans d'autres modules
module.exports = {
  demonstrateUsage,
  getDataForAI
};

// Exécuter la démonstration si appelé directement
if (require.main === module) {
  demonstrateUsage();
}
