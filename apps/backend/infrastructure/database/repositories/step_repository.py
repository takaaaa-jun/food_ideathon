from scripts.check_db import cursor
from mysql.connector.abstracts import MySQLConnectionAbstract

from apps.backend.infrastructure.database.raw_step_record import RawStepRecord

class StepRepository:
    def __init__(self, connection: MySQLConnectionAbstract) -> None:
        self.connection = connection
    
    def find_by_recipe_id(
        self,
        recipe_id: int,
    ) -> RawStepRecord | None:
        cursor = self.connection.cursor(dictionary=True)
        
        cursor.execute(
            """
            SELECT
                id,
                recipe_id,
                position,
                memo
            FROM steps
            WHERE recipe_id = %s
            LIMIT 1
            """,
            (recipe_id,),
        )
        
        raw = cursor.fetchone()
        
        if raw is None:
            return None
        
        return RawStepRecord(
            step_id=raw["id"],
            recipe_id=raw["recipe_id"],
            step_position_id=raw["position"],
            step_text=raw["memo"],
        )