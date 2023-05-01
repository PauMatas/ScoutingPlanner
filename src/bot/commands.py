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
            if isinstance(message, list):
                for m in message:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=m,
                        parse_mode=ParseMode.MARKDOWN)
            elif isinstance(message, str):
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
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
    try:
        competitions = DB_PROXY.get_competitions(season=SEASON, timestamp=context.user_data['date'])
    except:
        competitions = DB_PROXY.get_competitions(season=SEASON)
    competitions = [f'- **{competition}**' for competition in competitions]
    competitions = '\n'.join(competitions)
    return f"""🏆 Aquestes són les competicions disponibles per a la {SEASON}:

{competitions}"""


@send_markdown_message
def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    competitions = DB_PROXY.get_competitions(season=SEASON)
    messages = []
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
            messages.append(message)
        else:
            print(f"No matches for {competition}")
    
    return messages



@send_markdown_message
def routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matchday_graph = Matchday(context.user_data['date'])
    routes = matchday_graph.routes()
    routes_markdown_list = []
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
        routes_markdown_list.append(route_markdown)

    return routes_markdown_list

@send_markdown_message
def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return """
🤖🆘 Aquí tens les comandes que accepto:
/start - Inicia la conversa amb el bot 👋
/start <dd-mm-aaaa> - Escull quin dia vols fer scouting 📅
/help - Mostra aquesta llista de comandes 🆘
/competitions - Mostra les competicions disponibles 🏆
/matches - Mostra els partits d'un dia concret ⚽🆚
/routes - Ajuda a trobar la millor ruta per arribar al partit 📍🗺
/feedback - Per enviar comentaris o suggeriments al meu equip de desenvolupament 👨‍💻
"""
