from .ingredient import Ingredient
from .nutrition import Nutrition
from .step import Step

class Recipe:
    def __init__(
        self,
        recipe_id: int,
        recipe_title: str,
        description: str | None,
        ingredients: list[Ingredient],
        steps: list[step],
        nutrition: Nutrition | None,
    ) -> None:
        self.recipe_id = recipe_id
        self.recipe_title = recipe_title
        self.description = description
        self.ingreidents = ingredients
        self.steps = steps
        self.nutrition = nutrition