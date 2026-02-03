const fs = require('fs').promises;
const path = require('path');
const logger = require('../config/logger');

class CsvStorageService {
  constructor() {
    this.dataDir = path.join(__dirname, '../../data');
    this.csvFile = path.join(this.dataDir, 'twentyone_rounds.csv');
    this.headers = [
      'id',
      'event_id',
      'collected_at',
      'option_type',
      'odd',
      'round_state',
      'raw_payload'
    ];
  }

  async ensureDataDirectory() {
    try {
      await fs.access(this.dataDir);
    } catch (error) {
      await fs.mkdir(this.dataDir, { recursive: true });
      logger.info(`📁 Répertoire de données créé: ${this.dataDir}`);
    }
  }

  async ensureCsvFile() {
    await this.ensureDataDirectory();
    
    try {
      await fs.access(this.csvFile);
    } catch (error) {
      // Le fichier n'existe pas, on le crée avec les en-têtes
      const headerRow = this.headers.join(',') + '\n';
      await fs.writeFile(this.csvFile, headerRow, 'utf8');
      logger.info(`📄 Fichier CSV créé: ${this.csvFile}`);
    }
  }

  escapeCsvField(field) {
    if (field === null || field === undefined) {
      return '';
    }
    
    const stringField = String(field);
    
    // Échapper les guillemets et entourer si contient virgule, guillemet ou saut de ligne
    if (stringField.includes(',') || stringField.includes('"') || stringField.includes('\n')) {
      return '"' + stringField.replace(/"/g, '""') + '"';
    }
    
    return stringField;
  }

  async saveRoundData(eventId, bettingOptions, roundState, rawPayload) {
    await this.ensureCsvFile();
    
    try {
      const timestamp = new Date().toISOString();
      const rows = [];
      
      // Vérifier si c'est une partie terminée
      const isGameFinished = this.isGameFinished(roundState, rawPayload);
      
      if (!isGameFinished) {
        logger.debug(`⏭️ Événement ${eventId} ignoré : partie non terminée`);
        return 0;
      }
      
      // Vérifier si cet événement est déjà sauvegardé
      const isDuplicate = await this.isEventAlreadySaved(eventId, timestamp);
      
      if (isDuplicate) {
        logger.debug(`⏭️ Événement ${eventId} ignoré : déjà sauvegardé`);
        return 0;
      }
      
      for (const option of bettingOptions) {
        const row = [
          Date.now() + Math.random(), // ID unique simple
          eventId,
          timestamp,
          option.optionType || '',
          option.odd || '',
          JSON.stringify(roundState),
          JSON.stringify(rawPayload)
        ];
        
        const csvRow = row.map(field => this.escapeCsvField(field)).join(',') + '\n';
        rows.push(csvRow);
      }
      
      // Écrire toutes les nouvelles lignes
      await fs.appendFile(this.csvFile, rows.join(''), 'utf8');
      
      logger.debug(`💾 ${bettingOptions.length} options sauvegardées en CSV pour l'événement ${eventId} (partie terminée)`);
      return rows.length;
    } catch (error) {
      logger.error(`❌ Erreur lors de la sauvegarde CSV pour l'événement ${eventId}:`, error.message);
      throw error;
    }
  }

  isGameFinished(roundState, rawPayload) {
    try {
      // Vérifier si la partie est terminée selon différents critères
      
      // 1. Vérifier l'état du round
      if (roundState && roundState.gamePhase === 'Result') {
        return true;
      }
      
      // 2. Vérifier les scores finaux (21 ou proche)
      if (roundState) {
        const playerScore = parseInt(roundState.playerScore) || 0;
        const bankerScore = parseInt(roundState.bankerScore) || 0;
        
        // Si un des joueurs a 21 ou plus, la partie est probablement terminée
        if (playerScore >= 21 || bankerScore >= 21) {
          return true;
        }
        
        // Si les deux scores sont valides et qu'il n'y a pas de temps restant
        if (playerScore > 0 && bankerScore > 0 && roundState.timeRemaining === 0) {
          return true;
        }
      }
      
      // 3. Vérifier dans le payload brut
      if (rawPayload && rawPayload.isMockData) {
        // Pour les données de test, considérer comme terminé si isLive est false
        return !roundState.isLive;
      }
      
      // 4. Vérifier si c'est une donnée de test avec phase "Result"
      if (rawPayload && rawPayload.event && rawPayload.event.roundState) {
        return rawPayload.event.roundState.gamePhase === 'Result';
      }
      
      return false;
    } catch (error) {
      logger.warn(`⚠️ Erreur lors de la vérification de fin de partie: ${error.message}`);
      // En cas d'erreur, sauvegarder pour ne pas perdre de données
      return true;
    }
  }

  async isEventAlreadySaved(eventId, timestamp) {
    try {
      const content = await fs.readFile(this.csvFile, 'utf8');
      const lines = content.trim().split('\n');
      
      // Ignorer l'en-tête
      const dataLines = lines.slice(1);
      
      // Chercher si cet eventId existe déjà
      for (const line of dataLines) {
        if (!line.trim()) continue;
        
        const fields = this.parseCsvLine(line);
        if (fields.length >= 2 && fields[1] === eventId.toString()) {
          // Vérifier si la sauvegarde est récente (moins de 30 secondes)
          const existingTimestamp = fields[2];
          if (existingTimestamp) {
            const existingTime = new Date(existingTimestamp);
            const currentTime = new Date(timestamp);
            const diffSeconds = (currentTime - existingTime) / 1000;
            
            if (diffSeconds < 30) {
              return true; // Doublon récent
            }
          }
        }
      }
      
      return false;
    } catch (error) {
      logger.warn(`⚠️ Erreur lors de la vérification de doublons: ${error.message}`);
      return false;
    }
  }

  async getRecentData(limit = 100) {
    try {
      await this.ensureCsvFile();
      
      // Vérifier si le fichier existe et n'est pas vide
      try {
        const stats = await fs.stat(this.csvFile);
        if (stats.size === 0) {
          logger.debug('📄 Fichier CSV vide, retour de données vides');
          return [];
        }
      } catch (statError) {
        logger.debug('📄 Fichier CSV inexistant, retour de données vides');
        return [];
      }
      
      const content = await fs.readFile(this.csvFile, 'utf8');
      
      // Vérifier si le contenu est vide ou seulement l'en-tête
      if (!content || content.trim() === '' || content.trim().split('\n').length <= 1) {
        logger.debug('📄 Fichier CSV sans données, retour de données vides');
        return [];
      }
      
      const lines = content.trim().split('\n');
      
      // Ignorer l'en-tête
      const dataLines = lines.slice(1);
      
      if (dataLines.length === 0) {
        logger.debug('📄 Aucune ligne de données dans le CSV');
        return [];
      }
      
      // Prendre les dernières lignes (inverse pour avoir les plus récentes)
      const recentLines = dataLines.slice(-limit).reverse();
      
      const results = [];
      
      for (const line of recentLines) {
        if (!line.trim()) continue;
        
        // Parser le CSV (gestion simple des guillemets)
        const fields = this.parseCsvLine(line);
        
        if (fields.length >= this.headers.length) {
          try {
            results.push({
              id: fields[0],
              event_id: fields[1],
              collected_at: fields[2],
              option_type: fields[3],
              odd: parseFloat(fields[4]) || null,
              round_state: fields[5] ? JSON.parse(fields[5]) : null,
              raw_payload: fields[6] ? JSON.parse(fields[6]) : null
            });
          } catch (parseError) {
            logger.warn(`⚠️ Erreur parsing ligne CSV: ${parseError.message}`);
            continue;
          }
        }
      }
      
      logger.debug(`📊 ${results.length} entrées récupérées du CSV`);
      return results;
    } catch (error) {
      logger.error('❌ Erreur lors de la lecture des données CSV récentes:', error.message);
      return [];
    }
  }

  parseCsvLine(line) {
    const fields = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      
      if (char === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i++; // Sauter le prochain guillemet
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === ',' && !inQuotes) {
        fields.push(current);
        current = '';
      } else {
        current += char;
      }
    }
    
    fields.push(current);
    return fields;
  }

