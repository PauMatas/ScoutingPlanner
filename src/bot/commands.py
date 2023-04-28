import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from os.path import join, dirname, abspath
import sys

ROOT_DIR = join(dirname(abspath(__file__)), '../..')
sys.path.append(ROOT_DIR)

from .parsers import *
from src.interfaces.database import MongoDBDatabaseProxy
from src.graphs import MatchdayGraph

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

DB_PROXY = MongoDBDatabaseProxy()
SEASON = 'TEMPORADA 2022-2023'

def send_markdown_message(func: callable):
    """ Sends a message containing the return of func.
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=func(update, context),
                parse_mode=ParseMode.MARKDOWN)
        except NotImplementedError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="""🚧 Aquesta funció encara no està implementada. 🚧""",
                parse_mode=ParseMode.MARKDOWN)
    return wrapper


@send_markdown_message
def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        message = str(' '.join(context.args))
        try:
            context.user_data['date'] = parse_date(message)
            print(f'Parsed date: {context.user_data["date"]}, type: {type(context.user_data["date"])}')
            return f"""Quina informació futbolística vols saber del dia {context.user_data['date'].date()}? 📅"""
        except ParseError:
            return """❌ Format de data incorrecte. Si us plau, introdueix la data en el format DD-MM-AAAA.
            
Exemple: /start 07-12-2001"""

    else:
        user = update.effective_chat.first_name
        return f"""👋 Hola {user}!

Sóc **ScoutingPlanner**, el bot de rutes d'scouting de futbol de Catalunya. 🤖👨‍💻
Estic aquí per ajudar-te a trobar les millors rutes per als partits de futbol que es celebren a la regió! 📍⚽

Per començar, només has de dir-me quin dia tens pensat fer scouting. 📅

Si no saps com fer-ho, pots escriure /help i t'ajudo."""

@send_markdown_message
def competitions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'User data: {context.user_data["date"]}, type: {type(context.user_data["date"])}')
    try:
        competitions = DB_PROXY.get_competitions(season=SEASON, timestamp=context.user_data['date'])
    except:
        competitions = DB_PROXY.get_competitions(season=SEASON)
    print(competitions)
    competitions = [f'- **{competition}**' for competition in competitions]
    print(competitions)
    competitions = '\n'.join(competitions)
    print(competitions)
    return f"""🏆 Aquestes són les competicions disponibles per a la {SEASON}:

{competitions}"""


@send_markdown_message
def matchday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = DB_PROXY.get_matches(season=SEASON, timestamp=context.user_data['date'], sort={'competition': 1})

@send_markdown_message
def route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raise NotImplementedError

@send_markdown_message
def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return """
🤖🆘 Aquí tens les comandes que accepto:
/start - Inicia la conversa amb el bot 👋
/start <dd-mm-aaaa> - Escull quin dia vols fer scouting 📅
/help - Mostra aquesta llista de comandes 🆘
/competitions - Mostra les competicions disponibles 🏆
/matchday - Mostra els partits d'un dia concret ⚽🆚
/route - Ajuda a trobar la millor ruta per arribar al partit 📍🗺
/feedback - Per enviar comentaris o suggeriments al meu equip de desenvolupament 👨‍💻
"""
