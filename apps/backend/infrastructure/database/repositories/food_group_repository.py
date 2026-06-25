from mysql.connector.abstracts import MySQLConnectionAbstract

from apps.backend.infrastructure.database.raw_food_group_record import (
    RawFoodGroupRecord,
)


class FoodGroupRepository:
    def __init__(self, connection: MySQLConnectionAbstract) -> None:
        self.connection = connection

    def fing_by_group_id(
        self,
        group_id: int,
    ) -> RawFoodGroupRecord | None:
        cursor = self.connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                group_id,
                group_name
            FROM ingredient_group
            WHERE group_id = %s
            LIMIT 1
            """,
            (group_id,),
        )

        raw = cursor.fetchone()

        if raw is None:
            return None

        return RawFoodGroupRecord(
            food_id=raw["id"],
            group_id=raw["group_id"],
            group_name=raw["group_name"],
        )
