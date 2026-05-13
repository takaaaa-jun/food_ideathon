class Nutrition:
    def __init__(
        self,
        nutrition_id: int,
        nutrition_name: str,
        energy_name: str,
        energy_value: float,
        protein_name: str,
        protein_value: float,
        fat_name: str,
        fat_value: float,
        carbs_name: str,
        carbs_value: float,
        fiber_name: str,
        fiber_value: float,
        salt_name: str,
        salt_value: float,
    ) -> None:
        self.nutrition_id = nutrition_id
        self.nutrition_name = nutrition_name
        self.energy_name = energy_name
        self.energy_value = energy_value
        self.protein_name = protein_name
        self.protein_value = protein_value
        self.fat_name = fat_name
        self.fat_value = fat_value
        self.carbs_name = carbs_name
        self.carbs_value = carbs_value
        self.fiber_name = fiber_name
        self.fiber_value = fiber_value
        self.salt_name = salt_name
        self.salt_value = salt_value
