class RawIngredientUnit:
    def __init__(
        self,
        ingredient_unit_id: int,
        ingredient_id: int,
        ingredient_detail_amount: float,
        ingredient_detail_unit: str,
        ingredient_detail_normalized_quantity: float,
    ) -> None:
        self.ingredient_unit_id = ingredient_unit_id
        self.ingredient_id = ingredient_id
        self.ingredient_detail_amount = ingredient_detail_amount
        self.ingredient_detail_unit = ingredient_detail_unit
        self.ingredient_detail_normalized_quantity = ingredient_detail_normalized_quantity