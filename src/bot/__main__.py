import logging
from telegram.ext import ApplicationBuilder, CommandHandler

import json
from os.path import join, dirname, abspath
import sys

ROOT_DIR = join(dirname(abspath(__file__)), '../..')
sys.path.append(ROOT_DIR)

from src.bot.commands import start, competitions, matchday, route, help



with open(join(ROOT_DIR, 'etc/config.json'), 'r') as f:
    config = json.load(f)
TOKEN = config['telegram']['token']

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO

application = ApplicationBuilder().token(TOKEN).build()

application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('help', help))
application.add_handler(CommandHandler('competitions', competitions))
application.add_handler(CommandHandler('matchday', matchday))
application.add_handler(CommandHandler('route', route))

application.run_polling()
