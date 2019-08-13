#!/usr/bin/env bash

cd ../
docker build -t zartug345/stockratesbot:latest .
cd deploy
docker-compose build && docker-compose up -d