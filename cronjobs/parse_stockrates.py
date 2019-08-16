#!/usr/bin/python3.6

import json
import logging
import os
import time
from datetime import datetime

import aioredis
import asyncio
import asyncpg
import sentry_sdk
import uvloop
from aiohttp import ClientSession
from lxml import html
from sentry_sdk import capture_exception

sentry_sdk.init(os.environ["SENTRY_DSN"])

logger = logging.getLogger(__name__)

DEBUG = os.environ["DEBUG"]
DEBUG = DEBUG.lower() == "true"

DATABASES = {
	"redis": {
		"HOST": os.environ["REDIS_HOST"],
		"PORT": 6379
	},
	"postgres": {
		"HOST": os.environ["DB_HOST"],
		"PORT": os.environ["DB_PORT"],
		"NAME": os.environ["DB_NAME"],
		"USER": os.environ["DB_USER"],
		"PASSWORD": os.environ["DB_PASSWORD"]
	}
}


exchange_rates_dict = {
	"cbr_url": "https://www.cbr-xml-daily.ru/daily_json.js",
	"euro_rates": {
		"tinkoff_api": "https://api.tinkoff.ru/v1/currency_rates?from=EUR&to=RUB",
		"sberbank_url": "https://www.sravni.ru/bank/sberbank-rossii/valjuty/eur/",
		"vtb_url": "https://www.vtb.ru/api/currency-exchange/table-info?contextItemId=%7BC5471052-2291-4AFD-9C2D-1DBC40A4769D%7D&conversionPlace=1&conversionType=1&renderingId=ede2e4d0-eb6b-4730-857b-06fd4975c06b&renderingParams=LegalStatus__%7BF2A32685-E909-44E8-A954-1E206D92FFF8%7D;IsFromRuble__1;CardMaxPeriodDays__5;CardRecordsOnPage__5;ConditionsUrl__%2Fpersonal%2Fplatezhi-i-perevody%2Fobmen-valjuty%2Fspezkassy%2F",
		"spbbank_url": "https://www.sravni.ru/bank/bank-sankt-peterburg/valjuty/eur/",
		},
	"usd_rates": {
		"tinkoff_api": "https://api.tinkoff.ru/v1/currency_rates?from=USD&to=RUB",
		"sberbank_url": "https://www.sravni.ru/bank/sberbank-rossii/valjuty/usd/",
		"vtb_url": "https://www.vtb.ru/api/currency-exchange/table-info?contextItemId=%7BC5471052-2291-4AFD-9C2D-1DBC40A4769D%7D&conversionPlace=1&conversionType=1&renderingId=ede2e4d0-eb6b-4730-857b-06fd4975c06b&renderingParams=LegalStatus__%7BF2A32685-E909-44E8-A954-1E206D92FFF8%7D;IsFromRuble__1;CardMaxPeriodDays__5;CardRecordsOnPage__5;ConditionsUrl__%2Fpersonal%2Fplatezhi-i-perevody%2Fobmen-valjuty%2Fspezkassy%2F",
		"spbbank_url": "https://www.sravni.ru/bank/bank-sankt-peterburg/valjuty/usd/",
	},
}


now_time = datetime.now()
now = now_time.strftime("%d.%m.%Y %H:%M")


async def save_to_redis(redis_key, data_rates):
	try:
		redis_conn = await aioredis.create_redis(
			"redis://{HOST}:{PORT}/0".format(**DATABASES["redis"]),

		)
		await redis_conn.hmset_dict(redis_key, data_rates)
		await redis_conn.expire(redis_key, 60)
	except Exception as exc:
		capture_exception(exc)
	return 0


async def save_to_postgres(data_rates, rate):
	try:
		# to_rub = json.loads(data_rates["{}_to_rub".format(rate)])
		rub_to = json.loads(data_rates["rub_to_{}".format(rate)])
		db_conn = await asyncpg.connect(
			dsn="postgres://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}".format(**DATABASES["postgres"]),
		)
		async with db_conn.transaction():
			await db_conn.execute("INSERT INTO rates (rate, cbr, tinkoff, sberbank, vtb, spbbank)"
			            "VALUES ($1, $2, $3, $4, $5, $6)",
			            rate,
			            data_rates["cbr"],
			            rub_to["tinkoff"],
			            rub_to["sberbank"],
			            rub_to["vtb"],
			            rub_to["spbbank"]
			            )
	except Exception as exc:
		capture_exception(exc)
	return True


