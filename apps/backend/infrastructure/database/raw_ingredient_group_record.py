class RawIngredientGroupRecord:
    def __init__(
        self,
        nutrition_id: int,
        group_id: int,
        group_name: str,
    ) -> None:
        self.nutrition_id = nutrition_id
        self.group_id = group_id
        self.group_name = group_name
