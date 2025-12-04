import os
import json
import logging
from typing import List, Dict, Tuple
from openai import AsyncOpenAI, BadRequestError
from dotenv import load_dotenv
import httpx

load_dotenv()

# Configurazione del logging anche qui
logging.basicConfig(level=logging.INFO)

FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_API_KEY")
SERIE_A_ID = 2019

client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


async def get_next_matchday_fixtures():
    """Recupera le partite della prossima giornata di Serie A."""
    if not FOOTBALL_DATA_TOKEN:
        return "Errore: Chiave API per i dati sul calcio non trovata."

    url = f"https://api.football-data.org/v4/competitions/{SERIE_A_ID}/matches?status=SCHEDULED"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()  # Solleva un'eccezione per errori HTTP (4xx o 5xx)
            data = response.json()
            
            if not data.get("matches"):
                return "Nessuna partita programmata trovata per la Serie A."
            
            # Formatta le partite in una stringa leggibile
            matchday = data['matches'][0]['matchday']
            fixtures_list = [
                f"{match['homeTeam']['name']} - {match['awayTeam']['name']}"
                for match in data['matches'] if match['matchday'] == matchday
            ]
            logging.info(f"Partite della prossima giornata ({matchday}): {fixtures_list}")
            return f"Giornata {matchday}, stagione 2025/2026:\n" + "\n".join(fixtures_list)
            
    except httpx.HTTPStatusError as e:
        logging.error(f"Errore API Football-Data: {e.response.status_code} - {e.response.text}")
        return "Errore nel recuperare i dati delle partite dall'API."
    except Exception as e:
        logging.error(f"Errore generico in get_next_matchday_fixtures: {e}")
        return "Errore sconosciuto durante il recupero delle partite."


async def get_best_lineup(ROSTER: Dict[str, List[Tuple[str, str]]]):
    """Genera la formazione tenendo conto delle partite della prossima giornata."""
    
    # 1. Recupera le partite
    fixtures_info = await get_next_matchday_fixtures()
    if fixtures_info.startswith("Errore"):
        return fixtures_info # Restituisce direttamente il messaggio di errore

    # 2. Crea il prompt con il nuovo contesto
    prompt = f"""
        Sei un esperto di fantacalcio. Il tuo compito è scegliere la migliore formazione per la prossima giornata.

        LA MIA ROSA (Nome, Squadra):
        Portieri: {ROSTER['Por']}
        Difensori: {ROSTER['Dif']}
        Centrocampisti: {ROSTER['Cen']}
        Attaccanti: {ROSTER['Att']}

        PARTITE DELLA PROSSIMA GIORNATA:
        {fixtures_info}

        ISTRUZIONI:
        1. Scegli la migliore formazione (1 POR, 3 DIF, 4 CEN, 3 ATT).
        2. Valuta la difficoltà delle partite: favorisci i giocatori di squadre forti che giocano contro squadre deboli, specialmente se giocano in casa.
        4. Scegli un portiere che ha alte probabilità di non subire gol (clean sheet).
        4. Considera centrocampisti e attaccanti che hanno buone probabilità di segnare o fornire assist.
        5. Considera le quote dei bookmaker come indicatore di performance attesa.

        Restituisci ESCLUSIVAMENTE un oggetto JSON valido con la seguente struttura, senza alcun testo aggiuntivo:
        {{
            "Por": ["nome"],
            "Dif": ["nome1", "nome2", "nome3"],
            "Cen": ["nome1", "nome2", "nome3", "nome4"],
            "Att": ["nome1", "nome2", "nome3"]
        }}
    """

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {"role": "system", "content": "Sei un assistente che risponde solo in formato JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1 # Abbassiamo la temperatura per risposte più prevedibili
        )

        content = response.choices[0].message.content
        lineup = json.loads(content)

        formazione_text = (
            f"\n🧤 *POR*: {', '.join(lineup.get('Por', []))}\n"
            f"🛡️ *DIF*: {', '.join(lineup.get('Dif', []))}\n"
            f"👟 *CEN*: {', '.join(lineup.get('Cen', []))}\n"
            f"⚽ *ATT*: {', '.join(lineup.get('Att', []))}"
        )
        
        return formazione_text

    # Catturiamo l'errore specifico di OpenAI/Groq
    except BadRequestError as e:
        logging.error(f"Errore 400 da Groq: {e.body}")
        # Restituiamo un testo pulito, senza caratteri speciali
        return "Errore: la richiesta all'AI e' stata rifiutata. Controlla il prompt o i parametri del modello."
    
    except json.JSONDecodeError:
        logging.error(f"Errore di parsing JSON. Risposta ricevuta: {content}")
        return "Errore: l'AI non ha risposto con un JSON valido."
        
    except Exception as e:
        logging.error(f"Errore generico in get_best_lineup: {e}", exc_info=True)
        return "Errore generico durante la generazione della formazione."