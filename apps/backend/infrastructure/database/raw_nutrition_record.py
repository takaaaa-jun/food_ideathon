class RawNutritionRecord:
    def __init__(
        self,
        nutrition_id: int,
        nutrition_name: str,
        energy: float,
        protein: float,
        fat: float,
        carbs: float,
        fib: float,
        salt: float,
    ) -> None:
        self.nutrition_id = nutrition_id
        self.nutrition_name = nutrition_name
        self.energy = energy
        self.protein = protein
        self.fat = fat
        self.carbs = carbs
        self.fiber = fib
        self.salt = salt
