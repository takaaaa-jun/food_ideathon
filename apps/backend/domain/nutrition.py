class NutritionItem:
    def __init__(
        self,
        nutrient: str,
        value: float,
    ) -> None:
        self.nutrient = nutrient
        self.value = value


class Nutrition:
    def __init__(
        self,
        nutrition_id: int,
        nutrition_name: str,
        energy: NutritionItem,
        protein: NutritionItem,
        fat: NutritionItem,
        carbs: NutritionItem,
        fiber: NutritionItem,
        salt: NutritionItem,
    ) -> None:
        self.nutrition_id = nutrition_id
        self.nutrition_name = nutrition_name
        self.energy = energy
        self.protein = protein
        self.fat = fat
        self.carbs = carbs
        self.fiber = fiber
        self.salt = salt