  async getDataByEventId(eventId, limit = 50) {
    try {
      const allData = await this.getRecentData(10000); // Prendre plus de données pour filtrer
      return allData.filter(row => row.event_id === eventId).slice(0, limit);
    } catch (error) {
      logger.error(`❌ Erreur lors de la récupération des données pour l'événement ${eventId}:`, error.message);
      return [];
    }
  }

  async getStatistics() {
    try {
      await this.ensureCsvFile();
      
      const content = await fs.readFile(this.csvFile, 'utf8');
      const lines = content.trim().split('\n');
      
      const totalRows = Math.max(0, lines.length - 1); // -1 pour l'en-tête
      const recentData = await this.getRecentData(1000);
      
      // Compter les événements uniques
      const uniqueEvents = new Set(recentData.map(row => row.event_id)).size;
      
      // Compter les types d'options
      const optionTypes = {};
      recentData.forEach(row => {
        if (row.option_type) {
          optionTypes[row.option_type] = (optionTypes[row.option_type] || 0) + 1;
        }
      });
      
      return {
        totalRows,
        uniqueEvents,
        optionTypes,
        filePath: this.csvFile,
        lastUpdate: new Date().toISOString()
      };
    } catch (error) {
      logger.error('❌ Erreur lors du calcul des statistiques:', error.message);
      return {
        totalRows: 0,
        uniqueEvents: 0,
        optionTypes: {},
        filePath: this.csvFile,
        lastUpdate: new Date().toISOString(),
        error: error.message
      };
    }
  }

  async cleanupOldData(daysToKeep = 30) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - daysToKeep);
      
      const content = await fs.readFile(this.csvFile, 'utf8');
      const lines = content.split('\n');
      
      const header = lines[0];
      const dataLines = lines.slice(1);
      
      const filteredLines = dataLines.filter(line => {
        if (!line.trim()) return false;
        
        const fields = this.parseCsvLine(line);
        if (fields.length < 3) return false;
        
        const collectedAt = new Date(fields[2]);
        return collectedAt > cutoffDate;
      });
      
      const newContent = [header, ...filteredLines].join('\n');
      await fs.writeFile(this.csvFile, newContent, 'utf8');
      
      const removedCount = dataLines.length - filteredLines.length;
      logger.info(`🧹 Nettoyage terminé: ${removedCount} lignes supprimées (plus de ${daysToKeep} jours)`);
      
      return removedCount;
    } catch (error) {
      logger.error('❌ Erreur lors du nettoyage des anciennes données:', error.message);
      throw error;
    }
  }
}

module.exports = CsvStorageService;
