import os
import asyncio
from fastapi import FastAPI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
from formazione.model import get_best_lineup
import logging

from quote.model import run_scraper_for_roster, format_roster_quotes_for_telegram

# Configura il logging di base per vedere più informazioni
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
print(f"--- TOKEN LETTO: {'Sì, è presente' if TELEGRAM_TOKEN else 'NO, MANCANTE!'} ---") # CONTROLLO 1

if not TELEGRAM_TOKEN:
    raise ValueError("Manca il TELEGRAM_TOKEN nelle variabili d'ambiente!")

ROSTER = {
    "Por": [("Audero", "Cremonese"), ("Svilar", "Roma"), ("Vasquez D.", "Roma")],
    "Dif": [
        ("Angori", "Pisa"), ("Biraghi", "Torino"), ("Dodo Cordeiro", "Fiorentina"), 
        ("Mancini", "Roma"), ("Pavlovic", "Milan"), ("Pezzella Giu.", "Cremonese"), 
        ("Zemura", "Udinese"), ("Gaspar K.", "Lecce") 
    ],
    "Cen": [
        ("Bailey", "Roma"), ("Bernabe", "Parma"), ("Dele-Bashiru", "Lazio"),
        ("Gronbaek Erlykke", "Genoa"), ("Modric", "Milan"), ("Thuram Kephren", "Juventus"), 
        ("Vazquez Franco", "Cremonese"), ("Zaccagni", "Lazio")
    ],
    "Att": [
        ("Castro S.", "Bologna"), ("De Ketelaere", "Atalanta"),
        ("Dovbyk", "Roma"), ("Hojlund Rasmus", "Napoli"), ("Nzola M.", "Pisa"), 
        ("Zapata D.", "Torino")
    ],
}

# Setup FastAPI
app = FastAPI()

# Setup Telegram Bot (variabile globale per gestirla negli eventi)
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"Comando /start ricevuto da {update.effective_user.username}")
    await update.message.reply_text("Ciao! Usa /formazione per generare la tua squadra.")

async def formazione_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"Comando /formazione ricevuto da {update.effective_user.username}")
    
    msg = await update.message.reply_text("🤔 Sto analizzando la rosa...")
    
    lineup_text = await get_best_lineup(ROSTER)
    
    # Decidiamo se usare Markdown o no
    parse_mode_to_use = "Markdown"
    final_text = f"📋 *Formazione Consigliata:*\n{lineup_text}"

    # Se la risposta è un messaggio di errore, non usare Markdown per sicurezza
    if lineup_text.lower().startswith("errore"):
        parse_mode_to_use = None # Disattiva il parsing
        final_text = f"⚠️ {lineup_text}" # Formatta come semplice errore

    try:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=final_text,
            parse_mode=parse_mode_to_use
        )
    except Exception as e:
        logging.error(f"Errore durante l'invio del messaggio a Telegram: {e}")
        # Invia un messaggio di fallback se l'edit fallisce
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Si è verificato un errore durante la formattazione della risposta."
        )


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"Comando /quote ricevuto da {update.effective_user.username}")
    
    msg = await update.message.reply_text("⏳ Sto recuperando e abbinando le quote per la tua rosa...")

    try:
        # Esegui la nuova funzione passando il ROSTER
        roster_quotes = await asyncio.to_thread(run_scraper_for_roster, ROSTER)

        if roster_quotes:
            final_text = format_roster_quotes_for_telegram(roster_quotes)
            parse_mode = "Markdown"
        else:
            final_text = "⚠️ Si è verificato un errore durante il recupero dei dati. Riprova più tardi."
            parse_mode = None

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=final_text,
            parse_mode=parse_mode
        )

    except Exception as e:
        logging.error(f"Errore generale nel comando /quote: {e}", exc_info=True)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text="❌ Ops! Qualcosa è andato storto. Impossibile completare la richiesta."
        )


# Registra i comandi
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("formazione", formazione_command))
telegram_app.add_handler(CommandHandler("quote", quote_command))

# Endpoint per Healthcheck (per Render/Heroku)
@app.get("/")
def home():
    return {"status": "Bot is running", "service": "Fantacalcio AI"}

# --- Gestione Ciclo di Vita (Startup/Shutdown) ---

@app.on_event("startup")
async def startup_event():
    """Avvia il bot Telegram quando parte FastAPI"""
    print("Avvio del bot Telegram...")
    await telegram_app.initialize()
    await telegram_app.start()
    # Inizia a ricevere aggiornamenti (Polling) in background
    await telegram_app.updater.start_polling()

@app.on_event("shutdown")
async def shutdown_event():
    """Ferma il bot Telegram quando FastAPI si spegne"""
    print("Spegnimento del bot Telegram...")
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()