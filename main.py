# Bot Telegram con comando /formazione

from fastapi import FastAPI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
from model import get_best_lineup

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("8565914661:AAGjtdPvIRbQxrsqlqCrb9F2lxSifafFZvk")

# Entrypoint Telegram
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def formazione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lineup = get_best_lineup()
    await update.message.reply_text(f"📋 *Formazione consigliata:*{lineup}", parse_mode="Markdown")

telegram_app.add_handler(CommandHandler("formazione", formazione))

# Endpoint per Render/Heroku healthcheck
@app.get("/")
def home():
    return {"status": "ok"}


# Avvia il bot quando parte il server
@app.on_event("startup")
async def startup_event():
    await telegram_app.initialize()
    await telegram_app.start()


@app.on_event("shutdown")
async def shutdown_event():
    await telegram_app.stop()