import os


DEBUG = os.environ["DEBUG"]
DEBUG = DEBUG.lower() == "true"

BOT_TOKEN = os.environ["BOT_TOKEN"]


DATABASES = {
	"redis": {
		"HOST": os.environ["REDIS_HOST"],
		"PORT": 6379
	}
}
