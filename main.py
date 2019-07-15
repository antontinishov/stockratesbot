import logging

import asyncio
import uvloop
from aiohttp import web

from app.routes import setup_routes
from config.settings import DEBUG

logger = logging.getLogger(__name__)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()

if __name__ == '__main__':
	app = web.Application(
		debug=DEBUG,
		loop=loop
	)
	setup_routes(app)
	try:
		web.run_app(app, host="0.0.0.0", port=8080)
	except Exception as e:
		logger.exception(e)
