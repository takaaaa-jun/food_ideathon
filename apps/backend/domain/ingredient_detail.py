class IngredientDetail:
    def __init__(
        self,
        ingredient_id: int,
        ingredient_detail_name: str,
        ingredient_detail_symbol: str,
        ingredient_detail_note: str,
        ingredient_detail_amount: float,
        ingredient_detail_unit: str,
        ingredient_detail_other: str,
    ) -> None:
        self.ingredient_id = ingredient_id
        self.ingredient_detail_name = ingredient_detail_name
        self.ingredient_detail_symbol = ingredient_detail_symbol
        self.ingredient_detail_note = ingredient_detail_note
        self.ingredient_detail_amount = ingredient_detail_amount
        self.ingredient_detail_unit = ingredient_detail_unit
        self.ingredient_detail_other = ingredient_detail_other
