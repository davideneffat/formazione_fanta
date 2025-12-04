import requests
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Tuple, Any
from quote.config import Config, Match, PlayerQuote, MatchGoalQuotes, ProcessedData
from thefuzz import process, fuzz
from quote.save import save_all_quotes_to_dataframe

# --- 1. Configurazione e Setup del Logging ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# --- 3. Logica di Scraping ---

def get_next_events(session: requests.Session) -> Tuple[List[Match], Optional[str]]:
    """Recupera la lista delle prossime partite e il codice palinsesto."""
    logging.info("Recupero della lista delle prossime partite...")
    try:
        response = session.get(Config.EVENTS_URL, timeout=Config.HTTP_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        matches = []
        codice_palinsesto = None

        scommessa_map = data.get('scommessaMap', {})
        if not scommessa_map:
            logging.warning("Nessuna 'scommessaMap' trovata nella risposta API degli eventi.")
            return [], None

        for value in scommessa_map.values():
            if not codice_palinsesto and value.get('codicePalinsesto'):
                codice_palinsesto = str(value['codicePalinsesto'])
            
            description = value.get('descrizioneAvvenimento', '')
            teams = description.split(" - ")
            if len(teams) == 2:
                matches.append(Match(
                    id=str(value['codiceAvvenimento']),
                    description=description,
                    home_team=teams[0],
                    away_team=teams[1]
                ))
        
        logging.info(f"Trovate {len(matches)} partite. Codice Palinsesto: {codice_palinsesto}")
        return matches, codice_palinsesto

    except requests.exceptions.RequestException as e:
        logging.error(f"Errore critico durante il recupero degli eventi: {e}")
        return [], None

def get_quotes_for_match(session: requests.Session, match_id: str, codice_palinsesto: str) -> Tuple[List[PlayerQuote], List[PlayerQuote], Optional[MatchGoalQuotes]]:
    """Ottiene le quote per marcatori, assist e gol per una singola partita."""
    url = Config.EVENT_DETAIL_URL_TEMPLATE.format(codice_palinsesto=codice_palinsesto, match_id=match_id)
    
    scorers = []
    assists = []
    goal_quotes = None

    try:
        response = session.get(url, timeout=Config.HTTP_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        info_map = data.get('infoAggiuntivaMap', {})
        if not info_map:
            return [], [], None

        segna_casa_q = 1.0
        segna_ospite_q = 1.0

        for key, value in info_map.items():
            desc = value.get('descrizione', 'N/A')
            quota_raw = value.get('esitoList', [{}])[0].get('quota', 100)
            quota = quota_raw / 100.0
            
            # Es: "12345-67890-28231-1"
            key_parts = key.split('-')
            if len(key_parts) < 3: continue
            
            bet_type_id = key_parts[2]

            if bet_type_id == Config.MARCATORE_KEY_PREFIX:
                player_name = desc.replace(" SEGNA O SUO SOSTITUTO INCL. T.S.", "")
                scorers.append(PlayerQuote(player_name, quota))
            elif bet_type_id == Config.ASSIST_KEY_PREFIX:
                player_name = desc.replace(" ASSIST O SUO SOSTITUTO INCL. T.S.", "")
                assists.append(PlayerQuote(player_name, quota))
            elif bet_type_id == Config.SEGNA_CASA_KEY_PREFIX:
                segna_casa_q = quota
            elif bet_type_id == Config.SEGNA_OSPITE_KEY_PREFIX:
                segna_ospite_q = quota

        goal_quotes = MatchGoalQuotes(match_id, segna_casa_q, segna_ospite_q)
        return scorers, assists, goal_quotes

    except requests.exceptions.RequestException as e:
        logging.warning(f"Errore recupero quote per match {match_id}: {e}")
        return [], [], None

def fetch_and_process_all_data(matches: List[Match], codice_palinsesto: str) -> ProcessedData:
    """Coordina il download parallelo di tutte le quote e processa i dati aggregati."""
    logging.info(f"Recupero dettagli per {len(matches)} partite in parallelo (max {Config.MAX_WORKERS} workers)...")
    
    all_scorers: List[PlayerQuote] = []
    all_assists: List[PlayerQuote] = []
    all_goal_quotes: Dict[str, MatchGoalQuotes] = {}

    with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
        with requests.Session() as session:
            session.headers.update(Config.HEADERS)
            
            future_to_match = {
                executor.submit(get_quotes_for_match, session, match.id, codice_palinsesto): match
                for match in matches
            }
            
            for i, future in enumerate(as_completed(future_to_match)):
                match = future_to_match[future]
                logging.info(f"Processata partita {i+1}/{len(matches)}: {match.description}")
                try:
                    scorers, assists, goal_quotes = future.result()
                    all_scorers.extend(scorers)
                    all_assists.extend(assists)
                    if goal_quotes:
                        all_goal_quotes[goal_quotes.match_id] = goal_quotes
                except Exception as exc:
                    logging.error(f'Match {match.id} ha generato un\'eccezione: {exc}')
    
    logging.info("Elaborazione e aggregazione dei dati raccolti...")
    
    # Rimuovi duplicati mantenendo l'ultimo valore e ordina
    unique_scorers = sorted(list({p.player_name: p for p in all_scorers}.values()), key=lambda p: p.player_name)
    unique_assists = sorted(list({p.player_name: p for p in all_assists}.values()), key=lambda p: p.player_name)
    
    # Combina info partite con quote gol
    team_goal_stats = []
    for match in matches:
        quotes = all_goal_quotes.get(match.id)
        if quotes:
            team_goal_stats.append({
                "match_id": match.id,
                "home_team": match.home_team,
                "away_team": match.away_team,
                "prob_home_concedes_goal": 100 / quotes.away_team_scores_quote if quotes.away_team_scores_quote > 0 else 0,
                "prob_away_concedes_goal": 100 / quotes.home_team_scores_quote if quotes.home_team_scores_quote > 0 else 0
            })
            
    logging.info("Elaborazione completata.")
    return ProcessedData(scorers=unique_scorers, assists=unique_assists, team_goal_stats=team_goal_stats)


def find_best_match(name_to_find: str, choices: List[str]) -> Optional[Tuple[str, int]]:
    """
    Trova la migliore corrispondenza per un nome in una lista di scelte.
    Usa `process.extractOne` che è ottimizzato per questo.
    Restituisce una tupla (nome_trovato, punteggio_similarità) o None.
    """
    if not choices:
        return None
    # Usiamo il token_sort_ratio che gestisce bene l'ordine delle parole (es. "Vazquez D." vs "D. Vazquez")
    best_match = process.extractOne(name_to_find, choices, scorer=fuzz.token_sort_ratio)
    if best_match and best_match[1] >= Config.SIMILARITY_THRESHOLD:
        return best_match
    return None


def get_roster_quotes(roster: Dict[str, List[Tuple[str, str]]], scraped_data: ProcessedData) -> Dict[str, List[Dict[str, Any]]]:
    """
    Filtra e abbina i dati scaricati con i giocatori e le squadre del roster fornito.
    """
    roster_quotes: Dict[str, List[Dict[str, Any]]] = {
        "Por": [], "Dif": [], "Cen": [], "Att": []
    }

    # Prepara le liste di nomi e squadre dai dati scaricati per il matching
    scorer_names = [p.player_name for p in scraped_data.scorers]
    assist_names = [p.player_name for p in scraped_data.assists]
    
    # Crea dizionari per un accesso rapido alle quote
    scorer_quotes_map = {p.player_name: p.quote for p in scraped_data.scorers}
    assist_quotes_map = {p.player_name: p.quote for p in scraped_data.assists}
    
    # --- Processa Portieri ---
    for name, team in roster.get("Por", []):
        team_stats = None
        # Trova la partita che coinvolge la squadra del portiere
        for stats in scraped_data.team_goal_stats:
             # Usiamo `in` per gestire nomi parziali (es. "Roma" vs "AS Roma")
            if team.lower() in stats["home_team"].lower():
                team_stats = { "prob_concedes": stats["prob_home_concedes_goal"] }
                break
            elif team.lower() in stats["away_team"].lower():
                team_stats = { "prob_concedes": stats["prob_away_concedes_goal"] }
                break
        
        roster_quotes["Por"].append({
            "name": name,
            "team": team,
            "prob_concedes": team_stats["prob_concedes"] if team_stats else None
        })

    # --- Processa Giocatori di Movimento (Dif, Cen, Att) ---
    for role in ["Dif", "Cen", "Att"]:
        for name, team in roster.get(role, []):
            player_data = {"name": name, "team": team, "prob_goal": None, "prob_assist": None}

            # Cerca il marcatore più simile
            best_scorer_match = find_best_match(name, scorer_names)
            if best_scorer_match:
                matched_name = best_scorer_match[0]
                quote = scorer_quotes_map.get(matched_name, 0)
                player_data["prob_goal"] = 100 / quote if quote > 0 else 0

            # Cerca l'assist-man più simile
            best_assist_match = find_best_match(name, assist_names)
            if best_assist_match:
                matched_name = best_assist_match[0]
                quote = assist_quotes_map.get(matched_name, 0)
                player_data["prob_assist"] = 100 / quote if quote > 0 else 0
            
            roster_quotes[role].append(player_data)

    return roster_quotes


def format_roster_quotes_for_telegram(roster_quotes: Dict[str, List[Dict[str, Any]]]) -> str:
    """Formatta le quote del roster in un messaggio per Telegram."""
    message = "📊 *Probabilità per la tua rosa*\n\n"

    def format_prob(value, suffix='%'):
        return f"{value:.2f}{suffix}" if value is not None else "N/D"
    
    # Formatta Portieri
    message += "🧤 *PORTIERI* (Prob. subire gol)\n```\n"
    sorted_gks = sorted(roster_quotes.get("Por", []), key=lambda p: p["prob_concedes"] if p["prob_concedes"] is not None else 999)
    for p in sorted_gks:
        message += f"{p['name']:<15} {format_prob(p['prob_concedes']):>6}\n" # Aumenta lo spazio per N/D
    message += "```\n"

    for role_info in [
        ("🛡️ *DIFENSORI*", "Dif"),
        ("🧠 *CENTROCAMPISTI*", "Cen"),
        ("⚽️ *ATTACCANTI*", "Att")
    ]:
        title, role = role_info
        message += f"{title} (Gol% / Assist%)\n```\n"
        
        # Ordina per somma di probabilità, trattando None come 0
        players = roster_quotes.get(role, [])
        sorted_players = sorted(players, key=lambda p: (p["prob_goal"] or 0) + (p["prob_assist"] or 0), reverse=True)
        
        for p in sorted_players:
            goal_prob_str = format_prob(p['prob_goal'])
            assist_prob_str = format_prob(p['prob_assist'])
            message += f"{p['name']:<15} {goal_prob_str:>6} / {assist_prob_str:>6}\n"
        message += "```\n"

    return message



def run_scraper_for_roster(roster: Dict[str, List[Tuple[str, str]]]) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """
    Esegue lo scraping e abbina i risultati al roster fornito.
    """
    with requests.Session() as session:
        session.headers.update(Config.HEADERS)
        matches, codice_palinsesto = get_next_events(session)

        if not matches or not codice_palinsesto:
            logging.error("Scraping fallito: non sono stati trovati match o il codice palinsesto.")
            return None

        scraped_data = fetch_and_process_all_data(matches, codice_palinsesto)
        
        if not scraped_data:
            return None
        
        # ==============================================================================
        #SALVATAGGIO DEL DATAFRAME CON TUTTE LE QUOTE
        save_all_quotes_to_dataframe(scraped_data)
        # ==============================================================================
            
        roster_quotes = get_roster_quotes(roster, scraped_data)
        return roster_quotes