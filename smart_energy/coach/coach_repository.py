"""Repository for persisting and retrieving Coach evaluations."""

import sqlite3
from typing import Any, Dict, List
from smart_energy.coach.exceptions import EvaluationPersistenceError


class CoachRepository:
    """Handles database interactions for Coach evaluations."""

    def __init__(self, db_path: str = "smart_energy.db") -> None:
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as exc:
            raise EvaluationPersistenceError(f"Database connection failed: {exc}") from exc

    def list_for_building(self, building_id: int) -> List[Dict[str, Any]]:
        """Retrieve evaluation records for a specific building."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, building_id, score, penalty_eur, peak_detected, advice_summary, created_at
                    FROM coach_evaluations
                    WHERE building_id = ?
                    ORDER BY created_at DESC
                    """,
                    (building_id,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except EvaluationPersistenceError:
            raise
        except Exception as exc:
            raise EvaluationPersistenceError(f"Failed to fetch records: {exc}") from exc