from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import joblib
import threading
import time
from snake_win_simulator import SnakeWinSimulator

app = Flask(__name__)

# Initialiser le prédicteur Snake_win avec simulation
snake_predictor = SnakeWinSimulator()

class BaccaratPredictor:
    def __init__(self, csv_path='data/twentyone_rounds.csv'):
        self.csv_path = csv_path
        self.data = None
        self.model = None
        self.scaler = None
        self.feature_columns = []
        self.load_data()
        self.load_trained_model()
    
    def load_data(self):
        try:
            self.data = pd.read_csv(self.csv_path, header=None, 
                                  names=['id', 'event_id', 'collected_at', 'option_type', 'odd', 'round_state', 'raw_payload'])
            print(f"Chargé {len(self.data)} enregistrements depuis {self.csv_path}")
        except Exception as e:
            print(f"Erreur chargement CSV: {e}")
            self.data = pd.DataFrame()
    
    def load_trained_model(self):
        try:
            model_data = joblib.load('models/baccarat_model.pkl')
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            print("Modèle IA chargé avec succès")
        except Exception as e:
            print(f"Erreur chargement modèle: {e}")
    
    def preprocess_data(self):
        if self.data.empty:
            return pd.DataFrame()
        
        processed = self.data.copy()
        
        # Extraction des scores depuis round_state
        def extract_scores(row):
            try:
                round_state_str = str(row['round_state']) if pd.notna(row['round_state']) else '{}'
                round_state = json.loads(round_state_str) if round_state_str else {}
                return {
                    'player_score': round_state.get('playerScore', 0),
                    'banker_score': round_state.get('bankerScore', 0),
                    'round_number': round_state.get('roundNumber', 0),
                    'is_live': round_state.get('isLive', False)
                }
            except:
                return {'player_score': 0, 'banker_score': 0, 'round_number': 0, 'is_live': False}
        
        scores_df = processed.apply(extract_scores, axis=1, result_type='expand')
        processed = pd.concat([processed, scores_df], axis=1)
        
        # Conversion du résultat en numérique
        result_map = {'Player Win': 0, 'Banker Win': 1, 'Tie': 2, 'Player Pair': 3, 'Banker Pair': 4}
        processed['result_numeric'] = processed['option_type'].map(result_map).fillna(-1)
        
        # Features temporelles
        processed['timestamp'] = pd.to_datetime(processed['collected_at'], errors='coerce')
        processed['hour'] = processed['timestamp'].dt.hour
        processed['day_of_week'] = processed['timestamp'].dt.dayofweek
        
        return processed
    
    def get_statistics(self):
        if self.data.empty:
            return {}
        
        processed = self.preprocess_data()
        
        stats = {
            'total_rounds': len(processed),
            'results_distribution': processed['option_type'].value_counts().to_dict(),
            'avg_player_score': processed['player_score'].mean(),
            'avg_banker_score': processed['banker_score'].mean(),
            'hourly_distribution': processed.groupby('hour')['option_type'].count().to_dict(),
            'recent_results': processed.tail(10)['option_type'].tolist()
        }
        
        return stats
    
    def extract_features_for_prediction(self, row):
        try:
            round_state_str = str(row['round_state']) if pd.notna(row['round_state']) else '{}'
            raw_payload_str = str(row['raw_payload']) if pd.notna(row['raw_payload']) else '{}'
            
            round_state = json.loads(round_state_str) if round_state_str else {}
            raw_payload = json.loads(raw_payload_str) if raw_payload_str else {}
            
            features = {
                'player_score': round_state.get('playerScore', 0),
                'banker_score': round_state.get('bankerScore', 0),
                'round_number': round_state.get('roundNumber', 0),
                'is_live': 1 if round_state.get('isLive', False) else 0,
                'odd_value': float(row['odd']) if pd.notna(row['odd']) and str(row['odd']) != 'null' else 1.0
            }
            
            timestamp = pd.to_datetime(row['collected_at'], errors='coerce')
            if pd.notna(timestamp):
                features.update({
                    'hour': timestamp.hour,
                    'day_of_week': timestamp.dayofweek,
                    'minute': timestamp.minute
                })
            else:
                features.update({'hour': 0, 'day_of_week': 0, 'minute': 0})
            
            betting_options = raw_payload.get('bettingOptions', [])
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
            
            # Ajouter les features séquentielles (simplifiées)
            recent_data = self.data.tail(50)
            features.update({
                'Player_Win_ma_5': (recent_data['option_type'] == 'Player Win').tail(5).mean(),
                'Banker_Win_ma_5': (recent_data['option_type'] == 'Banker Win').tail(5).mean(),
                'Tie_ma_5': (recent_data['option_type'] == 'Tie').tail(5).mean(),
                'consecutive_Player_Win': 0,
                'consecutive_Banker_Win': 0,
                'consecutive_Tie': 0
            })
            
            return features
            
        except Exception as e:
            print(f"Erreur extraction features: {e}")
            return {col: 0 for col in self.feature_columns}
    
    def predict_next(self, event_id=None):
        if self.data.empty or self.model is None:
            return {'error': 'Pas de données ou modèle disponible'}
        
        # Utiliser la dernière ligne comme base pour la prédiction
        last_row = self.data.iloc[-1]
        features = self.extract_features_for_prediction(last_row)
        
        # S'assurer que toutes les features requises sont présentes
        feature_vector = []
        for col in self.feature_columns:
            feature_vector.append(features.get(col, 0))
        
        # Normalisation et prédiction
        feature_vector_scaled = self.scaler.transform([feature_vector])
        prediction = self.model.predict(feature_vector_scaled)[0]
        probabilities = self.model.predict_proba(feature_vector_scaled)[0]
        
        result_map = {0: 'Player Win', 1: 'Banker Win', 2: 'Tie', 3: 'Player Pair', 4: 'Banker Pair'}
        
        return {
            'prediction': result_map[prediction],
            'probabilities': {
                result_map[i]: prob for i, prob in enumerate(probabilities)
            },
            'confidence': max(probabilities) * 100,
            'based_on': 'Modèle IA entraîné',
            'event_id': event_id
        }

