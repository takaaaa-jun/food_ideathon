class IngredientDetail:
    def __init__(
        self,
        ingredient_detail_id: int,
        ingredient_id: int,
        ingredient_detail_name: str,
        ingredient_detail_symbol: str,
        ingredient_detail_supplement: str,
        ingredient_detail_normalized_name: str,
        ingredient_detail_amount: float,
        ingredient_detail_unit: str,
        ingredient_detail_normalized_quantity: float,
    ) -> None:
        self.ingreident_detail_id = ingredient_detail_id
        self.ingredient_id = ingredient_id
        self.ingredient_detail_name = ingredient_detail_name
        self.ingredient_detail_symbol = ingredient_detail_symbol
        self.ingredient_detail_supplement = ingredient_detail_supplement
        self.ingredient_detail_normalized_name = ingredient_detail_normalized_name
        self.ingredient_detail_amount = ingredient_detail_amount
        self.ingredient_detail_unit = ingredient_detail_unit
        self.ingredient_detail_normalized_quantity = (
            ingredient_detail_normalized_quantity
        )
