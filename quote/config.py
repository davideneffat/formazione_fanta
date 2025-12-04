from dataclasses import dataclass, field
from typing import List


class Config:
    """Centralizza tutte le costanti e le configurazioni."""
    BASE_URL = "https://betting.sisal.it/api/lettura-palinsesto-sport/palinsesto/prematch"
    EVENTS_URL = f"{BASE_URL}/schedaManifestazione/0/1-209?offerId=0"
    EVENT_DETAIL_URL_TEMPLATE = f"{BASE_URL}/v1/eventDetail/{{codice_palinsesto}}-{{match_id}}?offerId=0&metaTplEnabled=true"
    
    # Prefissi delle chiavi API per le varie scommesse
    MARCATORE_KEY_PREFIX = "28231"
    ASSIST_KEY_PREFIX = "28547"
    SEGNA_CASA_KEY_PREFIX = "165"
    SEGNA_OSPITE_KEY_PREFIX = "166"

    # Impostazioni per le richieste HTTP
    HTTP_TIMEOUT = 10  # secondi
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    MAX_WORKERS = 10 # Numero di thread paralleli per lo scraping
    SIMILARITY_THRESHOLD = 70  # Soglia di similarità per il matching dei nomi dei giocatori

# --- 2. Strutture Dati (Dataclasses) ---

@dataclass
class Match:
    id: str
    description: str
    home_team: str
    away_team: str

@dataclass
class PlayerQuote:
    player_name: str
    quote: float

@dataclass
class MatchGoalQuotes:
    match_id: str
    home_team_scores_quote: float
    away_team_scores_quote: float

@dataclass
class ProcessedData:
    """Contenitore per tutti i dati finali elaborati."""
    scorers: List[PlayerQuote] = field(default_factory=list)
    assists: List[PlayerQuote] = field(default_factory=list)
    team_goal_stats: List[dict] = field(default_factory=list)