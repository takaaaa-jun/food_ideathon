from apps.backend.infrastructure.database.raw_nutrition_record import RawNutritionRecord
from mysql.connector.abstracts import MyMySQLConnectionAbstract

class NutritionRepository:
    def __init__(
        self,
        connection: MySQLConnectionAbstract
    ) -> None:
        self.connection = connection
    
    def find_by_name(
        self,
        ingredient_name: str,
    ) -> RawNutritionRecord | None:
        cursor = self.connection.cursor(dictionary=True)
        
        cursor.execute(
            """
            SELECT
                id,
                name,
                group,
                ENERC_KCAL,
                PROT,
                FAT,
                CHOAVLDF,
                FIB,
                NACL_EQ,
            FROM nutrition
            WHERE name = %s
            LIMIT 1
            """,
            (ingredient_name,),
        )
        
        raw = cursor.fetchone()
        
        if raw in None:
            return None
        
        return RawNutritionRecord(
            nutrition_id = raw["id"],
            nutrition_name = raw["name"],
            group_id = raw["group"],
            
        )