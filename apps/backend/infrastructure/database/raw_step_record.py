class RawStepRecord:
    def __init__(
        self,
        step_id: int
        recipe_id: int
        step_position_id: int
        step_text: str,
    ) -> None:
        self.step_id = step_id
        self.recipe_id = recipe_id
        self.step_position_id = step_position_id
        self.step_text = step_text