from unittest import registerResult
from mysql.connector.abstracts import MySQLConnectionAbstract

from apps.backend.infrastructure.database.raw_ingredient_structure_record import RawIngredientStructureRecord

class IngredientStructureRepository:
    def __init__(self, connection: MySQLConnectionAbstract) -> None:
        self.connection = connection
    
    def find_by_ingredient_id(
        self,
        ingredient_id: str,
    ) -> RawIngredientStructureRecord | None:
        cursor = self.connection.cursor(dictionary=True)
        
        cursor.execute(
            """
            SELECT
                id,
                ingredient_id,
                name,
                symbol,
                supplement,
                normalized_name
            FROM ingredient_structured
            WHERE id = %s
            LIMIT 1
            """,
            (ingredient_id,),
        )
        
        raw = cursor.fetchone()
        
        if raw is None:
            return None
        
        return RawIngredientStructureRecord(
            ingredient_structure_id=raw["id"],
            ingredient_id=raw["ingredient_id"],
            ingredient_detail_name=raw["name"],
            ingredient_detail_symbol=raw["symbol"],
            ingredient_detail_supplement=raw["supplement"],
            ingredient_detail_normalized_name=raw["normalized_name"],
        )