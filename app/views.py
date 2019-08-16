import json
import logging
from datetime import datetime, timedelta

from aiohttp import ClientSession

from app.cache.redis_actions import check_redis_key
from config.logging import send_logging
from config.settings import BOT_TOKEN
from cronjobs.parse_stockrates import save_euro_rates, save_dollar_rates

logger = logging.getLogger(__name__)

base_url = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)
send_message = "{}sendMessage".format(base_url)
headers = {'content-type': 'application/json'}


async def start(data, request):
	user_id = data["message"]["from"]["id"]
	username = data["message"]["from"]["username"]
	first_name = data["message"]["from"]["first_name"]

	try:
		last_name = data["message"]["from"]["last_name"]
	except KeyError:
		last_name = ""

	message = data["message"]["text"]
	now = datetime.now()
	keyboard = await main_keyboard()
	try:
		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": "{}, добро пожаловать в бота!\n\n"
			        "С моей помощью ты cможешь быстро узнать курсы валютных пар\n\n"
			        "- 🇪🇺EUR/🇷🇺RUB\n"
			        "- 🇺🇸USD/🇷🇺RUB".format(data["message"]["from"]["first_name"]),
			"reply_markup": keyboard
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)

		db_conn = request.app["postgres"]
		async with db_conn.acquire() as con:
			async with con.transaction():
				user_exists = await con.fetchrow("SELECT id from users where user_id=$1", user_id)
				if not user_exists:
					await con.execute("INSERT INTO users (user_id, username, first_name, last_name, date)"
					                  "VALUES ($1, $2, $3, $4, $5)",
					                  user_id, username, first_name, last_name, now
					)
				await con.execute("INSERT INTO messages (date, message, from_user_id)"
				            "VALUES ($1, $2, $3)",
				            now, message, user_id
				)

	except Exception as exc:
		send_logging(exception=exc)


async def incorrect_request(data, request):
	user_id = data["message"]["from"]["id"]
	username = data["message"]["from"]["username"]
	first_name = data["message"]["from"]["first_name"]
	try:
		last_name = data["message"]["from"]["last_name"]
	except KeyError:
		last_name = ""
	try:
		message = data["message"]["text"]
	except KeyError:
		message = "not message"

	now = datetime.now()
	keyboard = await main_keyboard()
	try:
		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": "Ваш запрос мне непонятен 😔 \nПока что я могу предоставить информацию только по котировкам валют",
			"reply_markup": keyboard
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)

		db_conn = request.app["postgres"]
		async with db_conn.acquire() as con:
			async with con.transaction():
				user_exists = await con.fetchrow("SELECT id from users where user_id=$1", user_id)
				if not user_exists:
					await con.execute("INSERT INTO users (user_id, username, first_name, last_name, date)"
					                  "VALUES ($1, $2, $3, $4, $5)",
					                  user_id, username, first_name, last_name, now
					)
				await con.execute("INSERT INTO messages (date, message, from_user_id)"
				                  "VALUES ($1, $2, $3)",
				                  now, message, user_id
				                  )
	except Exception as exc:
		send_logging(exception=exc)


async def euro_rates(data, request):
	keyboard = await main_keyboard()
	text = await render_exchange_text()
	try:
		redis_data = await check_redis_key(redis_key="euro_rates", request=request)
		if redis_data:
			await send_redis_data(data=data, currency="евро", text=text, keyboard=keyboard, redis_data=redis_data)
		else:
			wait_post_data = json.dumps({
				"chat_id": data["message"]["from"]["id"],
				"text": "<i>Получаю данные. Ожидайте...</i>",
				"parse_mode": "HTML",
				"disable_web_page_preview": True,
				"reply_markup": keyboard
			})
			async with ClientSession(headers=headers) as session:
				await session.post(url=send_message, data=wait_post_data)

			await save_euro_rates()

			redis_data = await check_redis_key(redis_key="euro_rates", request=request)
			if redis_data:
				await send_redis_data(data=data, currency="евро", text=text, keyboard=keyboard, redis_data=redis_data)
			else:
				post_data = json.dumps({
					"chat_id": data["message"]["from"]["id"],
					"text": "Данные временно недоступны",
					"parse_mode": "HTML",
					"disable_web_page_preview": True,
					"reply_markup": keyboard
				})
				async with ClientSession(headers=headers) as session:
					await session.post(url=send_message, data=post_data)
	except Exception as exc:
		send_logging(exception=exc)


