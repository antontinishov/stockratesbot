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


