#!/bin/bash
# Runs once, on first initialization of the mysql_data volume (official image entrypoint).
# Creates the isolated test database used by backend DB tests and grants it to the app user.
# The main database and app user are created by the image from MYSQL_DATABASE / MYSQL_USER.
# Note: this file is SOURCED by the entrypoint; do not use `set -u` (it breaks entrypoint functions).

docker_process_sql --database=mysql <<-EOSQL
	CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}_test\`
	  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
	GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}_test\`.* TO '${MYSQL_USER}'@'%';
	FLUSH PRIVILEGES;
EOSQL
