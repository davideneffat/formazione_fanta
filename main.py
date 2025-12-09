import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
from formazione.model import get_best_lineup
import logging

from quote.model import run_scraper_for_roster, format_roster_quotes_for_telegram

# Configurazione del logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
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


def main():
    """Avvia il bot in modalità polling."""
    logging.info("Avvio del bot in modalità polling...")
    
    # Costruisce l'applicazione
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Aggiunge i gestori dei comandi
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("formazione", formazione_command))
    application.add_handler(CommandHandler("quote", quote_command))

    # Avvia il bot finché non viene interrotto (es. con Ctrl-C)
    application.run_polling()
    
    logging.info("Il bot è stato fermato.")

if __name__ == '__main__':
    main()