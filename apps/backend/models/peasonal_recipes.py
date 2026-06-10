class PeasonalRecipe:
    def __init__(
        self,
        peasonal_recipe_id: int,
        peasonal_recipe_name: str,
        peasonal_recipe_ingredients: list[str],
        peasonal_recipe_steps: list[str],
    ) -> None:
        self.peasonal_recipe_id = peasonal_recipe_id
        self.peasonal_recipe_name = peasonal_recipe_name
        self.peasonal_recipe_ingredients = peasonal_recipe_ingredients
        self.peasonal_recipe_steps = peasonal_recipe_steps


class PeasonalRecipeName:
    def __init__(
        self,
        peasonal_recipe_id: int,
        peasonal_recipe_name: str,
    ) -> None:
        self.peasonal_recipe_id = peasonal_recipe_id
        self.peasonal_recipe_name = peasonal_recipe_name
