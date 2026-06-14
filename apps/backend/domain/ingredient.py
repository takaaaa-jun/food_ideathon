class Ingredient:
    def __init__(
        self,
        ingredient_id: int,
        ingredient_name: str,
        quantity: str,
    ) -> None:
        self.ingredient_id = ingredient_id
        self.ingredient_name = ingredient_name
        self.quantity = quantity


class IngredientDetail:
    def __init__(
        self,
        ingredient_id: int,
        name: str,
        symbol: str,
        note: str,
        amount: float,
        unit: str,
        other: str,
    ) -> None:
        self.ingredient_id = ingredient_id
        self.name = name
        self.symbol = symbol
        self.note = note
        self.amount = amount
        self.unit = unit
        self.other = other
