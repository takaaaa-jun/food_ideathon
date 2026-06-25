class RawNutritionRecord:
    def __init__(
        self,
        food_id: int,
        food_name: str,
        energy: float,
        protein: float,
        fat: float,
        carbs: float,
        fib: float,
        salt: float,
    ) -> None:
        self.food_id = food_id
        self.food_name = food_name
        self.energy = energy
        self.protein = protein
        self.fat = fat
        self.carbs = carbs
        self.fiber = fib
        self.salt = salt
