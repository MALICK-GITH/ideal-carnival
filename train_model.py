import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
import json
from datetime import datetime
import os

class BaccaratModelTrainer:
    def __init__(self, csv_path='data/twentyone_rounds.csv'):
        self.csv_path = csv_path
        self.data = None
        self.model = None
        self.scaler = None
        self.feature_columns = []
        
    def load_and_preprocess_data(self):
        print("Chargement des données...")
        try:
            self.data = pd.read_csv(self.csv_path, header=None, 
                                  names=['id', 'event_id', 'collected_at', 'option_type', 'odd', 'round_state', 'raw_payload'])
            print(f"Chargé {len(self.data)} enregistrements")
        except Exception as e:
            print(f"Erreur chargement CSV: {e}")
            return False
            
        # Nettoyage et prétraitement
        processed = self.data.copy()
        
        # Extraction des scores depuis round_state
        def extract_features(row):
            try:
                # Gérer les différents types de données
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
                
                # Features temporelles
                timestamp = pd.to_datetime(row['collected_at'], errors='coerce')
                if pd.notna(timestamp):
                    features.update({
                        'hour': timestamp.hour,
                        'day_of_week': timestamp.dayofweek,
                        'minute': timestamp.minute
                    })
                else:
                    features.update({'hour': 0, 'day_of_week': 0, 'minute': 0})
                
                # Extraire les cotes depuis bettingOptions
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
                
                return features
                
            except Exception as e:
                print(f"Erreur extraction features: {e}")
                return {
                    'player_score': 0, 'banker_score': 0, 'round_number': 0,
                    'is_live': 0, 'odd_value': 1.0, 'hour': 0, 
                    'day_of_week': 0, 'minute': 0,
                    'player_win_odd': 1.0, 'banker_win_odd': 1.0, 'tie_odd': 1.0
                }
        
        # Appliquer l'extraction de features
        features_df = processed.apply(extract_features, axis=1, result_type='expand')
        
        # Ajouter les features au dataframe
        processed = pd.concat([processed, features_df], axis=1)
        
        # Conversion du résultat en numérique
        result_map = {'Player Win': 0, 'Banker Win': 1, 'Tie': 2, 'Player Pair': 3, 'Banker Pair': 4}
        processed['target'] = processed['option_type'].map(result_map).fillna(-1)
        
        # Filtrer les résultats valides
        processed = processed[processed['target'] != -1]
        
        print(f"Données prétraitées: {len(processed)} enregistrements valides")
        self.processed_data = processed
        return True
    
    def create_sequential_features(self, window_size=5):
        """Crée des features séquentielles basées sur les résultats précédents"""
        print("Création des features séquentielles...")
        
        data = self.processed_data.copy()
        data = data.sort_values('collected_at')
        
        # Features de séquence pour chaque type de résultat
        result_types = ['Player Win', 'Banker Win', 'Tie']
        
        for result_type in result_types:
            # Créer une colonne binaire pour ce résultat
            data[f'is_{result_type.replace(" ", "_")}'] = (data['option_type'] == result_type).astype(int)
            
            # Moyenne mobile sur la fenêtre
            data[f'{result_type.replace(" ", "_")}_ma_{window_size}'] = (
                data[f'is_{result_type.replace(" ", "_")}']
                .rolling(window=window_size, min_periods=1)
                .mean()
            )
        
        # Compter les occurrences consécutives
        for result_type in result_types:
            col_name = f'consecutive_{result_type.replace(" ", "_")}'
            data[col_name] = 0
            count = 0
            
            for i in range(len(data)):
                if data.iloc[i]['option_type'] == result_type:
                    count += 1
                else:
                    count = 0
                data.loc[data.index[i], col_name] = count
        
        self.processed_data = data
        print("Features séquentielles créées")
    
    def prepare_training_data(self):
        """Prépare les données pour l'entraînement"""
        # Colonnes de features
        feature_cols = [
            'player_score', 'banker_score', 'round_number', 'is_live', 'odd_value',
            'hour', 'day_of_week', 'minute',
            'player_win_odd', 'banker_win_odd', 'tie_odd'
        ]
        
        # Ajouter les features séquentielles si elles existent
        sequential_cols = [col for col in self.processed_data.columns 
                          if 'ma_' in col or 'consecutive_' in col]
        feature_cols.extend(sequential_cols)
        
        # Filtrer seulement les colonnes qui existent
        self.feature_columns = [col for col in feature_cols if col in self.processed_data.columns]
        
        X = self.processed_data[self.feature_columns]
        y = self.processed_data['target']
        
        # Gérer les valeurs manquantes
        X = X.fillna(X.mean())
        
        print(f"Features utilisées: {len(self.feature_columns)}")
        print(f"Distribution des targets: {y.value_counts().to_dict()}")
        
        return X, y
    
    def train_model(self):
        """Entraîne le modèle de prédiction"""
        print("Préparation des données d'entraînement...")
        
        X, y = self.prepare_training_data()
        
        # Division train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Normalisation
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Entraînement du modèle
        print("Entraînement du modèle...")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Évaluation
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"Accuracy: {accuracy:.3f}")
        print("\nRapport de classification:")
        print(classification_report(y_test, y_pred, 
                                  target_names=['Player Win', 'Banker Win', 'Tie', 'Player Pair', 'Banker Pair']))
        
        # Importance des features
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\nTop 10 features les plus importantes:")
        print(feature_importance.head(10))
        
        return accuracy
    
    def save_model(self, model_path='models/baccarat_model.pkl'):
        """Sauvegarde le modèle entraîné"""
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'training_date': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, model_path)
        print(f"Modèle sauvegardé dans {model_path}")
    
    def load_model(self, model_path='models/baccarat_model.pkl'):
        """Charge un modèle entraîné"""
        try:
            model_data = joblib.load(model_path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            print(f"Modèle chargé depuis {model_path}")
            print(f"Date d'entraînement: {model_data['training_date']}")
            return True
        except Exception as e:
            print(f"Erreur chargement modèle: {e}")
            return False
    
    def predict(self, features):
        """Fait une prédiction avec le modèle entraîné"""
        if self.model is None:
            return None
        
        # S'assurer que les features sont dans le bon ordre
        feature_vector = []
        for col in self.feature_columns:
            feature_vector.append(features.get(col, 0))
        
        # Normalisation
        feature_vector_scaled = self.scaler.transform([feature_vector])
        
        # Prédiction
        prediction = self.model.predict(feature_vector_scaled)[0]
        probabilities = self.model.predict_proba(feature_vector_scaled)[0]
        
        result_map = {0: 'Player Win', 1: 'Banker Win', 2: 'Tie', 3: 'Player Pair', 4: 'Banker Pair'}
        
        return {
            'prediction': result_map[prediction],
            'probabilities': {
                result_map[i]: prob for i, prob in enumerate(probabilities)
            },
            'confidence': max(probabilities) * 100
        }

def main():
    trainer = BaccaratModelTrainer()
    
    # Charger et prétraiter les données
    if not trainer.load_and_preprocess_data():
        return
    
    # Créer les features séquentielles
    trainer.create_sequential_features(window_size=5)
    
    # Entraîner le modèle
    accuracy = trainer.train_model()
    
    # Sauvegarder le modèle
    trainer.save_model()
    
    print(f"\nEntraînement terminé! Accuracy: {accuracy:.3f}")

if __name__ == "__main__":
    main()
