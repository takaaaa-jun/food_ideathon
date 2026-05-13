class PeasonalRecipe:
    def __init__(
        self,
        recipe_id: int,
        recipe_name: str,
        ingredients: list[str],
        steps: list[str],
    ):
        self.recipe_id = recipe_id
        self.recipe_name = recipe_name
        self.ingredients = ingredients
        self.steps = steps
