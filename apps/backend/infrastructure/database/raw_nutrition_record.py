class RawNutritionRecord:
    def __init__(
        self,
        nutrition_id: int,
        nutrition_name: str,
        group_id: int,
        group_name: str,
        ENERC_KCAL: float,
        PROT: float,
        FAT: float,
        CHOAVLDF: float,
        FIB: float,
        NACL_EQ: float,
    ) -> None:
        self.nutrition_nutrition_id = nutrition_id
        self.nutrition_nutrition_name = nutrition_name
        self.group_id = group_id
        self.group_name = group_name
        self.energy = ENERC_KCAL
        self.protein = PROT
        self.fat = FAT
        self.carbs = CHOAVLDF
        self.fiber = FIB
        self.salt = NACL_EQ
