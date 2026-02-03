# 🎰 Baccarat Predictor IA - Site Flask de Prédictions

## 📋 Description

Transformation du collecteur de données TwentyOne en site web Flask de prédictions Baccarat avec intelligence artificielle. Le système analyse les données historiques pour fournir des prédictions intelligentes des résultats de Baccarat.

## 🏗️ Architecture

### Structure Python/Flask
- **app.py** - Application web principale avec API REST
- **train_model.py** - Script d'entraînement du modèle IA
- **templates/index.html** - Interface web moderne
- **models/** - Modèles IA entraînés
- **data/** - Fichiers CSV de données historiques

### Technologies Utilisées
- **Backend**: Python 3.14, Flask 2.3.3
- **Machine Learning**: scikit-learn, pandas, numpy
- **Frontend**: HTML5, TailwindCSS, JavaScript, Plotly.js
- **IA**: RandomForest Classifier avec features séquentielles

## 🚀 Installation

### Prérequis
```bash
Python 3.14+
pip install -r requirements.txt
```

### Installation des dépendances
```bash
pip install Flask==2.3.3 pandas==2.0.3 numpy==1.24.3 scikit-learn==1.3.0 tensorflow==2.13.0 matplotlib==3.7.2 seaborn==0.12.2 plotly==5.15.0 requests==2.31.0 python-dotenv==1.0.0 gunicorn==21.2.0
```

## 🤖 Entraînement du Modèle IA

### 1. Entraîner le modèle avec les données historiques
```bash
python train_model.py
```

**Résultats d'entraînement:**
- Accuracy: 86.3%
- Features utilisées: 17 (scores, cotes, temporelles, séquentielles)
- Top features: odd_value (28.8%), consecutive_Player_Win (20.3%), consecutive_Tie (19.8%)

### 2. Modèle sauvegardé dans
```
models/baccarat_model.pkl
```

## 🌐 Lancement de l'Application

### Développement
```bash
python app.py
```

### Production
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

L'application sera disponible sur `http://localhost:5000`

## 📊 Fonctionnalités

### API Endpoints

#### Statistiques des données
```
GET /api/stats
```
Retourne les statistiques des données historiques:
- Total des rounds
- Distribution des résultats
- Scores moyens
- Distribution horaire

#### Prédiction IA
```
GET /api/predict?event_id=<optional>
```
Génère une prédiction avec le modèle entraîné:
- Résultat prédit
- Probabilités détaillées
- Niveau de confiance
- Basé sur le modèle IA

#### Historique récent
```
GET /api/history?limit=<optional>
```
Retourne les N derniers résultats

#### Events disponibles
```
GET /api/events
```
Liste des events Baccarat disponibles

### Interface Web

#### 🎯 Tableau de Bord Principal
- Statistiques en temps réel
- Cartes de métriques (total rounds, win rates)
- Visualisations interactives

#### 🔮 Prédiction Intelligente
- Prédiction principale avec niveau de confiance
- Probabilités détaillées pour chaque résultat
- Sélection d'events spécifiques
- Graphique des probabilités

#### 📈 Analyses et Visualisations
- Distribution horaire des résultats
- Graphique circulaire des résultats
- Historique récent avec badges colorés
- Auto-rafraîchissement toutes les 30 secondes

## 🧠 Modèle de Prédiction

### Features Utilisées
1. **Scores du jeu**: player_score, banker_score
2. **Informations de round**: round_number, is_live
3. **Cotes de paris**: odd_value, player_win_odd, banker_win_odd, tie_odd
4. **Features temporelles**: hour, day_of_week, minute
5. **Features séquentielles**:
   - Moyennes mobiles sur 5 rounds
   - Compteurs de résultats consécutifs

### Performance du Modèle
- **Accuracy globale**: 86.3%
- **Précision Player/Banker Win**: 100%
- **Précision Tie**: 100%
- **Précision Pairs**: 79% (Player), 61% (Banker)

## 📁 Structure des Données

### Format CSV (twentyone_rounds.csv)
```
id, event_id, collected_at, option_type, odd, round_state, raw_payload
```

### Types de résultats prédits
- Player Win
- Banker Win  
- Tie
- Player Pair
- Banker Pair

## 🔧 Configuration

### Variables d'environnement
```bash
# .env file (optionnel)
FLASK_ENV=development
FLASK_DEBUG=True
CSV_PATH=data/twentyone_rounds.csv
MODEL_PATH=models/baccarat_model.pkl
```

## 📱 Utilisation

### 1. Visualiser les statistiques
Accédez à la page d'accueil pour voir les statistiques en temps réel des données historiques.

### 2. Générer une prédiction
Cliquez sur "Générer Prédiction" pour obtenir une prédiction basée sur le modèle IA entraîné.

### 3. Analyser les probabilités
Consultez le graphique des probabilités et la liste détaillée pour chaque type de résultat.

### 4. Suivre l'historique
Visualisez les résultats récents avec les badges colorés pour identifier rapidement les tendances.

## 🔄 Mise à jour du Modèle

Pour ré-entraîner le modèle avec de nouvelles données:
```bash
# Ajouter de nouvelles données au CSV
# Ré-entraîner le modèle
python train_model.py

# Redémarrer l'application pour charger le nouveau modèle
python app.py
```

## 🚨 Notes importantes

- Le modèle nécessite au moins 50 enregistrements pour fonctionner correctement
- Les prédictions sont basées sur des tendances historiques et ne garantissent pas les résultats futurs
- L'application se met à jour automatiquement toutes les 30 secondes
- Le modèle est sauvegardé pour éviter de ré-entraîner à chaque redémarrage

## 📞 Support

Pour toute question ou problème:
1. Vérifiez que le fichier CSV existe et contient des données
2. Assurez-vous que le modèle a été entraîné (`python train_model.py`)
3. Consultez les logs de l'application pour les erreurs détaillées

---

**🎰 Baccarat Predictor IA - Transformez vos données en prédictions intelligentes!**
