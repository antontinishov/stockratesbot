import logging

import aioredis
import asyncio
import asyncpg
import uvloop
from aiohttp import web

from app.routes import setup_routes
from config.settings import DEBUG, DATABASES, SENTRY_DSN

logger = logging.getLogger(__name__)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()


async def redis_connection_pool(app):
	app["redis"] = await aioredis.create_redis_pool(
		'redis://{HOST}:{PORT}/0'.format(**DATABASES["redis"]),
		minsize=5,
		maxsize=50,
		timeout=1,
		loop=loop
	)


async def postgres_connection_pool(app):
	app["postgres"] = await asyncpg.create_pool(
		dsn="postgres://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}".format(**DATABASES["postgres"]),
		min_size=5,
		max_size=100,
		max_inactive_connection_lifetime=10
	)


async def shutdown_postgres(app):
	app["postgres"].terminate()


def init_application(app_loop):
	app = web.Application(
		debug=DEBUG,
		loop=app_loop
	)
	setup_routes(app)
	return app


if __name__ == '__main__':
	try:
		if not DEBUG:
			import sentry_sdk
			sentry_sdk.init(SENTRY_DSN)

		web_app = init_application(app_loop=loop)
		web_app.on_startup.append(redis_connection_pool)
		web_app.on_startup.append(postgres_connection_pool)
		web_app.on_shutdown.append(shutdown_postgres)
		web.run_app(web_app, host="0.0.0.0", port=8080)
	except Exception as e:
		logger.exception(e)
