from aiohttp import web

from .views import *


def setup_routes(app):
	app.router.add_post("/webhook/{}/".format(BOT_TOKEN), internal_route)


async def internal_route(request):
	if request.method == "POST":
		try:
			body = await request.text()
			data = json.loads(body, encoding="utf-8")
			if "text" not in data["message"].keys():
				await incorrect_request(data=data)
				return web.Response(status=200)
			if body:
				user_request = data["message"]["text"]
				if "/start" in user_request:
					await start(data=data, request=request)
				elif "Курс евро 💶" in user_request:
					await euro_rates(data=data, request=request)
				elif "Курс доллара 💵" in user_request:
					await dollar_rates(data=data, request=request)
				else:
					await incorrect_request(data=data)
			else:
				return web.Response(status=204)
		except Exception as e:
			logger.exception(e)

		return web.Response(status=200)
	else:
		return web.Response(status=405)