async def dollar_rates(data, request):
	keyboard = await main_keyboard()
	text = await render_exchange_text()
	try:
		redis_data = await check_redis_key(redis_key="dollar_rates", request=request)
		if redis_data:
			await send_redis_data(data=data, currency="доллара", text=text, keyboard=keyboard, redis_data=redis_data)
		else:
			wait_post_data = json.dumps({
				"chat_id": data["message"]["from"]["id"],
				"text": "<i>Получаю данные. Ожидайте...</i>",
				"parse_mode": "HTML",
				"disable_web_page_preview": True,
				"reply_markup": keyboard
			})
			async with ClientSession(headers=headers) as session:
				await session.post(url=send_message, data=wait_post_data)

			await save_dollar_rates()

			redis_data = await check_redis_key(redis_key="dollar_rates", request=request)
			if redis_data:
				await send_redis_data(data=data, currency="доллара", text=text, keyboard=keyboard, redis_data=redis_data)
			else:
				post_data = json.dumps({
					"chat_id": data["message"]["from"]["id"],
					"text": "Данные временно недоступны",
					"parse_mode": "HTML",
					"disable_web_page_preview": True,
					"reply_markup": keyboard
				})
				async with ClientSession(headers=headers) as session:
					await session.post(url=send_message, data=post_data)
	except Exception as exc:
		send_logging(exception=exc)


async def rates_analytics(data):
	keyboard = await keyboard_render(buttons_list=[["Евро"], ["Доллар"]])
	try:
		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": "Выберите валюту, по которой необходима аналитика динамики изменения курсов у банков",
			"parse_mode": "HTML",
			"reply_markup": keyboard
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)
	except Exception as exc:
		send_logging(exception=exc)


async def analytics_message(data):
	currency = data["message"]["text"].lower()
	if currency == "евро":
		emoji = "🇪🇺"
	elif currency == "доллар":
		emoji = "🇺🇸"
	else:
		raise NameError

	keyboard = await keyboard_render(buttons_list=[["День {}".format(emoji)],
	                                               ["Неделя {}".format(emoji)],
	                                               ["Месяц {}".format(emoji)],
	                                               ["Год {}".format(emoji)],
	                                               ["Главное меню"]])
	try:
		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": "Выберите интересующий период",
			"parse_mode": "HTML",
			"disable_web_page_preview": True,
			"reply_markup": keyboard
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)
	except Exception as e:
		send_logging(exception=e)


async def analytics_for_period(data, request):
	now = datetime.now().date()
	tomorrow = now + timedelta(days=1)
	user_request = data["message"]["text"]
	emoji = user_request.split()[-1]

	if emoji == "🇪🇺":
		currency = "euro"
	elif emoji == "🇺🇸":
		currency = "dollar"
	else:
		raise NameError

	if "День" in user_request:
		date1 = now
		date2 = tomorrow
	elif "Неделя" in user_request:
		date1 = now - timedelta(weeks=1)
		date2 = tomorrow
	elif "Месяц" in user_request:
		date1 = now - timedelta(weeks=4)
		date2 = tomorrow
	elif "Год" in user_request:
		date1 = now - timedelta(days=365)
		date2 = tomorrow
	else:
		raise NameError

	try:
		db_conn = request.app["postgres"]
		async with db_conn.acquire() as con:
			async with con.transaction():
				_period = await con.fetchrow("SELECT json_agg(json_build_object('cbr', rates.cbr, 'tinkoff', rates.tinkoff, 'sberbank', rates.sberbank, 'vtb', rates.vtb, 'spbbank', rates.spbbank)) as values_list from rates where rate='{}' and date between '{}' and '{}'".format(currency, date1, date2))

		period = json.loads(_period["values_list"])
		first_rate = period[0]
		last_rate = period[-1]

		cbr_delta = last_rate["cbr"] - first_rate["cbr"]
		tinkoff_delta = last_rate["tinkoff"] - first_rate["tinkoff"]
		sberbank_delta = last_rate["sberbank"] - first_rate["sberbank"]
		vtb_delta = last_rate["vtb"] - first_rate["vtb"]
		spbbank_delta = last_rate["spbbank"] - first_rate["spbbank"]

		keyboard = await keyboard_render(buttons_list=[["День {}".format(emoji)],
		                                               ["Неделя {}".format(emoji)],
		                                               ["Месяц {}".format(emoji)],
		                                               ["Год {}".format(emoji)],
		                                               ["Главное меню"]])
		text = await render_analytics_text()
		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": text.format(
				currency="евро" if currency == "euro" else "доллару",
				date=now.strftime("%d.%m.%Y"),
				cbr=await render_delta(_delta=cbr_delta),
				tinkoff=await render_delta(_delta=tinkoff_delta),
				sberbank=await render_delta(_delta=sberbank_delta),
				vtb=await render_delta(_delta=vtb_delta),
				spbbank=await render_delta(_delta=spbbank_delta)
			),
			"parse_mode": "HTML",
			"disable_web_page_preview": True,
			"reply_markup": keyboard
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)
	except Exception as e:
		send_logging(exception=e)


