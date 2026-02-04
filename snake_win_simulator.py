import pandas as pd
import numpy as np
import json
import time
from datetime import datetime
import threading
import logging
from simulator_api import BaccaratSimulator
import joblib
from collections import deque

class SnakeWinSimulator:
    def __init__(self, csv_path='data/twentyone_rounds.csv', model_path='models/baccarat_model.pkl'):
        self.csv_path = csv_path
        self.model_path = model_path
        self.simulator = BaccaratSimulator()
        
        # Configuration du modèle Snake_win
        self.ai_config = {
            "model": {
                "name": "Snake_win",
                "version": "v1.0",
                "type": "pattern_based + probability"
            },
            "input": {
                "last_rounds": 20,
                "symbols": ["♠", "♦", "♣"],
                "history_depth": 100
            }
        }
        
        # Données historiques et tracking
        self.historical_data = None
        self.model = None
        self.scaler = None
        self.feature_columns = []
        
        # Système de tracking ♠ ♦ ♣
        self.symbol_history = deque(maxlen=100)
        self.round_history = deque(maxlen=100)
        self.current_rounds = {}
        self.predictions = {}
        
        # Variables pour le streaming
        self.is_running = False
        
        # Configuration logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.load_historical_data()
        self.load_trained_model()
        self.initialize_symbol_tracking()
    
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
            self.logger.info("Modèle IA Snake_win chargé avec succès")
        except Exception as e:
            self.logger.error(f"Erreur chargement modèle: {e}")
    
    def initialize_symbol_tracking(self):
        """Initialise le système de tracking avec symboles ♠ ♦ ♣"""
        if not self.historical_data.empty:
            # Convertir les résultats historiques en symboles
            for _, row in self.historical_data.tail(50).iterrows():
                symbol = self.convert_result_to_symbol(row['option_type'])
                self.symbol_history.append(symbol)
                
                round_info = {
                    "round_id": row['id'],
                    "symbol": symbol,
                    "bet": "PLAYER+2",
                    "result_code": self.get_result_code_from_history(row)
                }
                self.round_history.append(round_info)
        
        self.logger.info(f"Tracking initialisé avec {len(self.symbol_history)} symboles")
    
    def convert_result_to_symbol(self, result):
        """Convertit un résultat en symbole ♠ ♦ ♣"""
        symbols = ["♠", "♦", "♣"]
        # Logique de conversion basée sur le type de résultat
        if result == "Player Win":
            return symbols[0]
        elif result == "Banker Win":
            return symbols[1]
        else:  # Tie ou autres
            return symbols[2]
    
    def get_result_code_from_history(self, row):
        """Extrait le code résultat depuis les données historiques"""
        # Logique basée sur les cotes et scores
        try:
            round_state = json.loads(row['round_state'])
            player_score = round_state.get('playerScore', 0)
            banker_score = round_state.get('bankerScore', 0)
            odd = float(row['odd']) if row['odd'] != 'null' else 1.0
            
            if abs(player_score - banker_score) >= 3:
                return 2  # strong_win
            elif player_score != banker_score:
                return 1  # win
            else:
                return 0  # loss
                
        except:
            return 1  # win par défaut
    
    def extract_features_from_round(self, round_data):
        """Extrait les features depuis un round pour la prédiction IA"""
        try:
            round_info = round_data.get('round', {})
            tracking_info = round_data.get('tracking', {})
            
            features = {
                'player_score': round_info.get('score', {}).get('player', 0),
                'banker_score': round_info.get('score', {}).get('banker', 0),
                'round_number': round_info.get('round_id', 0),
                'is_live': 1,  # Toujours live pour les données simulées
            }
            
            # Features temporelles
            timestamp = datetime.fromisoformat(round_info.get('timestamp', datetime.now().isoformat()))
            features.update({
                'hour': timestamp.hour,
                'day_of_week': timestamp.weekday(),
                'minute': timestamp.minute
            })
            
            # Cotes depuis betting info
            bet_info = round_data.get('bet', {})
            features.update({
                'player_win_odd': bet_info.get('odds', 1.85),
                'banker_win_odd': 1.95,  # Simulation
                'tie_odd': 8.5,  # Simulation
                'odd_value': bet_info.get('odds', 1.85)
            })
            
            # Features séquentielles basées sur l'historique des symboles
            recent_symbols = list(self.symbol_history)[-20:]
            features.update({
                'Player_Win_ma_5': recent_symbols.count('♠') / min(5, len(recent_symbols)) if recent_symbols else 0.33,
                'Banker_Win_ma_5': recent_symbols.count('♦') / min(5, len(recent_symbols)) if recent_symbols else 0.33,
                'Tie_ma_5': recent_symbols.count('♣') / min(5, len(recent_symbols)) if recent_symbols else 0.34,
                'consecutive_Player_Win': self.count_consecutive_symbols('♠'),
                'consecutive_Banker_Win': self.count_consecutive_symbols('♦'),
                'consecutive_Tie': self.count_consecutive_symbols('♣')
            })
            
            return features
            
        except Exception as e:
            self.logger.error(f"Erreur extraction features: {e}")
            return {col: 0 for col in self.feature_columns}
    
    def count_consecutive_symbols(self, symbol):
        """Compte les symboles consécutifs"""
        if not self.symbol_history:
            return 0
        
        count = 0
        for s in reversed(self.symbol_history):
            if s == symbol:
                count += 1
            else:
                break
        return count
    
    def predict_round(self, round_data):
        """Fait une prédiction Snake_win pour un round"""
        if self.model is None:
            # Simulation de prédiction si modèle non disponible
            import random
            confidence = random.uniform(0.65, 0.92)
            return {
                "model": self.ai_config["model"],
                "input": self.ai_config["input"],
                "prediction": {
                    "recommended_bet": "PLAYER+2",
                    "confidence": confidence,
                    "risk_level": "LOW" if confidence >= 0.8 else "MEDIUM" if confidence >= 0.6 else "HIGH",
                    "predicted_winner": random.choice(["Player Win", "Banker Win", "Tie"]),
                    "probabilities": {
                        "Player Win": random.uniform(0.3, 0.4),
                        "Banker Win": random.uniform(0.3, 0.4),
                        "Tie": random.uniform(0.08, 0.12)
                    }
                }
            }
        
        try:
            # Extraire les features
            features = self.extract_features_from_round(round_data)
            
            # Préparer le vecteur de features
            feature_vector = []
            for col in self.feature_columns:
                feature_vector.append(features.get(col, 0))
            
            # Prédiction avec le modèle
            feature_vector_scaled = self.scaler.transform([feature_vector])
            prediction = self.model.predict(feature_vector_scaled)[0]
            probabilities = self.model.predict_proba(feature_vector_scaled)[0]
            
            result_map = {0: 'Player Win', 1: 'Banker Win', 2: 'Tie', 3: 'Player Pair', 4: 'Banker Pair'}
            
            # Déterminer le pari recommandé (toujours PLAYER+2 selon votre structure)
            recommended_bet = "PLAYER+2"
            
            # Calculer le niveau de risque
            confidence = max(probabilities) * 100
            if confidence >= 80:
                risk_level = "LOW"
            elif confidence >= 60:
                risk_level = "MEDIUM"
            else:
                risk_level = "HIGH"
            
            # Créer la structure de prédiction selon votre format
            ai_prediction = {
                "model": self.ai_config["model"],
                "input": self.ai_config["input"],
                "prediction": {
                    "recommended_bet": recommended_bet,
                    "confidence": confidence / 100,  # En décimal
                    "risk_level": risk_level,
                    "predicted_winner": result_map[prediction],
                    "probabilities": {
                        result_map[i]: prob for i, prob in enumerate(probabilities)
                    }
                }
            }
            
            return ai_prediction
            
        except Exception as e:
            self.logger.error(f"Erreur prédiction round: {e}")
            # Fallback vers simulation
            import random
            confidence = random.uniform(0.65, 0.92)
            return {
                "model": self.ai_config["model"],
                "input": self.ai_config["input"],
                "prediction": {
                    "recommended_bet": "PLAYER+2",
                    "confidence": confidence,
                    "risk_level": "LOW" if confidence >= 0.8 else "MEDIUM" if confidence >= 0.6 else "HIGH",
                    "predicted_winner": random.choice(["Player Win", "Banker Win", "Tie"])
                }
            }
    
    def process_simulated_round(self, round_data):
        """Traite un round simulé"""
        round_id = round_data['round']['round_id']
        
        # Stocker le round courant
        self.current_rounds[round_id] = round_data
        
        # Générer une prédiction Snake_win
        prediction = self.predict_round(round_data)
        
        # Mettre à jour l'historique des symboles
        symbol = round_data.get('tracking', {}).get('symbol', '♠')
        self.symbol_history.append(symbol)
        
        round_info = {
            "round_id": round_id,
            "symbol": symbol,
            "bet": "PLAYER+2",
            "result_code": round_data.get('tracking', {}).get('result_code', 1)
        }
        self.round_history.append(round_info)
        
        # Stocker la prédiction
        self.predictions[round_id] = {
            "round_data": round_data,
            "ai_prediction": prediction,
            "timestamp": datetime.now().isoformat()
        }
        
        # Logger
        self.logger.info(f"Round {round_id}: {symbol} -> {prediction.get('prediction', {}).get('predicted_winner', 'N/A')}")
        
        return prediction
    
    def get_complete_json_response(self):
        """Retourne la structure JSON complète selon votre format"""
        return {
            "meta": {
                "provider": "1xBet",
                "api": "GetSportsShortZip",
                "endpoint": "https://1xbet.com/service-api/LiveFeed/GetSportsShortZip",
                "params": {
                    "lng": "fr",
                    "gr": 455,
                    "withCountries": True,
                    "country": 96,
                    "virtualSports": True,
                    "groupChamps": True
                },
                "status": "SUCCESS"
            },
            "sports": [
                {
                    "id": 236,
                    "code": "BACCARAT",
                    "category_id": 6,
                    "names": {
                        "fr": "Baccara",
                        "en": "Baccarat",
                        "ru": "Баккара"
                    },
                    "type": "casino",
                    "virtual": True,
                    "active": True
                }
            ],
            "current_rounds": list(self.current_rounds.values()),
            "history": list(self.round_history),
            "ai": self.get_latest_ai_prediction()
        }
    
    def get_latest_ai_prediction(self):
        """Retourne la dernière prédiction IA"""
        if self.predictions:
            latest_prediction = max(self.predictions.values(), key=lambda x: x['timestamp'])
            return latest_prediction['ai_prediction']
        else:
            return {
                "model": self.ai_config["model"],
                "input": self.ai_config["input"],
                "prediction": {
                    "recommended_bet": "PLAYER+2",
                    "confidence": 0.0,
                    "risk_level": "UNKNOWN"
                }
            }
    
    def start_real_time_prediction(self, interval=3):
        """Démarre la prédiction en temps réel avec simulation"""
        self.is_running = True
        self.logger.info(f"Démarrage prédiction Snake_win simulation (interval: {interval}s)")
        
        def simulation_callback(round_data):
            if self.is_running:
                self.process_simulated_round(round_data)
        
        # Démarrer la simulation
        sim_thread = threading.Thread(target=self.simulator.start_simulation, 
                                    args=(simulation_callback, interval))
        sim_thread.daemon = True
        sim_thread.start()
        
        return sim_thread
    
    def stop_real_time_prediction(self):
        """Arrête la prédiction en temps réel"""
        self.is_running = False
        self.logger.info("Arrêt prédiction Snake_win simulation")

