#!/usr/bin/python3.6

import json
import logging
import time
from datetime import datetime

import aioredis
import asyncio
import uvloop
from aiohttp import ClientSession
from lxml import html

from config.settings import DATABASES

logger = logging.getLogger(__name__)


async def save_euro_rates():
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

	cbr_rate_euro = round(json.loads(cbr_answer)["Valute"]["EUR"]["Value"], 2)

	tinkoff_euro_rates = tinkoff_api_answer_eur["payload"]["rates"]
	tinkoff_euro_rate = "{:.2f}".format(next(item["sell"] for item in tinkoff_euro_rates if item["category"] == "DebitCardsTransfers"))

	sberbank_euro_rate = html.fromstring(sberbank_euro_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

	vtb_euro_rates = vtb_eur_answer["GroupedRates"][1]
	vtb_euro_rate = "{:.2f}".format(next(item["BankSellAt"] for item in vtb_euro_rates["MoneyRates"]))

	spbbank_euro_rate = html.fromstring(spb_bank_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

	data_rates = {
		"date": datetime.now().strftime("%d.%m.%Y %H:%M"),
		"cbr": cbr_rate_euro,
		"tinkoff": tinkoff_euro_rate,
		"sberbank": sberbank_euro_rate,
		"vtb": vtb_euro_rate,
		"spbbank": spbbank_euro_rate
	}
	await save_to_redis_background(redis_key="euro_rates", data_rates=data_rates)


async def save_dollar_rates():
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

	cbr_rate_dollar = round(json.loads(cbr_answer)["Valute"]["USD"]["Value"], 2)

	tinkoff_dollar_rates = tinkoff_api_answer_dollar["payload"]["rates"]
	tinkoff_dollar_rate = "{0:.2f}".format(next(item["sell"] for item in tinkoff_dollar_rates if item["category"] == "DebitCardsTransfers"))

	sberbank_dollar_rate = html.fromstring(sberbank_dollar_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

	vtb_dollar_rates = vtb_dollar_answer["GroupedRates"][0]
	vtb_dollar_rate = "{0:.2f}".format(next(item["BankSellAt"] for item in vtb_dollar_rates["MoneyRates"]))

	spbbank_dollar_rate = html.fromstring(spb_bank_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

	data_rates = {
		"date": datetime.now().strftime("%d.%m.%Y %H:%M"),
		"cbr": cbr_rate_dollar,
		"tinkoff": tinkoff_dollar_rate,
		"sberbank": sberbank_dollar_rate,
		"vtb": vtb_dollar_rate,
		"spbbank": spbbank_dollar_rate
	}

	await save_to_redis_background(redis_key="dollar_rates", data_rates=data_rates)


if __name__ == '__main__':
	try:
		start = time.time()
		asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
		app_loop = asyncio.get_event_loop()
		app_loop.run_until_complete(save_euro_rates())
		app_loop.run_until_complete(save_dollar_rates())
		print(time.time() - start)
	except Exception as e:
		logger.exception(e)


async def save_to_redis_background(redis_key, data_rates):
	redis_conn = await aioredis.create_redis(
		"redis://{HOST}:{PORT}/0".format(**DATABASES["redis"]),

	)
	await redis_conn.hmset_dict(redis_key, data_rates)
	await redis_conn.expire(redis_key, 60)
	return 0
