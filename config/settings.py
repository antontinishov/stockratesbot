import os


DEBUG = os.environ["DEBUG"]
DEBUG = DEBUG.lower() == "true"

BOT_TOKEN = os.environ["BOT_TOKEN"]
