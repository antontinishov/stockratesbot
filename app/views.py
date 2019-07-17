import json
import logging
from datetime import datetime

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
				await euro_rates(data=data, request=request)
			elif "Курс доллара 💵" in user_request:
				await dollar_rates(data=data, request=request)
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


async def euro_rates(data, request):
	redis_data = await check_redis_key(redis_key="euro_rates", request=request)
	if redis_data:
		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": "Курс валюты на {date}\n"
					"ЦБ: <b>{cb_dollar} ₽</b>\n\n"
			        "Тинькофф Банк: <b>{tinkoff_dollar} ₽</b>\n"
			        "Сбербанк: <b>{sberbank_dollar} ₽</b>\n"
			        "Банк ВТБ: <b>{vtb_dollar} ₽</b>\n"
			        "Банк Санкт-Петербург: <b>{spbbank_dollar} ₽</b>\n\n"
			        "Все банки: {all_banks}"
			        "".format(date=datetime.now().strftime("%d.%m.%Y %H:%M"),
							  cb_dollar=redis_data["cbr"],
			                  tinkoff_dollar=redis_data["tinkoff"],
			                  sberbank_dollar=redis_data["sberbank"],
			                  vtb_dollar=redis_data["vtb"],
			                  spbbank_dollar=redis_data["spbbank"],
			                  all_banks="https://www.banki.ru/products/currency/cash/usd/sankt-peterburg/#sort=sale&order=asc"),
			"parse_mode": "HTML"
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)
	else:
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
				sberbank_euro_page = await resp.text()
			async with session.get(url=vtb_url_eur) as resp:
				vtb_eur_answer = await resp.json()
			async with session.get(url=spbbank_eur) as resp:
				spb_bank_page = await resp.text()

		cbr_rate_euro = json.loads(cbr_answer)["Valute"]["EUR"]["Value"]

		tinkoff_euro_rates = tinkoff_api_answer_eur["payload"]["rates"]
		tinkoff_euro_rate = "{:.2f}".format(next(item["sell"] for item in tinkoff_euro_rates if item["category"] == "DebitCardsTransfers"))

		sberbank_euro_rate = html.fromstring(sberbank_euro_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

		vtb_euro_rates = vtb_eur_answer["GroupedRates"][1]
		vtb_euro_rate = "{:.2f}".format(next(item["BankSellAt"] for item in vtb_euro_rates["MoneyRates"]))

		spbbank_euro_rate = html.fromstring(spb_bank_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": "ЦБ: <b>{cb_eur} ₽</b>\n\n"
			        "Тинькофф Банк: <b>{tinkoff_eur} ₽</b>\n"
			        "Сбербанк: <b>{sberbank_eur} ₽</b>\n"
			        "Банк ВТБ: <b>{vtb_eur} ₽</b>\n"
			        "Банк Санкт-Петербург: <b>{spbbank_eur} ₽</b>\n\n"
			        "Все банки: {all_banks}"
			        "".format(cb_eur=cbr_rate_euro,
			                  tinkoff_eur=tinkoff_euro_rate,
			                  sberbank_eur=sberbank_euro_rate,
			                  vtb_eur=vtb_euro_rate,
			                  spbbank_eur=spbbank_euro_rate,
			                  all_banks="https://www.banki.ru/products/currency/cash/eur/sankt-peterburg/#sort=sale&order=asc"),
			"parse_mode": "HTML"
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)

		data_rates = {
			"cbr": cbr_rate_euro,
			"tinkoff": tinkoff_euro_rate,
			"sberbank": sberbank_euro_rate,
			"vtb": vtb_euro_rate,
			"spbbank": spbbank_euro_rate
		}
		await save_to_redis(redis_key="euro_rates", data_rates=data_rates, request=request)


async def dollar_rates(data, request):
	redis_data = await check_redis_key(redis_key="dollar_rates", request=request)
	if redis_data:
		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": "Курс валюты на {date}\n"
					"ЦБ: <b>{cb_dollar} ₽</b>\n\n"
			        "Тинькофф Банк: <b>{tinkoff_dollar} ₽</b>\n"
			        "Сбербанк: <b>{sberbank_dollar} ₽</b>\n"
			        "Банк ВТБ: <b>{vtb_dollar} ₽</b>\n"
			        "Банк Санкт-Петербург: <b>{spbbank_dollar} ₽</b>\n\n"
			        "Все банки: {all_banks}"
			        "".format(date=datetime.now().strftime("%d.%m.%Y %H:%M"),
							  cb_dollar=redis_data["cbr"],
			                  tinkoff_dollar=redis_data["tinkoff"],
			                  sberbank_dollar=redis_data["sberbank"],
			                  vtb_dollar=redis_data["vtb"],
			                  spbbank_dollar=redis_data["spbbank"],
			                  all_banks="https://www.banki.ru/products/currency/cash/usd/sankt-peterburg/#sort=sale&order=asc"),
			"parse_mode": "HTML"
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)
	else:
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
			"text": "Курс валюты на {date}\n"
				    "ЦБ: <b>{cb_dollar} ₽</b>\n\n"
			        "Тинькофф Банк: <b>{tinkoff_dollar} ₽</b>\n"
			        "Сбербанк: <b>{sberbank_dollar} ₽</b>\n"
			        "Банк ВТБ: <b>{vtb_dollar} ₽</b>\n"
			        "Банк Санкт-Петербург: <b>{spbbank_dollar} ₽</b>\n\n"
			        "Все банки: {all_banks}"
			        "".format(date=datetime.now().strftime("%d.%m.%Y %H:%M"),
				              cb_dollar=cbr_rate_dollar,
			                  tinkoff_dollar=tinkoff_dollar_rate,
			                  sberbank_dollar=sberbank_dollar_rate,
			                  vtb_dollar=vtb_dollar_rate,
			                  spbbank_dollar=spbbank_dollar_rate,
			                  all_banks="https://www.banki.ru/products/currency/cash/usd/sankt-peterburg/#sort=sale&order=asc"),
			"parse_mode": "HTML"
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)

		data_rates = {
			"cbr": cbr_rate_dollar,
			"tinkoff": tinkoff_dollar_rate,
			"sberbank": sberbank_dollar_rate,
			"vtb": vtb_dollar_rate,
			"spbbank": spbbank_dollar_rate
		}

		await save_to_redis(redis_key="dollar_rates", data_rates=data_rates, request=request)


async def check_redis_key(redis_key, request):
	redis_conn = request.app["redis"]
	with await redis_conn as redis_con:
		if await redis_con.exists(redis_key) == 1:
			return await redis_con.hgetall(redis_key, encoding="utf-8")
		else:
			return 0


async def save_to_redis(redis_key, data_rates, request):
	redis_conn = request.app["redis"]
	with await redis_conn as redis_con:
		await redis_con.hmset_dict(redis_key, data_rates)
		await redis_con.expire(redis_key, 60)
	return 0
