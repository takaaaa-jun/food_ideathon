from .ingredient import Ingredient
from .nutrition import Nutrition

class Recipe:
    def __init__(
        self,
        recipe_id: int,
        recipe_title: str,
        description: str | None,
        ingredients: list[Ingredient],
        nutrition: Nutrition | None,
    ) -> None:
        self.recipe_id = recipe_id
        self.recipe_title = recipe_title
        self.description = description
        self.ingreidents = ingredients
        self.nutrition = nutrition