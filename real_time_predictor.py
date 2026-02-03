import pandas as pd
import numpy as np
import json
import time
from datetime import datetime
import threading
import logging
from baccarat_api_client import BaccaratAPIClient
import joblib

class RealTimeBaccaratPredictor:
    def __init__(self, csv_path='data/twentyone_rounds.csv', model_path='models/baccarat_model.pkl'):
        self.csv_path = csv_path
        self.model_path = model_path
        self.api_client = BaccaratAPIClient()
        
        # Charger les données historiques et le modèle
        self.historical_data = None
        self.model = None
        self.scaler = None
        self.feature_columns = []
        
        # Variables pour le streaming
        self.current_events = {}
        self.predictions = {}
        self.is_running = False
        
        # Configuration logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.load_historical_data()
        self.load_trained_model()
    
    def load_historical_data(self):
        """Charge les données historiques du CSV"""
        try:
            self.historical_data = pd.read_csv(self.csv_path, header=None, 
                                            names=['id', 'event_id', 'collected_at', 'option_type', 'odd', 'round_state', 'raw_payload'])
            self.logger.info(f"Chargé {len(self.historical_data)} enregistrements historiques")
        except Exception as e:
            self.logger.error(f"Erreur chargement données historiques: {e}")
            self.historical_data = pd.DataFrame()
    
    def load_trained_model(self):
        """Charge le modèle IA entraîné"""
        try:
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            self.logger.info("Modèle IA chargé avec succès")
        except Exception as e:
            self.logger.error(f"Erreur chargement modèle: {e}")
    
    def extract_features_from_api_event(self, event):
        """Extrait les features depuis un événement de l'API pour la prédiction"""
        try:
            features = {
                'player_score': event.get('playerScore', 0),
                'banker_score': event.get('bankerScore', 0),
                'round_number': event.get('roundNumber', 0),
                'is_live': 1 if event.get('isLive', False) else 0,
            }
            
            # Features temporelles
            try:
                start_time = event.get('startTime', datetime.now().isoformat())
                if isinstance(start_time, (int, float)):
                    timestamp = datetime.fromtimestamp(start_time)
                elif start_time:
                    timestamp = datetime.fromisoformat(str(start_time)[:19])
                else:
                    timestamp = datetime.now()
            except (ValueError, TypeError, OSError):
                timestamp = datetime.now()
            features.update({
                'hour': timestamp.hour,
                'day_of_week': timestamp.weekday(),
                'minute': timestamp.minute
            })
            
            # Extraire les cotes depuis bettingOptions
            betting_options = event.get('bettingOptions', [])
            if isinstance(betting_options, list):
                odds_map = {}
                for option in betting_options:
                    if isinstance(option, dict):
                        odds_map[option.get('optionType', '')] = option.get('odd', 1.0)
                
                features.update({
                    'player_win_odd': odds_map.get('Player Win', 1.0),
                    'banker_win_odd': odds_map.get('Banker Win', 1.0),
                    'tie_odd': odds_map.get('Tie', 1.0)
                })
            else:
                features.update({
                    'player_win_odd': 1.0,
                    'banker_win_odd': 1.0,
                    'tie_odd': 1.0
                })
            
            # Calculer la cote actuelle basée sur le type de pari
            current_odd = 1.0
            if betting_options:
                # Prendre la cote la plus basse comme référence
                current_odd = min([opt.get('odd', 1.0) for opt in betting_options])
            features['odd_value'] = current_odd
            
            # Features séquentielles basées sur les données historiques
            if not self.historical_data.empty:
                recent_data = self.historical_data.tail(50)
                features.update({
                    'Player_Win_ma_5': (recent_data['option_type'] == 'Player Win').tail(5).mean(),
                    'Banker_Win_ma_5': (recent_data['option_type'] == 'Banker Win').tail(5).mean(),
                    'Tie_ma_5': (recent_data['option_type'] == 'Tie').tail(5).mean(),
                    'consecutive_Player_Win': self.get_consecutive_count(recent_data, 'Player Win'),
                    'consecutive_Banker_Win': self.get_consecutive_count(recent_data, 'Banker Win'),
                    'consecutive_Tie': self.get_consecutive_count(recent_data, 'Tie')
                })
            else:
                # Valeurs par défaut si pas de données historiques
                features.update({
                    'Player_Win_ma_5': 0.33,
                    'Banker_Win_ma_5': 0.33,
                    'Tie_ma_5': 0.34,
                    'consecutive_Player_Win': 0,
                    'consecutive_Banker_Win': 0,
                    'consecutive_Tie': 0
                })
            
            return features
            
        except Exception as e:
            self.logger.error(f"Erreur extraction features: {e}")
            return {col: 0 for col in self.feature_columns}
    
    def get_consecutive_count(self, data, result_type):
        """Compte les occurrences consécutives d'un type de résultat"""
        count = 0
        for _, row in data.iterrows():
            if row['option_type'] == result_type:
                count += 1
            else:
                count = 0
        return count
    
    def predict_event(self, event):
        """Fait une prédiction pour un événement spécifique"""
        if self.model is None:
            return {'error': 'Modèle non disponible'}
        
        try:
            # Extraire les features
            features = self.extract_features_from_api_event(event)
            
            # Préparer le vecteur de features dans le bon ordre
            feature_vector = []
            for col in self.feature_columns:
                feature_vector.append(features.get(col, 0))
            
            # Normalisation et prédiction
            feature_vector_scaled = self.scaler.transform([feature_vector])
            prediction = self.model.predict(feature_vector_scaled)[0]
            probabilities = self.model.predict_proba(feature_vector_scaled)[0]
            
            result_map = {0: 'Player Win', 1: 'Banker Win', 2: 'Tie', 3: 'Player Pair', 4: 'Banker Pair'}
            
            result = {
                'eventId': event.get('eventId'),
                'eventName': event.get('eventName'),
                'prediction': result_map[prediction],
                'probabilities': {
                    result_map[i]: prob for i, prob in enumerate(probabilities)
                },
                'confidence': max(probabilities) * 100,
                'gamePhase': event.get('gamePhase'),
                'currentScores': {
                    'player': event.get('playerScore', 0),
                    'banker': event.get('bankerScore', 0)
                },
                'timestamp': datetime.now().isoformat(),
                'features_used': self.feature_columns
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur prédiction event {event.get('eventId')}: {e}")
            return {'error': f'Erreur prédiction: {str(e)}'}
    
    def process_api_event(self, event):
        """Traite un événement reçu de l'API"""
        event_id = event.get('eventId')
        
        # Stocker l'événement courant
        self.current_events[event_id] = event
        
        # Générer une prédiction
        prediction = self.predict_event(event)
        self.predictions[event_id] = prediction
        
        # Logger
        self.logger.info(f"Event {event_id}: {prediction.get('prediction', 'N/A')} (confiance: {prediction.get('confidence', 0):.1f}%)")
        
        return prediction
    
    def start_real_time_prediction(self, interval=3):
        """Démarre la prédiction en temps réel"""
        self.is_running = True
        self.logger.info(f"Démarrage prédiction temps réel (interval: {interval}s)")
        
        def api_callback(event):
            if self.is_running:
                self.process_api_event(event)
        
        # Démarrer le monitoring API dans un thread séparé
        api_thread = threading.Thread(target=self.api_client.start_real_time_monitoring, 
                                    args=(api_callback, interval))
        api_thread.daemon = True
        api_thread.start()
        
        return api_thread
    
    def stop_real_time_prediction(self):
        """Arrête la prédiction en temps réel"""
        self.is_running = False
        self.logger.info("Arrêt prédiction temps réel")
    
    def get_current_predictions(self):
        """Retourne toutes les prédictions actuelles"""
        return self.predictions
    
    def get_current_events(self):
        """Retourne tous les événements actuels"""
        return self.current_events
    
    def get_prediction_for_event(self, event_id):
        """Retourne la prédiction pour un événement spécifique"""
        return self.predictions.get(event_id)

# Point d'entrée pour le test
if __name__ == "__main__":
    predictor = RealTimeBaccaratPredictor()
    
    print("Test du prédicteur temps réel...")
    
    # Test avec un événement fictif
    test_event = {
        'eventId': 12345,
        'eventName': 'Test Baccarat Game',
        'startTime': datetime.now().isoformat(),
        'isLive': True,
        'roundNumber': 5,
        'playerScore': 16,
        'bankerScore': 12,
        'gamePhase': 'Betting',
        'bettingOptions': [
            {'optionType': 'Player Win', 'odd': 1.95},
            {'optionType': 'Banker Win', 'odd': 1.85},
            {'optionType': 'Tie', 'odd': 8.5}
        ]
    }
    
    prediction = predictor.predict_event(test_event)
    print(f"Prédiction test: {json.dumps(prediction, indent=2)}")
    
    # Démarrer le monitoring temps réel
    print("\nDémarrage monitoring temps réel (Ctrl+C pour arrêter)...")
    try:
        predictor.start_real_time_prediction(interval=5)
        
        # Garder le programme en cours d'exécution
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        predictor.stop_real_time_prediction()
        print("Arrêt du programme")
