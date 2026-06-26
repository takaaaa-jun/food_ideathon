from mysql.connector.abstracts import MySQLConnectionAbstract

from apps.backend.infrastructure.database.raw_ingredient_record import (
    RawIngredientRecord,
)


class IngredientRepository:
    def __init__(self, connection: MySQLConnectionAbstract) -> None:
        self.connection = connection

    def find_by_ingredient_name(
        self,
        ingredient_name: str,
    ) -> RawIngredientRecord | None:
        cursor = self.connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                recipe_id,
                name,
                quantity
            FROM ingredients
            WHERE name = %s
            LIMIT 1
            """,
            (ingredient_name,),
        )

        raw = cursor.fetchone()

        if raw is None:
            return None

        return RawIngredientRecord(
            ingredient_id=raw["id"],
            recipe_id=raw["recipe_id"],
            ingredient_name=raw["name"],
            ingredient_quantity=raw["quantity"],
        )