async def render_delta(_delta):
	if _delta < 0:
		delta = "📉 {:.2f}".format(_delta)
	elif _delta > 0:
		delta = "📈 +{:.2f}".format(_delta)
	else:
		delta = 0
	return delta


async def main_keyboard():
	return json.dumps({
		"resize_keyboard": True,
		"keyboard": [["Курс евро 💶"],
		             ["Курс доллара 💵"],
		             ["Аналитика 📊"]]
	})


async def keyboard_render(buttons_list: list):
	return json.dumps({
		"resize_keyboard": True,
		"keyboard": buttons_list
	})


async def render_analytics_text():
	return "Аналитика по {currency} за {date}\n\n" \
		   "ЦБ: <b>{cbr} ₽</b>\n" \
	       "Тинькофф Банк: <b>{tinkoff} ₽</b>\n" \
	       "Сбербанк: <b>{sberbank} ₽</b>\n" \
	       "Банк ВТБ: <b>{vtb} ₽</b>\n" \
	       "Банк Санкт-Петербург: <b>{spbbank} ₽</b>\n\n"


async def render_exchange_text():
	return "Курс {currency} на {date}\n" \
	       "ЦБ: <b>{cbr} ₽</b>\n\n" \
	       "₽ → € | € → ₽\n" \
	       "Тинькофф Банк: <b>{tinkoff} ₽</b> | <b>{tinkoff_to_rub} ₽</b>\n" \
	       "Сбербанк: <b>{sberbank} ₽</b> | <b>{sberbank_to_rub} ₽</b>\n" \
	       "Банк ВТБ: <b>{vtb} ₽</b> | <b>{vtb_to_rub} ₽</b>\n" \
	       "Банк Санкт-Петербург: <b>{spbbank} ₽</b> | <b>{spbbank_to_rub} ₽</b>\n\n"
	       # "Все банки: {all_banks}"


async def send_redis_data(data, currency, text, keyboard, redis_data):
	if currency == "dollar":
		_c = "usd"
	else:
		_c = "euro"
	try:
		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": text.format(
				currency=currency,
				date=redis_data["date"],
				cbr=redis_data["cbr"],
				tinkoff=redis_data["rub_to_{}".format(_c)]["tinkoff"],
				tinkoff_to_rub=redis_data["{}_to_rub".format(_c)]["tinkoff"],
				sberbank=redis_data["rub_to_{}".format(_c)]["sberbank"],
				sberbank_to_rub=redis_data["{}_to_rub".format(_c)]["sberbank"],
				vtb=redis_data["rub_to_{}".format(_c)]["vtb"],
				vtb_to_rub=redis_data["{}_to_rub".format(_c)]["vtb"],
				spbbank=redis_data["rub_to_{}".format(_c)]["spbbank"],
				spbbank_to_rub=redis_data["{}_to_rub".format(_c)]["spbbank"]),
				# all_banks="https://www.banki.ru/products/currency/cash/{}/sankt-peterburg/#sort=sale&order=asc".format(_c)),
			"parse_mode": "HTML",
			"disable_web_page_preview": True,
			"reply_markup": keyboard
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)
	except Exception as exc:
		send_logging(exception=exc)
