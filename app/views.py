import json
import logging

from aiohttp import ClientSession

from app.cache.redis_actions import check_redis_key
from config.settings import BOT_TOKEN
from cronjobs.parse_stockrates import save_euro_rates, save_dollar_rates

logger = logging.getLogger(__name__)

base_url = "https://api.telegram.org/bot{}/".format(BOT_TOKEN)
send_message = "{}sendMessage".format(base_url)
headers = {'content-type': 'application/json'}


async def start(data):
	keyboard = await keyboard_render(buttons_list=[["Курс евро 💶"], ["Курс доллара 💵"]])
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
	except Exception as exc:
		logger.exception(exc)


async def incorrect_request(data):
	keyboard = await keyboard_render(buttons_list=[["Курс евро 💶"], ["Курс доллара 💵"]])
	try:
		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": "Ваш запрос мне непонятен 😔 \nПока что я могу предоставить информацию только по котировкам валют",
			"reply_markup": keyboard
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)
	except Exception as exc:
		logger.exception(exc)


async def euro_rates(data, request):
	keyboard = await keyboard_render(buttons_list=[["Курс евро 💶"], ["Курс доллара 💵"]])
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
		logger.exception(exc)


async def dollar_rates(data, request):
	keyboard = await keyboard_render(buttons_list=[["Курс евро 💶"], ["Курс доллара 💵"]])
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
		logger.exception(exc)


async def keyboard_render(buttons_list: list):
	return json.dumps({
		"resize_keyboard": True,
		"keyboard": buttons_list
	})


async def render_exchange_text():
	return "Курс {currency} на {date}\n" \
	       "ЦБ: <b>{cbr} ₽</b>\n\n" \
	       "Тинькофф Банк: <b>{tinkoff} ₽</b>\n" \
	       "Сбербанк: <b>{sberbank} ₽</b>\n" \
	       "Банк ВТБ: <b>{vtb} ₽</b>\n" \
	       "Банк Санкт-Петербург: <b>{spbbank} ₽</b>\n\n" \
	       "Все банки: {all_banks}"


async def send_redis_data(data, currency, text, keyboard, redis_data):
	if currency == "dollar":
		_c = "usd"
	else:
		_c = "eur"
	try:
		post_data = json.dumps({
			"chat_id": data["message"]["from"]["id"],
			"text": text.format(
				currency=currency,
				date=redis_data["date"],
				cbr=redis_data["cbr"],
				tinkoff=redis_data["tinkoff"],
				sberbank=redis_data["sberbank"],
				vtb=redis_data["vtb"],
				spbbank=redis_data["spbbank"],
				all_banks="https://www.banki.ru/products/currency/cash/{}/sankt-peterburg/#sort=sale&order=asc".format(_c)),
			"parse_mode": "HTML",
			"disable_web_page_preview": True,
			"reply_markup": keyboard
		})
		async with ClientSession(headers=headers) as session:
			await session.post(url=send_message, data=post_data)
	except Exception as exc:
		logger.exception(exc)
