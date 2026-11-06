"""Database access layer for Subsystem C (AI Coach & Sustainability Score)."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any


class CoachEvaluationRepository:
    """Repository pattern to manage building sustainability score evaluations in MySQL."""

    def __init__(self, database) -> None:
        self._database = database

    def save_evaluation(
        self,
        building_id: int,
        score: Decimal,
        penalty_eur: Decimal = Decimal("0.00"),
        peak_detected: bool = False,
        advice_summary: str = "",
        created_at: Optional[datetime] = None,
    ) -> int:
        """Persist a sustainability score evaluation for a building."""
        if created_at is None:
            created_at = datetime.utcnow()

        sql = """
            INSERT INTO coach_evaluations 
            (building_id, score, penalty_eur, peak_detected, advice_summary, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            building_id,
            float(score),
            float(penalty_eur),
            peak_detected,
            advice_summary,
            created_at,
        )

        with self._database.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                conn.commit()
                return cursor.lastrowid

    def list_for_building(self, building_id: int) -> List[Dict[str, Any]]:
        """Retrieve all historical evaluations for a given building."""
        sql = """
            SELECT evaluation_id, building_id, score, penalty_eur, 
                   peak_detected, advice_summary, created_at
            FROM coach_evaluations
            WHERE building_id = %s
            ORDER BY created_at DESC
        """
        results = []
        with self._database.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (building_id,))
                rows = cursor.fetchall()
                for row in rows:
                    results.append({
                        "evaluation_id": row[0],
                        "building_id": row[1],
                        "score": Decimal(str(row[2])),
                        "penalty_eur": Decimal(str(row[3])),
                        "peak_detected": bool(row[4]),
                        "advice_summary": row[5],
                        "created_at": row[6],
                    })
        return results