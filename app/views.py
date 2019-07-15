import json
import logging

from aiohttp import web, ClientSession
from lxml import html

from config.settings import BOT_TOKEN

logger = logging.getLogger(__name__)

BASE_URL = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)
sendMessage = "{}sendMessage".format(BASE_URL)
headers = {'content-type': 'application/json'}


async def process_json(request):
	if request.method == "POST":
		body = await request.text()
		# TODO Not text message case
		if body:
			data = json.loads(body, encoding="utf-8")
			user_request = data["message"]["text"]
			if "/start" in user_request:
				await start(data=data)
			elif "Курсы валют" in user_request:
				await exchange_rates(data=data)
			elif "Курс евро 💶" in user_request:
				await euro_rates(data=data)
			else:
				await start(data=data)
		else:
			return web.Response(status=204)

		return web.Response(status=200)
	else:
		return web.Response(status=405)


async def start(data):
	keyboard = json.dumps({
		"resize_keyboard": True,
		"keyboard": [
			["Курсы акций"],
			["Курсы валют"],
		]
	})
	post_data = json.dumps({
		"chat_id": data["message"]["from"]["id"],
		"text": "Добро пожаловать в бота!",
		"reply_markup": keyboard
	})
	async with ClientSession(headers=headers) as session:
		await session.post(url=sendMessage, data=post_data)


async def exchange_rates(data):
	keyboard = json.dumps({
		"resize_keyboard": True,
		"keyboard": [
			["Курс евро 💶"],
			["Курс доллара 💵"],
		]
	})
	post_data = json.dumps({
		"chat_id": data["message"]["from"]["id"],
		"text": "Выберите интересующий курс валюты",
		"reply_markup": keyboard
	})
	async with ClientSession(headers=headers) as session:
		await session.post(url=sendMessage, data=post_data)


async def euro_rates(data):
	cbr_url = "https://www.cbr-xml-daily.ru/daily_json.js"
	tinkoff_api_eur = "https://api.tinkoff.ru/v1/currency_rates?from=EUR&to=RUB"
	# tinkoff_api_usd = "https://api.tinkoff.ru/v1/currency_rates?from=USD&to=RUB"
	# sberbank_url_usd = "https://www.sravni.ru/bank/sberbank-rossii/valjuty/usd/"
	sberbank_url_eur = "https://www.sravni.ru/bank/sberbank-rossii/valjuty/eur/"

	async with ClientSession() as session:
		async with session.get(url=cbr_url) as resp:
			cbr_answer = await resp.text()
		async with session.get(url=tinkoff_api_eur) as resp:
			tinkoff_api_answer_eur = await resp.json()
		async with session.get(url=sberbank_url_eur) as resp:
			sberbank_eur_page = await resp.text()
		# async with session.get(url=tinkoff_api_usd) as resp:
		# 	tinkoff_api_answer_usd = await resp.json()
		# async with session.get(url=sberbank_url_usd) as resp:
		# 	sberbank_usd_page = await resp.text()
		# async with session.get(url=sberbank_url_usd) as resp:
		# 	sberbank_usd_page = await resp.text()

	# cbr_rate_usd = round(json.loads(cbr_answer)["Valute"]["USD"]["Value"], 2)
	cbr_rate_euro = "{0:.2f}".format(json.loads(cbr_answer)["Valute"]["EUR"]["Value"])

	tinkoff_eur_rates = tinkoff_api_answer_eur["payload"]["rates"]
	tinkoff_eur_rate = "{0:.2f}".format(next(item["sell"] for item in tinkoff_eur_rates if item["category"] == "DebitCardsTransfers"))

	# tinkoff_usd_rates = tinkoff_api_answer_usd["payload"]["rates"]
	# tinkoff_usd_rate = next(item["sell"] for item in tinkoff_usd_rates if item["category"] == "DebitCardsTransfers")

	sberbank_eur_rate = html.fromstring(sberbank_eur_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")
	# sberbank_usd_rate = html.fromstring(sberbank_usd_page.content).xpath('//div[@class="bank-currency__info-val"]/text()')[1]

	post_data = json.dumps({
		"chat_id": data["message"]["from"]["id"],
		"text": "Курс ЦБ: <b>{cb_eur} ₽</b>\n\n"
		        "Тинькофф Банк: <b>{tinkoff_eur} ₽</b>\n"
		        "Сбербанк: <b>{sberbank_eur} ₽</b>\n\n"
		        "".format(cb_eur=cbr_rate_euro,
		                  tinkoff_eur=tinkoff_eur_rate,
		                  sberbank_eur=sberbank_eur_rate),
		"parse_mode": "HTML"
	})
	async with ClientSession(headers=headers) as session:
		await session.post(url=sendMessage, data=post_data)