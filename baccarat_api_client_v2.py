import requests
import json
import time
from datetime import datetime
import logging

class BaccaratAPIClientV2:
    def __init__(self):
        self.base_url = "https://1xbet.com/service-api"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
        })
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Configuration API selon votre structure
        self.api_config = {
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
                }
            }
        }
        
        # ID Baccarat selon votre structure
        self.baccarat_id = 236
    
    def get_sports(self):
        """Récupère la liste des sports/jeux"""
        try:
            response = self.session.get(
                self.api_config["meta"]["endpoint"],
                params=self.api_config["meta"]["params"],
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Sports récupérés: {len(data.get('sports', []))}")
                return data
            else:
                self.logger.error(f"Erreur API sports: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur récupération sports: {e}")
            return None
    
    def get_baccarat_games(self):
        """Récupère les jeux Baccarat actifs"""
        try:
            sports_data = self.get_sports()
            if not sports_data:
                return []
            
            # Filtrer pour Baccarat (ID: 236)
            baccarat_sports = [
                sport for sport in sports_data.get('sports', [])
                if sport.get('id') == self.baccarat_id
            ]
            
            if baccarat_sports:
                self.logger.info(f"Baccarat trouvé: {baccarat_sports[0].get('names', {}).get('fr', 'Baccarat')}")
                return baccarat_sports
            else:
                self.logger.warning("Aucun Baccarat trouvé dans les sports")
                return []
                
        except Exception as e:
            self.logger.error(f"Erreur récupération Baccarat: {e}")
            return []
    
    def get_live_baccarat_rounds(self):
        """Récupère les rounds Baccarat en direct"""
        try:
            # Endpoint pour les événements live de Baccarat
            url = f"{self.base_url}/LiveFeed/GetGamesZip"
            params = {
                "lng": "fr",
                "game": self.baccarat_id,
                "virtual": True,
                "count": 50
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                rounds = self.parse_baccarat_rounds(data)
                self.logger.info(f"Rounds Baccarat trouvés: {len(rounds)}")
                return rounds
            else:
                self.logger.error(f"Erreur API rounds: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Erreur récupération rounds: {e}")
            return []
    
    def parse_baccarat_rounds(self, data):
        """Parse les données de rounds selon votre structure JSON"""
        rounds = []
        
        try:
            games = data.get('games', [])
            
            for game_data in games:
                if game_data.get('game_id') == self.baccarat_id:
                    round_info = {
                        "round": {
                            "round_id": game_data.get('id', 0),
                            "game_id": self.baccarat_id,
                            "timestamp": datetime.fromtimestamp(game_data.get('time', 0)).isoformat(),
                            "cards": self.extract_cards(game_data),
                            "score": self.extract_scores(game_data),
                            "winner": self.determine_winner(game_data)
                        },
                        "bet": self.extract_betting_info(game_data),
                        "tracking": self.generate_tracking(game_data)
                    }
                    rounds.append(round_info)
                    
        except Exception as e:
            self.logger.error(f"Erreur parsing rounds: {e}")
            
        return rounds
    
    def extract_cards(self, game_data):
        """Extrait les cartes du jeu"""
        # Simulation basée sur les scores réels
        player_score = game_data.get('score1', 0)
        banker_score = game_data.get('score2', 0)
        
        # Générer des cartes logiques basées sur les scores
        def generate_cards_for_score(score):
            if score == 0:
                return ["10♠", "K♣"]
            elif score <= 3:
                return [f"{score}♠", f"{(3-score)}♣"]
            elif score <= 6:
                return [f"{(score-2)}♦", f"2♣"]
            elif score <= 9:
                return [f"{(score-3)}♥", f"A♠"]
            else:
                return ["A♦", "8♣"]
        
        return {
            "player": generate_cards_for_score(player_score),
            "banker": generate_cards_for_score(banker_score)
        }
    
    def extract_scores(self, game_data):
        """Extrait les scores"""
        return {
            "player": game_data.get('score1', 0),
            "banker": game_data.get('score2', 0)
        }
    
    def determine_winner(self, game_data):
        """Détermine le gagnant"""
        player_score = game_data.get('score1', 0)
        banker_score = game_data.get('score2', 0)
        
        if player_score > banker_score:
            return "PLAYER"
        elif banker_score > player_score:
            return "BANKER"
        else:
            return "TIE"
    
    def extract_betting_info(self, game_data):
        """Extrait les informations de pari selon votre structure"""
        odds = game_data.get('odds', {})
        
        return {
            "bet_id": f"BET-IGROK-PLUS-2-{game_data.get('id', 0)}",
            "game_id": self.baccarat_id,
            "type": "HANDICAP",
            "side": "PLAYER",
            "handicap": 2,
            "odds": odds.get('player', 1.85),
            "status": "OPEN"  # "OPEN", "WIN", "LOSS"
        }
    
    def generate_tracking(self, game_data):
        """Génère le suivi avec symboles ♠ ♦ ♣"""
        # Logique de symboles basée sur patterns
        round_id = game_data.get('id', 0)
        
        # Génération de symboles cycliques
        symbols = ["♠", "♦", "♣"]
        symbol = symbols[round_id % 3]
        
        # Génération de result_code basée sur les scores
        player_score = game_data.get('score1', 0)
        banker_score = game_data.get('score2', 0)
        
        if abs(player_score - banker_score) >= 3:
            result_code = 2  # strong_win
        elif player_score != banker_score:
            result_code = 1  # win
        else:
            result_code = 0  # loss (tie)
        
        return {
            "round_id": round_id,
            "symbol": symbol,
            "result_code": result_code,
            "meaning": {
                "0": "loss",
                "1": "win", 
                "2": "strong_win"
            }
        }
    
    def start_real_time_monitoring(self, callback=None, interval=5):
        """Démarre la surveillance en temps réel"""
        self.logger.info(f"Démarrage monitoring temps réel (interval: {interval}s)")
        
        while True:
            try:
                rounds = self.get_live_baccarat_rounds()
                
                if rounds and callback:
                    for round_data in rounds:
                        callback(round_data)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.logger.info("Arrêt du monitoring")
                break
            except Exception as e:
                self.logger.error(f"Erreur monitoring: {e}")
                time.sleep(interval)

# Test du client API
if __name__ == "__main__":
    client = BaccaratAPIClientV2()
    
    def round_callback(round_data):
        print(f"Round {round_data['round']['round_id']}: {round_data['round']['winner']}")
        print(f"Scores: Player {round_data['round']['score']['player']} - Banker {round_data['round']['score']['banker']}")
        print(f"Symbole: {round_data['tracking']['symbol']} (Code: {round_data['tracking']['result_code']})")
        print("-" * 50)
    
    # Test récupération sports
    sports = client.get_sports()
    if sports:
        print(f"Sports trouvés: {len(sports.get('sports', []))}")
        
        # Test Baccarat
        baccarat_games = client.get_baccarat_games()
        print(f"Jeux Baccarat: {len(baccarat_games)}")
        
        # Test rounds
        rounds = client.get_live_baccarat_rounds()
        print(f"Rounds trouvés: {len(rounds)}")
        
        for round_data in rounds[:3]:
            round_callback(round_data)
