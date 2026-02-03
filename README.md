# ORACXPRED MÉTAPHORE - TwentyOne Data Collector

Collecteur de données spécialisé pour le jeu TwentyOne (Jeu 21) destiné à la plateforme ORACXPRED MÉTAPHORE.

## 🎯 Objectif

Fournir un flux de données propre, horodaté et structuré pour entraîner et alimenter l'IA Snake 🐍 win.

## 📋 Fonctionnalités

- **Collecte automatique** des données du jeu TwentyOne via API 1xBet
- **Stockage CSV** simple et efficace (pas de base de données requise)
- **Polling configurable** (1-3 secondes recommandé)
- **Gestion des erreurs** et retry automatique
- **API REST** pour contrôle et monitoring
- **Logging structuré** avec Winston

## 🏗️ Architecture

```
src/
├── config/
│   └── logger.js       # Configuration Winston
├── services/
│   ├── oneBetApi.js    # Client API 1xBet
│   ├── dataCollector.js # Logique de collecte
│   └── csvStorage.js   # Gestion stockage CSV
├── routes/
│   └── collector.js    # Endpoints REST
└── index.js           # Point d'entrée

data/
└── twentyone_rounds.csv # Fichier de données généré
```

## 🚀 Installation

```bash
# Installation des dépendances
npm install

# Configuration de l'environnement
cp .env.example .env
# Éditer .env avec vos configurations

# Démarrage
npm start

# Développement
npm run dev
```

## ⚙️ Configuration

Variables d'environnement requises :

```env
# Collecteur
COLLECTOR_INTERVAL_MS=2000
COLLECTOR_RETRY_ATTEMPTS=3
COLLECTOR_RETRY_DELAY_MS=1000

# Stockage CSV
CSV_DATA_DIR=./data

# API 1xBet
API_BASE_URL=https://1xbet.com
API_LANGUAGE=fr
API_COUNTRY=96
API_GROUP=455

# Serveur
PORT=3000
AUTO_START_COLLECTOR=false
```

## 📊 Fichier CSV

Le fichier `data/twentyone_rounds.csv` contient :

```csv
id,event_id,collected_at,option_type,odd,round_state,raw_payload
1640995200000.1234,123456,2024-01-01T12:00:00.000Z,Player,1.95,"{""isLive"":true}","{""event"":{...}}"
```

Colonnes :
- **id** : Identifiant unique de l'entrée
- **event_id** : Identifiant de l'événement TwentyOne
- **collected_at** : Timestamp de collecte
- **option_type** : Type de pari (Player, Banker, Tie, etc.)
- **odd** : Cote associée
- **round_state** : État du round (JSON)
- **raw_payload** : Données brutes API (JSON)

## 🔌 API Endpoints

### Collecte
- `POST /api/collect/21` - Déclencher une collecte manuelle
- `POST /api/collect/21/start` - Démarrer la collecte automatique
- `POST /api/collect/21/stop` - Arrêter la collecte automatique

### Monitoring
- `GET /api/collect/21/status` - Statut du collecteur
- `GET /api/collect/21/data?limit=100` - Données récentes
- `GET /api/collect/21/stats` - Statistiques de collecte
- `GET /api/collect/21/event/:eventId` - Données d'un événement spécifique
- `GET /health` - Santé du service

## 🔄 Flux de collecte

1. **Découverte** : Appel `/LiveFeed/GetSportsShortZip`
2. **Filtrage** : `sportId == 146` (TwentyOne)
3. **Détails** : Appel `/LineFeed/GetGameZip` par eventId
4. **Extraction** : Options de pari, cotes, état du round
5. **Persistance** : Sauvegarde en CSV avec horodatage

## 📈 Utilisation

### Démarrage rapide
```bash
npm start
```

### Contrôle manuel
```bash
# Démarrer la collecte
curl -X POST http://localhost:3000/api/collect/21/start \
  -H "Content-Type: application/json" \
  -d '{"intervalMs": 2000}'

# Collecte unique
curl -X POST http://localhost:3000/api/collect/21

# Vérifier le statut
curl http://localhost:3000/api/collect/21/status

# Récupérer les données
curl http://localhost:3000/api/collect/21/data?limit=50

# Statistiques
curl http://localhost:3000/api/collect/21/stats
```

### Utilisation du fichier CSV
```javascript
const fs = require('fs');
const csv = require('csv-parser');

const results = [];
fs.createReadStream('./data/twentyone_rounds.csv')
  .pipe(csv())
  .on('data', (data) => results.push(data))
  .on('end', () => {
    console.log(`Lu ${results.length} entrées`);
  });
```

## 🐍 Pour l'IA Snake win

Les données collectées sont structurées pour l'analyse de patterns :

```javascript
// Format pour l'IA
const formattedData = {
  timestamp: "2024-01-01T12:00:00.000Z",
  eventId: 123456,
  options: {
    type: "Player",
    odd: 1.95
  },
  roundState: {
    isLive: true,
    currentScore: "Player: 5 - Banker: 3"
  },
  raw: { /* données brutes API */ }
};
```

## 🔧 Développement

```bash
# Tests
npm test

# Logs
tail -f logs/combined.log
tail -f logs/error.log

# Voir le fichier CSV
cat data/twentyone_rounds.csv
```

## 📝 Notes importantes

- **Pas de base de données** : Stockage simple en fichiers CSV
- **Idempotence** : Gestion des doublons via timestamps
- **Résilience** : Retry automatique en cas d'erreur API
- **Performance** : Lecture/écriture CSV optimisée
- **Extensibilité** : Architecture modulaire pour l'ajout de nouveaux sports

## 🧹 Gestion des données

### Nettoyage automatique
```javascript
// Supprimer les données de plus de 30 jours
const CsvStorageService = require('./src/services/csvStorage');
const csvStorage = new CsvStorageService();
await csvStorage.cleanupOldData(30);
```

### Backup des données
```bash
# Sauvegarder le fichier CSV
cp data/twentyone_rounds.csv backup/twentyone_rounds_$(date +%Y%m%d).csv
```

## 🚨 Avantages du CSV

- **Installation simple** : Pas de serveur de base de données
- **Portabilité** : Fichiers faciles à déplacer et analyser
- **Compatibilité** : Ouvert avec Excel, Python, R, etc.
- **Performance** : Rapide pour les volumes de données modérés
- **Debugging** : Facile à inspecter manuellement

## 🔍 Analyse des données

### Avec Python
```python
import pandas as pd

df = pd.read_csv('data/twentyone_rounds.csv')
print(df.head())
print(f"Total entrées: {len(df)}")
print(f"Événements uniques: {df['event_id'].nunique()}")
```

### Avec Excel/Google Sheets
1. Ouvrir `data/twentyone_rounds.csv`
2. Utiliser les filtres pour analyser les patterns
3. Créer des graphiques pour visualiser les cotes

---

**ORACXPRED MÉTAPHORE** - Powered by Snake 🐍 win AI

*Version CSV - Simple, efficace, prêt pour l'IA*
