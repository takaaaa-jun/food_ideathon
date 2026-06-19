class RawNutritionRecord:
    def __init__(
        self,
        id: int,
        name: str,
        group_id: int,
        group_name: str,
        ENERC_KCAL: float,
        PROT: float,
        FAT: float,
        CHOAVLDF: float,
        FIB: float,
        NACL_EQ: float,
    ) -> None:
        self.id = id
        self.name = name
        self.group_id = group_id
        self.group_name = group_name
        self.energy = ENERC_KCAL
        self.protein = PROT
        self.fat = FAT
        self.carbs = CHOAVLDF
        self.fiber = FIB
        self.salt = NACL_EQ