async def save_euro_rates():
	try:
		async with ClientSession() as session:
			async with session.get(url=exchange_rates_dict["cbr_url"]) as resp:
				cbr_answer = await resp.text()
			async with session.get(url=exchange_rates_dict["euro_rates"]["tinkoff_api"]) as resp:
				tinkoff_api_answer_eur = await resp.json()
			async with session.get(url=exchange_rates_dict["euro_rates"]["sberbank_url"]) as resp:
				sberbank_euro_page = await resp.text()
			async with session.get(url=exchange_rates_dict["euro_rates"]["vtb_url"]) as resp:
				vtb_eur_answer = await resp.json()
			async with session.get(url=exchange_rates_dict["euro_rates"]["spbbank_url"]) as resp:
				spb_bank_page = await resp.text()

		cbr_rate_euro = round(json.loads(cbr_answer)["Valute"]["EUR"]["Value"], 2)

		# from RUB to EUR
		tinkoff_euro_rates = tinkoff_api_answer_eur["payload"]["rates"]
		tinkoff_euro_rate = "{:.2f}".format(next(item["sell"] for item in tinkoff_euro_rates if item["category"] == "DebitCardsTransfers"))

		sberbank_euro_rate = html.fromstring(sberbank_euro_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

		vtb_euro_rates = vtb_eur_answer["GroupedRates"][1]
		vtb_euro_rate = "{:.2f}".format(next(item["BankSellAt"] for item in vtb_euro_rates["MoneyRates"]))

		spbbank_euro_rate = html.fromstring(spb_bank_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

		# from EUR to RUB
		tinkoff_euro_to_rub = "{:.2f}".format(next(item["buy"] for item in tinkoff_euro_rates if item["category"] == "DebitCardsTransfers"))
		sberbank_euro_to_rub = html.fromstring(sberbank_euro_page).xpath('//div[@class="bank-currency__info-val"]/text()')[0].replace(",", ".")
		vtb_euro_to_rub = "{:.2f}".format(next(item["BankBuyAt"] for item in vtb_euro_rates["MoneyRates"]))
		spbbank_euro_to_rub = html.fromstring(spb_bank_page).xpath('//div[@class="bank-currency__info-val"]/text()')[0].replace(",", ".")

		data_rates = {
			"date": now,
			"cbr": cbr_rate_euro,
			"rub_to_euro": json.dumps({
				"tinkoff": tinkoff_euro_rate,
				"sberbank": sberbank_euro_rate,
				"vtb": vtb_euro_rate,
				"spbbank": spbbank_euro_rate
			}),
			"euro_to_rub": json.dumps({
				"tinkoff": tinkoff_euro_to_rub,
				"sberbank": sberbank_euro_to_rub,
				"vtb": vtb_euro_to_rub,
				"spbbank": spbbank_euro_to_rub
			})
		}
		await save_to_redis(redis_key="euro_rates", data_rates=data_rates)
		if now_time.minute == 0 and now_time.hour < 22:
			await save_to_postgres(data_rates=data_rates, rate="euro")
	except Exception as exc:
		capture_exception(exc)


async def save_usd_rates():
	try:
		async with ClientSession() as session:
			async with session.get(url=exchange_rates_dict["cbr_url"]) as resp:
				cbr_answer = await resp.text()
			async with session.get(url=exchange_rates_dict["usd_rates"]["tinkoff_api"]) as resp:
				tinkoff_api_answer_usd = await resp.json()
			async with session.get(url=exchange_rates_dict["usd_rates"]["sberbank_url"]) as resp:
				sberbank_usd_page = await resp.text()
			async with session.get(url=exchange_rates_dict["usd_rates"]["vtb_url"]) as resp:
				vtb_usd_answer = await resp.json()
			async with session.get(url=exchange_rates_dict["usd_rates"]["spbbank_url"]) as resp:
				spb_bank_page = await resp.text()

		cbr_rate_usd = round(json.loads(cbr_answer)["Valute"]["USD"]["Value"], 2)
		
		# from RUB to USD
		tinkoff_usd_rates = tinkoff_api_answer_usd["payload"]["rates"]
		tinkoff_usd_rate = "{0:.2f}".format(next(item["sell"] for item in tinkoff_usd_rates if item["category"] == "DebitCardsTransfers"))

		sberbank_usd_rate = html.fromstring(sberbank_usd_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

		vtb_usd_rates = vtb_usd_answer["GroupedRates"][0]
		vtb_usd_rate = "{0:.2f}".format(next(item["BankSellAt"] for item in vtb_usd_rates["MoneyRates"]))

		spbbank_usd_rate = html.fromstring(spb_bank_page).xpath('//div[@class="bank-currency__info-val"]/text()')[1].replace(",", ".")

		# from USD to RUB
		tinkoff_usd_to_rub = "{:.2f}".format(next(item["buy"] for item in tinkoff_usd_rates if item["category"] == "DebitCardsTransfers"))
		sberbank_usd_to_rub = html.fromstring(sberbank_usd_page).xpath('//div[@class="bank-currency__info-val"]/text()')[0].replace(",", ".")
		vtb_usd_to_rub = "{:.2f}".format(next(item["BankBuyAt"] for item in vtb_usd_rates["MoneyRates"]))
		spbbank_usd_to_rub = html.fromstring(spb_bank_page).xpath('//div[@class="bank-currency__info-val"]/text()')[0].replace(",", ".")

		data_rates = {
			"date": now,
			"cbr": cbr_rate_usd,
			"rub_to_usd": json.dumps({
				"tinkoff": tinkoff_usd_rate,
				"sberbank": sberbank_usd_rate,
				"vtb": vtb_usd_rate,
				"spbbank": spbbank_usd_rate
			}),
			"usd_to_rub": json.dumps({
				"tinkoff": tinkoff_usd_to_rub,
				"sberbank": sberbank_usd_to_rub,
				"vtb": vtb_usd_to_rub,
				"spbbank": spbbank_usd_to_rub
			})
		}

		await save_to_redis(redis_key="usd_rates", data_rates=data_rates)
		if now_time.minute == 0 and 10 < now_time.hour < 18:
			await save_to_postgres(data_rates=data_rates, rate="usd")
	except Exception as exc:
		capture_exception(exc)


if __name__ == '__main__':
	try:
		start = time.time()
		asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
		app_loop = asyncio.get_event_loop()
		app_loop.run_until_complete(save_euro_rates())
		app_loop.run_until_complete(save_usd_rates())
		print("Saved currencies for {date} Execution time: {time} sec".format(date=now, time=round(time.time() - start, 2)))
	except Exception as exc:
		capture_exception(exc)
