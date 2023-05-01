import logging
from telegram.ext import ApplicationBuilder, CommandHandler
from os.path import join, dirname, abspath
import json

from bot.commands import start, competitions, matches, routes, help


ROOT_DIR = join(dirname(abspath(__file__)), '../..')

with open(join(ROOT_DIR, 'etc/config.json'), 'r') as f:
    config = json.load(f)
TOKEN = config['telegram']['token']

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

application = ApplicationBuilder().token(TOKEN).build()

application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('help', help))
application.add_handler(CommandHandler('competitions', competitions))
application.add_handler(CommandHandler('matches', matches))
application.add_handler(CommandHandler('routes', routes))

application.run_polling()
