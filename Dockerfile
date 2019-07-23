FROM zartug345/stockratesbot:base

ADD . /docker/stockratesbot

USER www-data

CMD ["/bin/bash", "-c", "python3.6 /docker/main.py"]
