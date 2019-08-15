FROM devdevregistry.azurecr.io/stockratesbot:latest

RUN cp /docker/stockratesbot/cronjobs/cron-file /etc/cron.d/cron-file && \
    chmod 0644 /etc/cron.d/cron-file

RUN crontab /etc/cron.d/cron-file

CMD ["cron", "-f"]
