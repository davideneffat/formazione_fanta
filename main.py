import os
import asyncio
from fastapi import FastAPI, Request
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

RENDER_URL = "fanta-formazione.onrender.com"
WEBHOOK_URL = f"https://{RENDER_URL}/webhook"
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
    await update.message.reply_text("Ciao! Usa /formazione per generare la tua squadra.")

async def formazione_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🤔 Sto analizzando la rosa...")
    lineup_text = await get_best_lineup(ROSTER)
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=msg.message_id,
        text=f"📋 *Formazione Consigliata:*\n{lineup_text}",
        parse_mode="Markdown"
    )

async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Recupero le quote…")
    roster_quotes = await asyncio.to_thread(run_scraper_for_roster, ROSTER)
    final_text = format_roster_quotes_for_telegram(roster_quotes)
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=msg.message_id,
        text=final_text,
        parse_mode="Markdown"
    )

telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("formazione", formazione_command))
telegram_app.add_handler(CommandHandler("quote", quote_command))

# ----- FASTAPI ENDPOINTS -----

@app.on_event("startup")
async def startup():
    logging.info("Imposto webhook su Telegram…")
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)


@app.on_event("shutdown")
async def shutdown():
    logging.info("Rimuovo webhook e chiudo bot…")
    await telegram_app.bot.delete_webhook()
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    """
    Endpoint leggero per il keep-alive. 
    Risponde immediatamente senza fare nulla.
    """
    logging.info("Health check ping ricevuto.") # Utile per vedere nei log che UptimeRobot sta funzionando
    return {"status": "I'm alive!"}


@app.get("/")
def home():
    return {"status": "online"}