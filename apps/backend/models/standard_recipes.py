class StandardRecipe:
    def __init__(
        self,
        standard_recipe_id: int,
        standard_recipe_name: str,
        standard_recipe_ingredients: list[str],
        standard_recipe_steps: list[str],
    ) -> None:
        self.standard_recipe_id = standard_recipe_id
        self.standard_recipe_name = standard_recipe_name
        self.standard_recipe_ingredients = standard_recipe_ingredients
        self.standard_recipe_steps = standard_recipe_steps
