from mysql.connetor.abstracts import MySQLConnectionAbstract

from apps.backend.infrastructure.database.raw_recipe_record import RawRecipeRecord


class RecipeRepository:
    def __init__(self, connection: MySQLConnectionAbstract) -> None:
        self.connection = connection

    def find_by_recipe_id(
        self,
        recipe_id: int,
    ) -> RawRecipeRecord | None:
        cursor = self.connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                attribute,
                title,
                description,
                cooking_time,
                serving_for,
                published_at,
                serving_count
            FROM recipes
            WHHERE id = %s
            LIMIT 1
            """,
            (recipe_id,),
        )

        raw = cursor.fetchone()

        if raw is None:
            return None

        return RawRecipeRecord(
            recipe_id=raw["id"],
            recipe_attribute=raw["attribute"],
            recipe_title=raw["title"],
            recipe_description=raw["description"],
            recipe_cooking_time=raw["cooking_time"],
            recipe_serving_text=raw["serving_for"],
            recipe_serving_count=raw["serving_count"],
            recipe_published_at=raw["publish_count"],
        )