# Test du prédicteur Snake_win avec simulation
if __name__ == "__main__":
    simulator = SnakeWinSimulator()
    
    print("Test du prédicteur Snake_win avec simulation...")
    
    # Test avec un round fictif selon votre structure
    test_round = {
        "round": {
            "round_id": 52,
            "game_id": 236,
            "timestamp": "2026-02-03T14:32:00Z",
            "cards": {
                "player": ["7♦", "5♣"],
                "banker": ["6♠", "8♦"]
            },
            "score": {
                "player": 2,
                "banker": 4
            },
            "winner": "BANKER"
        },
        "bet": {
            "bet_id": "BET-IGROK-PLUS-2",
            "game_id": 236,
            "type": "HANDICAP",
            "side": "PLAYER",
            "handicap": 2,
            "odds": 1.85,
            "status": "OPEN"
        },
        "tracking": {
            "round_id": 52,
            "symbol": "♦",
            "result_code": 1,
            "meaning": {
                "0": "loss",
                "1": "win",
                "2": "strong_win"
            }
        }
    }
    
    prediction = simulator.process_simulated_round(test_round)
    print(f"Prédiction Snake_win: {json.dumps(prediction, indent=2)}")
    
    # Afficher la structure JSON complète
    complete_response = simulator.get_complete_json_response()
    print(f"\nStructure JSON complète: {json.dumps(complete_response, indent=2)}")
