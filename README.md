# Bot Telegram per Consigliare la Formazione al Fantacalcio

Questo progetto è un **bot Telegram** che utilizza un modello di linguaggio AI per generare una **formazione di fantacalcio consigliata**. Il bot analizza una rosa predefinita e le partite della prossima giornata di Serie A per suggerire la squadra migliore da schierare.

## Funzionalità

- **Analisi Contestuale:** La formazione viene scelta considerando la difficoltà delle partite della giornata imminente.
- **Dati Aggiornati:** Il calendario della Serie A viene recuperato in tempo reale tramite un'API esterna.
- **Integrazione AI:** Un modello linguistico (tramite API Groq) elabora i dati per formulare i suggerimenti.
- **Interfaccia Semplice:** L'interazione avviene tramite un semplice comando su Telegram.

## Architettura

- **Backend:** FastAPI
- **Bot Framework:** python-telegram-bot
- **Servizi Esterni:**
  - Groq API (per l'accesso al modello AI)
  - Football-Data.org API (per i dati sulle partite)
- **Linguaggio:** Python

## Guida all'Installazione

### 1. Prerequisiti

- Python 3.10+
- Token per un bot Telegram
- Chiave API da Groq
- Chiave API da Football-Data.org

### 2. Installazione

Clona il repository:
```bash
git clone https://github.com/davideneffat/formazione_fanta
cd formazione_fanta
```

Crea un ambiente virtuale:
```bash
python -m venv venv
source venv/bin/activate  # Su macOS/Linux
# venv\Scripts\activate    # Su Windows
```

Installa le dipendenze:
```bash
pip install fastapi uvicorn python-telegram-bot openai python-dotenv httpx
```

### 3. Configurazione

Crea un file `.env` nella directory principale e aggiungi le tue credenziali:
```env
TELEGRAM_TOKEN="IL_TUO_TOKEN_TELEGRAM"
GROQ_API_KEY="LA_TUA_CHIAVE_API_GROQ"
FOOTBALL_DATA_API_KEY="LA_TUA_CHIAVE_API_CALCIO"
```

### 4. Personalizzazione

Modifica il dizionario `ROSTER` nel file `model.py` per inserire i giocatori della tua rosa:
```python
# In model.py
ROSTER = {
    "Por": [("NomePortiere", "Squadra")],
    # ...
}
```

### 5. Avvio

Lancia l'applicazione con Uvicorn:
```bash
uvicorn main:app --reload
```
Il bot sarà ora attivo e risponderà ai comandi su Telegram.

## Comandi del Bot

- `/start`: Invia un messaggio di benvenuto.
- `/formazione`: Genera e invia la formazione consigliata.
