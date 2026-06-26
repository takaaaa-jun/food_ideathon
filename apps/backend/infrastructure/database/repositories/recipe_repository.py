from mysql.connetor.abstracts import MySQLConnectionAbstract

from apps.backend.infrastructure.database.raw_recipe_record import RawRecipeRecord

class RecipeRepository:
    def __init__(self, connection: MySQLConnectionAbstract) -> None:
        self.connection = connection
        
    def find_by_recipe_title(
        self,
        recipe_title: str,
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
                
            """
        )