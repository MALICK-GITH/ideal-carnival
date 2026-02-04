import json
import time
import random
from datetime import datetime, timedelta

class BaccaratSimulator:
    def __init__(self):
        self.round_counter = 1000
        self.symbols = ["♠", "♦", "♣"]
        self.current_symbol_index = 0
        
    def generate_realistic_round(self):
        """Génère un round Baccarat réaliste"""
        self.round_counter += 1
        
        # Génération de scores réalistes
        player_score = random.randint(0, 9)
        banker_score = random.randint(0, 9)
        
        # Déterminer le gagnant
        if player_score > banker_score:
            winner = "PLAYER"
        elif banker_score > player_score:
            winner = "BANKER"
        else:
            winner = "TIE"
        
        # Génération de cartes logiques
        def generate_cards(score):
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
        
        # Symbole cyclique
        symbol = self.symbols[self.current_symbol_index % 3]
        self.current_symbol_index += 1
        
        # Code résultat basé sur la différence de scores
        score_diff = abs(player_score - banker_score)
        if score_diff >= 3:
            result_code = 2  # strong_win
        elif player_score != banker_score:
            result_code = 1  # win
        else:
            result_code = 0  # loss (tie)
        
        round_data = {
            "round": {
                "round_id": self.round_counter,
                "game_id": 236,
                "timestamp": datetime.now().isoformat(),
                "cards": {
                    "player": generate_cards(player_score),
                    "banker": generate_cards(banker_score)
                },
                "score": {
                    "player": player_score,
                    "banker": banker_score
                },
                "winner": winner
            },
            "bet": {
                "bet_id": f"BET-IGROK-PLUS-2-{self.round_counter}",
                "game_id": 236,
                "type": "HANDICAP",
                "side": "PLAYER",
                "handicap": 2,
                "odds": round(random.uniform(1.80, 2.10), 2),
                "status": "OPEN"
            },
            "tracking": {
                "round_id": self.round_counter,
                "symbol": symbol,
                "result_code": result_code,
                "meaning": {
                    "0": "loss",
                    "1": "win",
                    "2": "strong_win"
                }
            }
        }
        
        return round_data
    
    def start_simulation(self, callback=None, interval=3):
        """Démarre la simulation de rounds en temps réel"""
        print(f"Démarrage simulation Baccarat (interval: {interval}s)")
        
        while True:
            try:
                round_data = self.generate_realistic_round()
                
                if callback:
                    callback(round_data)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("Arrêt simulation")
                break
            except Exception as e:
                print(f"Erreur simulation: {e}")
                time.sleep(interval)

# Test du simulateur
if __name__ == "__main__":
    simulator = BaccaratSimulator()
    
    def round_callback(round_data):
        print(f"Round {round_data['round']['round_id']}: {round_data['round']['winner']}")
        print(f"Scores: Player {round_data['round']['score']['player']} - Banker {round_data['round']['score']['banker']}")
        print(f"Symbole: {round_data['tracking']['symbol']} (Code: {round_data['tracking']['result_code']})")
        print(f"Cote: {round_data['bet']['odds']}")
        print("-" * 50)
    
    # Test simulation
    print("Test simulation Baccarat...")
    simulator.start_simulation(round_callback, interval=2)
