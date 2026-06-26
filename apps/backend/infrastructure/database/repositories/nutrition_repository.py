from mysql.connector.abstracts import MySQLConnectionAbstract

from apps.backend.infrastructure.database.raw_nutrition_record import RawNutritionRecord


class NutritionRepository:
    def __init__(self, connection: MySQLConnectionAbstract) -> None:
        self.connection = connection

    def find_by_food_name(
        self,
        food_name: str,
    ) -> RawNutritionRecord | None:
        cursor = self.connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                ENERC_KCAL,
                PROT,
                FAT,
                CHOAVLDF,
                FIB,
                NACL_EQ
            FROM nutrition
            WHERE name = %s
            LIMIT 1
            """,
            (food_name,),
        )

        raw = cursor.fetchone()

        if raw is None:
            return None

        return RawNutritionRecord(
            food_id=raw["id"],
            food_name=raw["name"],
            energy=raw["ENERC_KCAL"],
            protein=raw["PROT"],
            fat=raw["FAT"],
            carbs=raw["CHOAVLDF"],
            fib=raw["FIB"],
            salt=raw["NACL_EQ"],
        )
