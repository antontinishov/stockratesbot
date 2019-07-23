FROM zartug345/stockratesbot:base

COPY app/background_jobs/parse_stockrates.py /etc/cron.d/parse_stockrates.py
RUN chmod 0644 /etc/cron.d/parse_stockrates.py

USER www-data

RUN crontab /etc/cron.d/parse_stockrates.py

CMD ["cron", "-f"]
