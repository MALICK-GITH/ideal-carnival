from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import joblib
import threading
import time
from real_time_predictor import RealTimeBaccaratPredictor

app = Flask(__name__)

# Initialiser le prédicteur temps réel
real_time_predictor = RealTimeBaccaratPredictor()

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
        
        # Features temporelles (format ISO8601 pour éviter le UserWarning)
        try:
            processed['timestamp'] = pd.to_datetime(processed['collected_at'], format='ISO8601', errors='coerce')
        except (ValueError, TypeError):
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

# Démarrer le prédicteur temps réel dans un thread séparé
def start_real_time_service():
    time.sleep(2)  # Attendre que Flask démarre
    real_time_predictor.start_real_time_prediction(interval=5)

real_time_thread = threading.Thread(target=start_real_time_service)
real_time_thread.daemon = True
real_time_thread.start()

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

# Nouveaux endpoints pour le temps réel
@app.route('/api/realtime/events')
def get_realtime_events():
    """Retourne les événements actuels de l'API Baccarat"""
    return jsonify(real_time_predictor.get_current_events())

@app.route('/api/realtime/predictions')
def get_realtime_predictions():
    """Retourne toutes les prédictions en temps réel"""
    return jsonify(real_time_predictor.get_current_predictions())

@app.route('/api/realtime/predict/<int:event_id>')
def get_realtime_prediction(event_id):
    """Retourne la prédiction pour un événement spécifique"""
    prediction = real_time_predictor.get_prediction_for_event(event_id)
    if prediction:
        return jsonify(prediction)
    else:
        return jsonify({'error': 'Prédiction non trouvée pour cet événement'}), 404

@app.route('/api/realtime/status')
def get_realtime_status():
    """Retourne le statut du service temps réel"""
    return jsonify({
        'is_running': real_time_predictor.is_running,
        'current_events_count': len(real_time_predictor.get_current_events()),
        'predictions_count': len(real_time_predictor.get_current_predictions()),
        'last_update': datetime.now().isoformat()
    })

def _build_event_for_prediction(match):
    """Construit un objet event pour predict_event à partir d'un match"""
    start_time = match.get('startTime')
    if not start_time:
        start_time = datetime.now().isoformat()
    elif isinstance(start_time, (int, float)):
        try:
            start_time = datetime.fromtimestamp(start_time).isoformat()
        except (ValueError, OSError):
            start_time = datetime.now().isoformat()
    return {
        'eventId': match.get('eventId'),
        'eventName': match.get('eventName', 'Baccarat'),
        'playerScore': match.get('playerScore', 0),
        'bankerScore': match.get('bankerScore', 0),
        'roundNumber': match.get('roundNumber', 0),
        'gamePhase': match.get('gamePhase', 'Betting'),
        'startTime': start_time,
        'isLive': match.get('isLive', False),
        'bettingOptions': match.get('bettingOptions', [
            {'optionType': 'Player Win', 'odd': 1.95},
            {'optionType': 'Banker Win', 'odd': 1.85},
            {'optionType': 'Tie', 'odd': 8.5}
        ])
    }

def _add_prediction_to_match(match):
    """Ajoute une prédiction IA à chaque match"""
    try:
        event_obj = _build_event_for_prediction(match)
        prediction = real_time_predictor.predict_event(event_obj)
        if 'error' not in prediction:
            match['prediction'] = prediction
        else:
            match['prediction'] = None
    except Exception as e:
        match['prediction'] = None
    return match

@app.route('/api/baccarat/matches')
def get_baccarat_matches():
    """Retourne tous les matchs Baccarat avec prédiction IA pour chacun"""
    matches = []
    seen_ids = set()
    
    # 1. Matchs temps réel (priorité) - API 1xbet
    realtime_events = real_time_predictor.get_current_events()
    for event_id, event in realtime_events.items():
        if event_id not in seen_ids:
            seen_ids.add(event_id)
            match = {
                'eventId': event.get('eventId'),
                'eventName': event.get('eventName', 'Baccarat'),
                'playerScore': event.get('playerScore', 0),
                'bankerScore': event.get('bankerScore', 0),
                'roundNumber': event.get('roundNumber', 0),
                'gamePhase': event.get('gamePhase', 'Betting'),
                'startTime': event.get('startTime'),
                'source': 'live',
                'isLive': True,
                'bettingOptions': event.get('bettingOptions', [])
            }
            # Prédiction déjà dans real_time_predictor ou on la génère
            pred = real_time_predictor.get_prediction_for_event(event_id)
            match['prediction'] = pred if pred and 'error' not in pred else None
            if match['prediction'] is None:
                _add_prediction_to_match(match)
            matches.append(match)
    
    # 2. Matchs depuis la base de données (quand API down ou complément)
    processed = predictor.preprocess_data()
    if not processed.empty:
        try:
            event_data = {}
            for _, row in processed.tail(500).iloc[::-1].iterrows():
                try:
                    raw_payload = json.loads(row['raw_payload']) if pd.notna(row['raw_payload']) else {}
                    event = raw_payload.get('event', {})
                    event_id = event.get('eventId')
                    if event_id and event_id not in seen_ids:
                        rs = row.get('round_state')
                        round_state = {}
                        if pd.notna(rs) and str(rs) not in ('nan', '{}', ''):
                            try:
                                round_state = json.loads(str(rs)) if isinstance(rs, str) else (rs if isinstance(rs, dict) else {})
                            except (json.JSONDecodeError, TypeError):
                                pass
                        seen_ids.add(event_id)
                        betting_opts = raw_payload.get('bettingOptions', [])
                        if not isinstance(betting_opts, list):
                            betting_opts = []
                        match = {
                            'eventId': event_id,
                            'eventName': event.get('eventName', 'Baccarat'),
                            'playerScore': round_state.get('playerScore', 0) if isinstance(round_state, dict) else 0,
                            'bankerScore': round_state.get('bankerScore', 0) if isinstance(round_state, dict) else 0,
                            'roundNumber': round_state.get('roundNumber', 0) if isinstance(round_state, dict) else 0,
                            'gamePhase': 'Betting' if (isinstance(round_state, dict) and round_state.get('playerScore', 0) == 0 and round_state.get('bankerScore', 0) == 0) else 'Result',
                            'startTime': event.get('startTime'),
                            'source': 'database',
                            'isLive': round_state.get('isLive', False) if isinstance(round_state, dict) else False,
                            'bettingOptions': betting_opts if isinstance(betting_opts, list) else []
                        }
                        match = _add_prediction_to_match(match)
                        event_data[event_id] = match
                except (json.JSONDecodeError, TypeError):
                    continue
            db_matches = list(event_data.values())[:30]
            if not matches:
                matches = db_matches
            else:
                matches.extend(db_matches)
        except Exception as e:
            print(f"Erreur extraction matchs BDD: {e}")
    
    return jsonify({'matches': matches, 'count': len(matches)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
