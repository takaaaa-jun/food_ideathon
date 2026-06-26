class Ingredient:
    def __init__(
        self,
        ingredient_id: int,
        recipe_id: int,
        ingredient_name: str,
        ingredient_quantity: str,
    ) -> None:
        self.ingredient_id = ingredient_id
        self.recipe_id = recipe_id
        self.ingredient_name = ingredient_name
        self.ingredient_quantity = ingredient_quantity
