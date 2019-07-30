import os


DEBUG = os.environ["DEBUG"]
DEBUG = DEBUG.lower() == "true"

BOT_TOKEN = os.environ["BOT_TOKEN"]


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
