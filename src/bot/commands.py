import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from interfaces.database import MongoDBDatabaseProxy
from matchday import Matchday

from .parsers import *

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
            message = func(update, context)
            for m in message:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=m,
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
            yield f"""Espera mentres busco els partits de futbol del dia {context.user_data['date'].date()}... ⏳"""
            context.user_data['matchday'] = Matchday(date=context.user_data['date'])
            if not context.user_data['matchday'].matches:
                yield f"""❌ No he trobat cap partit de futbol per al dia {context.user_data['date'].date()}."""
            else:
                yield f"""🔎 Ja tinc tota la informació que necessito, que vols saber?"""
        except ParseError:
            yield """❌ Format de data incorrecte. Si us plau, introdueix la data en el format DD-MM-AAAA.
            
Exemple: /start 07-12-2001"""

    else:
        user = update.effective_chat.first_name
        yield f"""👋 Hola {user}!

Sóc **ScoutingPlanner**, el bot de rutes d'scouting de futbol de Catalunya. 🤖👨‍💻
Estic aquí per ajudar-te a trobar les millors rutes per als partits de futbol que es celebren a la regió! 📍⚽

Per començar, només has de dir-me quin dia tens pensat fer scouting. 📅

Si no saps com fer-ho, pots escriure /help i t'ajudo."""

@send_markdown_message
def competitions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    competitions_msg = f"""🏆 *Competicions* disponibles per al dia {context.user_data['date'].date()}:"""
    competitions_msg += "\n\n"
    for competition, v in context.user_data['matchday'].competitions.items():
        n_matches = v['matches']
        matchdays = list(v['matchday'])

        competitions_msg += f""" - {n_matches} partit{'' if n_matches == 1 else 's'} de _{competition}_ corresponent{'' if n_matches == 1 else 's'} a l{'a' if len(matchdays) == 1 else 'es'} jornada{'' if len(matchdays) == 1 else 's'} {', '.join(matchdays)}"""
        competitions_msg += "\n"
    
    yield competitions_msg

@send_markdown_message
def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    competitions = DB_PROXY.get_competitions(season=SEASON)
    for competition in competitions:
        matches = DB_PROXY.get_matches(season=SEASON, competition=competition, timestamp=context.user_data['date'])
        if matches:
            message = f"""🏆 **{competition}**"""
            message += "\n\n"
            for match in matches:
                if not match.finished:
                    day = str(match.timestamp.day)
                    month = str(match.timestamp.month)
                    hour = str(match.timestamp.hour) if match.timestamp.hour >= 10 else f"0{match.timestamp.hour}"
                    minute = str(match.timestamp.minute) if match.timestamp.minute >= 10 else f"0{match.timestamp.minute}"
                    match_markdown = f"""*[{day}/{month} {hour}:{minute}]* {match.home_team} - {match.away_team}"""
                else:
                    home_goals = match.home_goals
                    away_goals = match.away_goals
                    match_markdown = f"""{match.home_team} *{home_goals} - {away_goals}* {match.away_team}"""
                message += match_markdown + "\n"
            yield message
        else:
            print(f"No matches for {competition}")

@send_markdown_message
def routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routes = context.user_data['matchday'].routes()
    for i, route in enumerate(routes):
        route_markdown = f"""📍🗺 _Ruta {i+1}:_"""
        route_markdown += "\n\n"
        for match in route:
            match.home_team = match.home_team
            match.away_team = match.away_team
            hour = str(match.timestamp.hour) if match.timestamp.hour >= 10 else f"0{match.timestamp.hour}"
            minute = str(match.timestamp.minute) if match.timestamp.minute >= 10 else f"0{match.timestamp.minute}"
            match_markdown = f"""*[{hour}:{minute}]* {match.home_team} - {match.away_team}"""
            route_markdown += match_markdown + "\n"
        yield route_markdown

@send_markdown_message
def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    yield """
🤖🆘 Aquí tens les comandes que accepto:
/start - Inicia la conversa amb el bot 👋
/start <dd-mm-aaaa> - Escull quin dia vols fer scouting 📅
/help - Mostra aquesta llista de comandes 🆘
/competitions - Mostra les competicions disponibles 🏆
/matches - Mostra els partits d'un dia concret ⚽🆚
/routes - Ajuda a trobar la millor ruta per arribar al partit 📍🗺
/feedback - Per enviar comentaris o suggeriments al meu equip de desenvolupament 👨‍💻
"""
