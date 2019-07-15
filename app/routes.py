from config.settings import BOT_TOKEN
from .views import process_json


def setup_routes(app):
	app.router.add_post("/webhook/{}/".format(BOT_TOKEN), process_json)