predictor = BaccaratPredictor()

# Démarrer le prédicteur Snake_win avec simulation dans un thread séparé
def start_snake_win_service():
    time.sleep(2)  # Attendre que Flask démarre
    snake_predictor.start_real_time_prediction(interval=3)

snake_thread = threading.Thread(target=start_snake_win_service)
snake_thread.daemon = True
snake_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    return jsonify(predictor.get_statistics())

@app.route('/api/predict')
def predict():
    event_id = request.args.get('event_id')
    return jsonify(predictor.predict_next(event_id))

@app.route('/api/history')
def get_history():
    limit = int(request.args.get('limit', 50))
    processed = predictor.preprocess_data()
    
    if processed.empty:
        return jsonify([])
    
    history = processed.tail(limit).to_dict('records')
    return jsonify(history)

@app.route('/api/events')
def get_events():
    processed = predictor.preprocess_data()
    
    if processed.empty:
        return jsonify([])
    
    # Extraire les events uniques depuis raw_payload
    events = []
    try:
        for _, row in processed.tail(100).iterrows():
            raw_payload = json.loads(row['raw_payload'])
            event = raw_payload.get('event', {})
            if event and event.get('eventId') not in [e.get('eventId') for e in events]:
                events.append({
                    'eventId': event.get('eventId'),
                    'eventName': event.get('eventName'),
                    'sportId': event.get('sportId'),
                    'startTime': event.get('startTime')
                })
    except Exception as e:
        print(f"Erreur extraction events: {e}")
    
    return jsonify(events[-20:])  # Derniers 20 events

# Endpoints Snake_win avec structure JSON exacte - VERSION FONCTIONNELLE
@app.route('/api/snake-win/complete')
def get_snake_win_complete():
    """Retourne la structure JSON complète selon votre format"""
    return jsonify(snake_predictor.get_complete_json_response())

@app.route('/api/snake-win/rounds')
def get_snake_win_rounds():
    """Retourne les rounds actuels avec prédictions"""
    return jsonify({
        "current_rounds": list(snake_predictor.current_rounds.values()),
        "predictions": snake_predictor.predictions,
        "status": "simulation_active"
    })

@app.route('/api/snake-win/history')
def get_snake_win_history():
    """Retourne l'historique avec symboles ♠ ♦ ♣"""
    return jsonify({
        "history": list(snake_predictor.round_history),
        "symbol_history": list(snake_predictor.symbol_history),
        "total_rounds": len(snake_predictor.round_history)
    })

@app.route('/api/snake-win/prediction')
def get_snake_win_prediction():
    """Retourne la dernière prédiction IA"""
    return jsonify(snake_predictor.get_latest_ai_prediction())

@app.route('/api/snake-win/status')
def get_snake_win_status():
    """Retourne le statut du service Snake_win"""
    return jsonify({
        "is_running": snake_predictor.is_running,
        "current_rounds_count": len(snake_predictor.current_rounds),
        "predictions_count": len(snake_predictor.predictions),
        "symbol_history_length": len(snake_predictor.symbol_history),
        "model_info": snake_predictor.ai_config["model"],
        "last_update": datetime.now().isoformat(),
        "mode": "simulation",
        "message": "Simulation active - API 1xBet remplacée par données réalistes"
    })

@app.route('/api/test')
def test_endpoint():
    """Endpoint de test pour vérifier que tout fonctionne"""
    return jsonify({
        "status": "working",
        "timestamp": datetime.now().isoformat(),
        "snake_predictor": {
            "is_running": snake_predictor.is_running,
            "rounds": len(snake_predictor.current_rounds),
            "predictions": len(snake_predictor.predictions)
        },
        "endpoints_available": [
            "/api/snake-win/complete",
            "/api/snake-win/rounds", 
            "/api/snake-win/history",
            "/api/snake-win/prediction",
            "/api/snake-win/status"
        ]
    })

if __name__ == '__main__':
    print("🚀 Démarrage Snake_win Predictor - Mode Simulation")
    print("📊 Structure JSON exacte implémentée")
    print("🔄 Simulation de rounds Baccarat toutes les 3 secondes")
    print("🌐 Accès: http://localhost:5000")
    print("📱 API: http://localhost:5000/api/snake-win/complete")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
