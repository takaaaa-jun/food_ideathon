from datetime import date
class RawRecipeRecord:
    def __init__(
        self,
        recipe_id: int,
        recipe_attribute: str,
        recipe_title: str,
        recipe_description: str | None,
        recipe_cooking_time: str | None,
        recipe_published_at: date,
    ) -> None:
        self.recipe_id = recipe_id
        self.recipe_attribute = recipe_attribute
        self.recipe_title = recipe_title
        self.recipe_description = recipe_description
        self.recipe_cooking_time = recipe_cooking_time
        self.recipe_published_at = recipe_published_at
        