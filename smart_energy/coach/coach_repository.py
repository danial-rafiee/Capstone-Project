"""Repository for persisting and retrieving Coach evaluations in MySQL (or SQLite for unit tests)."""

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from smart_energy.coach.exceptions import EvaluationPersistenceError


class CoachRepository:
    """Handles database interactions for Coach evaluations using the shared MySQL Database."""

    def __init__(self, database: Optional[Any] = None) -> None:
        if database is None:
            from smart_energy.analytics.database import Database
            self._database = Database()
            self._sqlite_path = None
        elif isinstance(database, str):
            self._database = None
            self._sqlite_path = database
            self._ensure_sqlite_table()
        else:
            self._database = database
            self._sqlite_path = None

    def _get_sqlite_connection(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self._sqlite_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as exc:
            raise EvaluationPersistenceError(f"SQLite connection failed: {exc}") from exc

    def _ensure_sqlite_table(self) -> None:
        try:
            with self._get_sqlite_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS coach_evaluations (
                        evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        building_id INTEGER NOT NULL,
                        score REAL NOT NULL,
                        penalty_eur REAL NOT NULL DEFAULT 0.00,
                        peak_detected INTEGER NOT NULL DEFAULT 0,
                        advice_summary VARCHAR(255) NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
        except EvaluationPersistenceError:
            raise
        except Exception as exc:
            raise EvaluationPersistenceError(f"Failed to initialize SQLite evaluations table: {exc}") from exc

    def _ensure_mysql_table(self, cursor: Any) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS coach_evaluations (
                evaluation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                building_id INT NOT NULL,
                score DECIMAL(5,2) NOT NULL,
                penalty_eur DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                peak_detected BOOLEAN NOT NULL DEFAULT FALSE,
                advice_summary VARCHAR(255) NOT NULL,
                created_at DATETIME(6) NOT NULL,
                FOREIGN KEY (building_id) REFERENCES buildings(building_id)
            ) ENGINE=InnoDB
            """
        )

    def save_evaluation(
        self,
        building_id: int,
        score: Union[Decimal, float],
        penalty_eur: Union[Decimal, float],
        peak_detected: bool,
        advice_summary: str,
    ) -> int:
        """Persist a sustainability evaluation record into MySQL (or SQLite) and return evaluation_id."""
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        summary_trimmed = str(advice_summary)[:255]

        if self._sqlite_path is not None:
            try:
                with self._get_sqlite_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO coach_evaluations (building_id, score, penalty_eur, peak_detected, advice_summary, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            int(building_id),
                            float(score),
                            float(penalty_eur),
                            1 if peak_detected else 0,
                            summary_trimmed,
                            now_utc.isoformat(sep=" "),
                        ),
                    )
                    conn.commit()
                    return int(cursor.lastrowid)
            except EvaluationPersistenceError:
                raise
            except Exception as exc:
                raise EvaluationPersistenceError(f"Failed to save evaluation: {exc}") from exc

        conn = None
        cursor = None
        try:
            conn = self._database.connect()
            cursor = conn.cursor()
            self._ensure_mysql_table(cursor)
            cursor.execute(
                """
                INSERT INTO coach_evaluations (building_id, score, penalty_eur, peak_detected, advice_summary, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    int(building_id),
                    Decimal(str(score)),
                    Decimal(str(penalty_eur)),
                    bool(peak_detected),
                    summary_trimmed,
                    now_utc,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)
        except Exception as exc:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise EvaluationPersistenceError(f"Failed to save evaluation to MySQL: {exc}") from exc
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    def list_for_building(self, building_id: int) -> List[Dict[str, Any]]:
        """Retrieve evaluation records for a specific building from MySQL (or SQLite)."""
        if self._sqlite_path is not None:
            try:
                with self._get_sqlite_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT evaluation_id, evaluation_id AS id, building_id, score, penalty_eur, peak_detected, advice_summary, created_at
                        FROM coach_evaluations
                        WHERE building_id = ?
                        ORDER BY created_at DESC, evaluation_id DESC
                        """,
                        (int(building_id),),
                    )
                    return [dict(row) for row in cursor.fetchall()]
            except EvaluationPersistenceError:
                raise
            except Exception as exc:
                raise EvaluationPersistenceError(f"Failed to fetch records: {exc}") from exc

        conn = None
        cursor = None
        try:
            conn = self._database.connect()
            cursor = conn.cursor(dictionary=True)
            self._ensure_mysql_table(cursor)
            cursor.execute(
                """
                SELECT evaluation_id, building_id, score, penalty_eur, peak_detected, advice_summary, created_at
                FROM coach_evaluations
                WHERE building_id = %s
                ORDER BY created_at DESC, evaluation_id DESC
                """,
                (int(building_id),),
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["id"] = item["evaluation_id"]
                item["peak_detected"] = bool(item["peak_detected"])
                results.append(item)
            return results
        except Exception as exc:
            raise EvaluationPersistenceError(f"Failed to fetch records from MySQL: {exc}") from exc
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()


# Backward-compatible alias matching HA3 specification
CoachEvaluationRepository = CoachRepository
