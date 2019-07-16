import json
import logging

from aiohttp import web, ClientSession
from lxml import html

from config.settings import BOT_TOKEN

logger = logging.getLogger(__name__)

base_url = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)
send_message = "{}sendMessage".format(base_url)
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
			elif "Курс доллара 💵" in user_request:
				await dollar_rates(data=data)
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
		await session.post(url=send_message, data=post_data)


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
		await session.post(url=send_message, data=post_data)


async def euro_rates(data):
	cbr_url = "https://www.cbr-xml-daily.ru/daily_json.js"
	tinkoff_api_eur = "https://api.tinkoff.ru/v1/currency_rates?from=EUR&to=RUB"
	sberbank_url_eur = "https://www.sravni.ru/bank/sberbank-rossii/valjuty/eur/"
	vtb_url_eur = "https://www.vtb.ru/api/currency-exchange/table-info?contextItemId=%7BC5471052-2291-4AFD-9C2D-1DBC40A4769D%7D&conversionPlace=1&conversionType=1&renderingId=ede2e4d0-eb6b-4730-857b-06fd4975c06b&renderingParams=LegalStatus__%7BF2A32685-E909-44E8-A954-1E206D92FFF8%7D;IsFromRuble__1;CardMaxPeriodDays__5;CardRecordsOnPage__5;ConditionsUrl__%2Fpersonal%2Fplatezhi-i-perevody%2Fobmen-valjuty%2Fspezkassy%2F"
	spbbank_eur = "https://www.sravni.ru/bank/bank-sankt-peterburg/valjuty/eur/"

	async with ClientSession() as session:
		async with session.get(url=cbr_url) as resp:
			cbr_answer = await resp.text()
		async with session.get(url=tinkoff_api_eur) as resp:
			tinkoff_api_answer_eur = await resp.json()
		async with session.get(url=sberbank_url_eur) as resp:
			sberbank_eur_page = await resp.text()
		async with session.get(url=vtb_url_eur) as resp:
			vtb_eur_answer = await resp.json()
		async with session.get(url=spbbank_eur) as resp:
			spb_bank_page = await resp.text()

	cbr_rate_euro = json.loads(cbr_answer)["Valute"]["EUR"]["Value"]

	tinkoff_eur_rates = tinkoff_api_answer_eur["payload"]["rates"]
	tinkoff_eur_rate = "{0:.2f}".format(next(item["sell"] for item in tinkoff_eur_rates if item["category"] == "DebitCardsTransfers"))

	sberbank_eur_rate = html.fromstring(sberbank_eur_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

	vtb_eur_rates = vtb_eur_answer["GroupedRates"][1]
	vtb_eur_rate = "{0:.2f}".format(next(item["BankSellAt"] for item in vtb_eur_rates["MoneyRates"]))

	spbbank_eur_rate = html.fromstring(spb_bank_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

	post_data = json.dumps({
		"chat_id": data["message"]["from"]["id"],
		"text": "ЦБ: <b>{cb_eur} ₽</b>\n\n"
		        "Тинькофф Банк: <b>{tinkoff_eur} ₽</b>\n"
		        "Сбербанк: <b>{sberbank_eur} ₽</b>\n"
		        "Банк ВТБ: <b>{vtb_eur} ₽</b>\n"
		        "Банк Санкт-Петербург: <b>{spbbank_eur} ₽</b>\n\n"
		        "Все банки: {all_banks}"
		        "".format(cb_eur=cbr_rate_euro,
		                  tinkoff_eur=tinkoff_eur_rate,
		                  sberbank_eur=sberbank_eur_rate,
		                  vtb_eur=vtb_eur_rate,
		                  spbbank_eur=spbbank_eur_rate,
		                  all_banks="https://www.banki.ru/products/currency/cash/eur/sankt-peterburg/#sort=sale&order=asc"),
		"parse_mode": "HTML"
	})
	async with ClientSession(headers=headers) as session:
		await session.post(url=send_message, data=post_data)


async def dollar_rates(data):
	cbr_url = "https://www.cbr-xml-daily.ru/daily_json.js"
	tinkoff_api_dollar = "https://api.tinkoff.ru/v1/currency_rates?from=USD&to=RUB"
	sberbank_url_dollar = "https://www.sravni.ru/bank/sberbank-rossii/valjuty/usd/"
	vtb_url_dollar = "https://www.vtb.ru/api/currency-exchange/table-info?contextItemId=%7BC5471052-2291-4AFD-9C2D-1DBC40A4769D%7D&conversionPlace=1&conversionType=1&renderingId=ede2e4d0-eb6b-4730-857b-06fd4975c06b&renderingParams=LegalStatus__%7BF2A32685-E909-44E8-A954-1E206D92FFF8%7D;IsFromRuble__1;CardMaxPeriodDays__5;CardRecordsOnPage__5;ConditionsUrl__%2Fpersonal%2Fplatezhi-i-perevody%2Fobmen-valjuty%2Fspezkassy%2F"
	spbbank_dollar = "https://www.sravni.ru/bank/bank-sankt-peterburg/valjuty/usd/"

	async with ClientSession() as session:
		async with session.get(url=cbr_url) as resp:
			cbr_answer = await resp.text()
		async with session.get(url=tinkoff_api_dollar) as resp:
			tinkoff_api_answer_dollar = await resp.json()
		async with session.get(url=sberbank_url_dollar) as resp:
			sberbank_dollar_page = await resp.text()
		async with session.get(url=vtb_url_dollar) as resp:
			vtb_dollar_answer = await resp.json()
		async with session.get(url=spbbank_dollar) as resp:
			spb_bank_page = await resp.text()

	cbr_rate_dollar = json.loads(cbr_answer)["Valute"]["USD"]["Value"]

	tinkoff_dollar_rates = tinkoff_api_answer_dollar["payload"]["rates"]
	tinkoff_dollar_rate = "{0:.2f}".format(next(item["sell"] for item in tinkoff_dollar_rates if item["category"] == "DebitCardsTransfers"))

	sberbank_dollar_rate = html.fromstring(sberbank_dollar_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

	vtb_dollar_rates = vtb_dollar_answer["GroupedRates"][0]
	vtb_dollar_rate = "{0:.2f}".format(next(item["BankSellAt"] for item in vtb_dollar_rates["MoneyRates"]))

	spbbank_dollar_rate = html.fromstring(spb_bank_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

	post_data = json.dumps({
		"chat_id": data["message"]["from"]["id"],
		"text": "ЦБ: <b>{cb_dollar} ₽</b>\n\n"
		        "Тинькофф Банк: <b>{tinkoff_dollar} ₽</b>\n"
		        "Сбербанк: <b>{sberbank_dollar} ₽</b>\n"
		        "Банк ВТБ: <b>{vtb_dollar} ₽</b>\n"
		        "Банк Санкт-Петербург: <b>{spbbank_dollar} ₽</b>\n\n"
		        "Все банки: {all_banks}"
		        "".format(cb_dollar=cbr_rate_dollar,
		                  tinkoff_dollar=tinkoff_dollar_rate,
		                  sberbank_dollar=sberbank_dollar_rate,
		                  vtb_dollar=vtb_dollar_rate,
		                  spbbank_dollar=spbbank_dollar_rate,
		                  all_banks="https://www.banki.ru/products/currency/cash/usd/sankt-peterburg/#sort=sale&order=asc"),
		"parse_mode": "HTML"
	})
	async with ClientSession(headers=headers) as session:
		await session.post(url=send_message, data=post_data)
