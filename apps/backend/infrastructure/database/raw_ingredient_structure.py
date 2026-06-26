class RawIngredientStructureRecord:
    def __init__(
        self,
        ingredient_structure_id: int,
        ingredient_id: int,
        ingredient_detail_name: str,
        ingredient_detail_symbol: str,
        ingredient_detail_supplement: str,
        ingredient_detail_normalized_name: str,
    ) -> None:
        self.ingredient_structure_id = ingredient_structure_id
        self.ingredient_id = ingredient_id
        self.ingredient_detail_name = ingredient_detail_name
        self.ingredient_detail_symbol = ingredient_detail_symbol
        self.ingredient_detail_supplement = ingredient_detail_supplement
        self.ingredient_detail_normalized_name = ingredient_detail_normalized_name