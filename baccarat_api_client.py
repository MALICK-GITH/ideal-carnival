import requests
import json
import time
from datetime import datetime
import logging

class BaccaratAPIClient:
    def __init__(self, base_url="https://api.1xbet.com", sport_id=146):
        self.base_url = base_url
        self.sport_id = sport_id
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self._api_fail_count = 0
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def get_live_events(self):
        """Récupère les événements Baccarat en direct"""
        try:
            url = f"{self.base_url}/LiveFeed/Get1x2_Virtual"
            params = {
                'sports': self.sport_id,
                'count': 50,
                'lng': 'fr',
                'domain': 'com'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                self._api_fail_count = 0
                data = response.json()
                return self.parse_events(data)
            else:
                self._api_fail_count += 1
                if self._api_fail_count <= 2 or self._api_fail_count % 12 == 0:
                    self.logger.warning(f"API 1xbet: erreur {response.status_code} (tentative {self._api_fail_count})")
                return []
                
        except Exception as e:
            self._api_fail_count += 1
            if self._api_fail_count <= 2 or self._api_fail_count % 12 == 0:
                self.logger.warning(f"API 1xbet indisponible - utilisation BDD (tentative {self._api_fail_count}): {type(e).__name__}")
            return []
    
    def parse_events(self, data):
        """Parse les données de l'API pour extraire les événements Baccarat"""
        events = []
        
        try:
            if 'Value' in data:
                for event_data in data['Value']:
                    # Filtrer uniquement les événements Baccarat/TwentyOne
                    if event_data.get('SportId') == self.sport_id:
                        event = {
                            'eventId': event_data.get('Id'),
                            'eventName': event_data.get('L', 'Unknown Event'),
                            'startTime': datetime.fromtimestamp(event_data.get('S', 0)).isoformat(),
                            'isLive': True,
                            'roundNumber': event_data.get('I', 0),
                            'playerScore': event_data.get('SC', {}).get('S1', 0),
                            'bankerScore': event_data.get('SC', {}).get('S2', 0),
                            'gamePhase': self.get_game_phase(event_data),
                            'bettingOptions': self.parse_betting_options(event_data)
                        }
                        events.append(event)
                        
        except Exception as e:
            self.logger.error(f"Erreur parsing events: {e}")
            
        return events
    
    def get_game_phase(self, event_data):
        """Détermine la phase actuelle du jeu"""
        # Logique pour déterminer si le jeu est en cours, résultat, etc.
        scores = event_data.get('SC', {})
        if scores.get('S1', 0) > 0 or scores.get('S2', 0) > 0:
            return "Result"
        else:
            return "Betting"
    
    def parse_betting_options(self, event_data):
        """Extrait les options de paris avec leurs cotes"""
        options = []
        
        try:
            # Les cotes sont généralement dans 'E' ou 'O'
            odds_data = event_data.get('E', [])
            
            # Mapping des types de paris
            bet_mapping = {
                1: {'optionType': 'Player Win', 'optionName': 'Player Win'},
                2: {'optionType': 'Banker Win', 'optionName': 'Banker Win'},
                3: {'optionType': 'Tie', 'optionName': 'Tie'},
                4: {'optionType': 'Player Pair', 'optionName': 'Player Pair'},
                5: {'optionType': 'Banker Pair', 'optionName': 'Banker Pair'}
            }
            
            for odd in odds_data:
                bet_type = odd.get('T')
                if bet_type in bet_mapping:
                    option = bet_mapping[bet_type].copy()
                    option.update({
                        'odd': odd.get('C', 1.0),
                        'optionId': odd.get('I', 0),
                        'group': 'Main'
                    })
                    options.append(option)
                    
        except Exception as e:
            self.logger.error(f"Erreur parsing betting options: {e}")
            
        return options
    
    def get_event_details(self, event_id):
        """Récupère les détails complets d'un événement spécifique"""
        try:
            url = f"{self.base_url}/LiveFeed/GetGameZip"
            params = {
                'id': event_id,
                'lng': 'fr',
                'domain': 'com'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                # Les données peuvent être compressées, nécessitant décompression
                return response.json()
            else:
                self.logger.error(f"Erreur détails event {event_id}: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur récupération détails event {event_id}: {e}")
            return None
    
    def start_real_time_monitoring(self, callback=None, interval=3):
        """Démarre la surveillance en temps réel des événements"""
        self.logger.info(f"Démarrage monitoring temps réel (interval: {interval}s)")
        
        while True:
            try:
                events = self.get_live_events()
                
                if events:
                    self.logger.info(f"Trouvé {len(events)} événements live")
                    if callback:
                        for event in events:
                            callback(event)
                
                # Backoff progressif si API down: 30s après 6 échecs, 60s après 12, max 120s
                if self._api_fail_count > 0:
                    sleep_time = min(30 + (self._api_fail_count // 6) * 15, 120)
                else:
                    sleep_time = interval
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                self.logger.info("Arrêt du monitoring")
                break
            except Exception as e:
                self.logger.warning(f"Erreur monitoring: {e}")
                time.sleep(30)

# Test du client API
if __name__ == "__main__":
    client = BaccaratAPIClient()
    
    def event_callback(event):
        print(f"Event: {event['eventName']} - Phase: {event['gamePhase']}")
        print(f"Scores: Player {event['playerScore']} - Banker {event['bankerScore']}")
        print(f"Cotes: {[opt['optionType'] + ': ' + str(opt['odd']) for opt in event['bettingOptions'][:3]]}")
        print("-" * 50)
    
    # Test récupération events
    events = client.get_live_events()
    print(f"Events trouvés: {len(events)}")
    
    for event in events[:3]:
        event_callback(event)
