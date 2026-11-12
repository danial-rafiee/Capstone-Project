"""Repository for persisting and retrieving Coach evaluations."""

import sqlite3
from decimal import Decimal
from typing import Any, Dict, List, Union
from smart_energy.coach.exceptions import EvaluationPersistenceError


class CoachRepository:
    """Handles database interactions for Coach evaluations."""

    def __init__(self, db_path: str = "smart_energy.db") -> None:
        self.db_path = db_path if isinstance(db_path, str) else "smart_energy.db"
        self._ensure_table()

    def _get_connection(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as exc:
            raise EvaluationPersistenceError(f"Database connection failed: {exc}") from exc

    def _ensure_table(self) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS coach_evaluations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        building_id INTEGER NOT NULL,
                        score REAL NOT NULL,
                        penalty_eur REAL NOT NULL,
                        peak_detected INTEGER NOT NULL DEFAULT 0,
                        advice_summary TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()
        except EvaluationPersistenceError:
            raise
        except Exception as exc:
            raise EvaluationPersistenceError(f"Failed to initialize evaluations table: {exc}") from exc

    def save_evaluation(
        self,
        building_id: int,
        score: Union[Decimal, float],
        penalty_eur: Union[Decimal, float],
        peak_detected: bool,
        advice_summary: str,
    ) -> int:
        """Persist a sustainability evaluation record and return its ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO coach_evaluations (building_id, score, penalty_eur, peak_detected, advice_summary)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        int(building_id),
                        float(score),
                        float(penalty_eur),
                        1 if peak_detected else 0,
                        str(advice_summary),
                    ),
                )
                conn.commit()
                return int(cursor.lastrowid)
        except EvaluationPersistenceError:
            raise
        except Exception as exc:
            raise EvaluationPersistenceError(f"Failed to save evaluation: {exc}") from exc

    def list_for_building(self, building_id: int) -> List[Dict[str, Any]]:
        """Retrieve evaluation records for a specific building."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id AS evaluation_id, id, building_id, score, penalty_eur, peak_detected, advice_summary, created_at
                    FROM coach_evaluations
                    WHERE building_id = ?
                    ORDER BY created_at DESC, id DESC
                    """,
                    (building_id,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except EvaluationPersistenceError:
            raise
        except Exception as exc:
            raise EvaluationPersistenceError(f"Failed to fetch records: {exc}") from exc


# Backward-compatible alias
CoachEvaluationRepository = CoachRepository
