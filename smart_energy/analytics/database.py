"""Reusable connection settings for the HA3 database."""

import os

import mysql.connector


class Database:
    def __init__(self):
        self._config = {
            "host": os.environ.get("SMART_ENERGY_DB_HOST", "127.0.0.1"),
            "port": int(os.environ.get("SMART_ENERGY_DB_PORT", "3306")),
            "user": os.environ.get("SMART_ENERGY_DB_USER", "root"),
            "password": os.environ.get("SMART_ENERGY_DB_PASSWORD", "root"),
            "database": os.environ.get(
                "SMART_ENERGY_DB_NAME", "smart_energy_ha3"
            ),
            "connection_timeout": 5,
        }

    def connect(self):
        return mysql.connector.connect(**self._config)