from .ingredient_group import IngredientGroup


class IngredientTag:
    def __init__(
        self,
        tag_id: int,
        tag_name: str,
    ) -> None:
        self.tag_id = tag_id
        self.tag_name = tag_name


class StandardIngredient:
    def __init__(
        self,
        standard_ingredient_count: int,
        standard_ingredient_tag: IngredientTag,
        standard_ingredient_group: IngredientGroup,
    ) -> None:
        self.standard_ingredient_count = standard_ingredient_count
        self.standard_ingredient_tag = standard_ingredient_tag
        self.standard_ingredient_group = standard_ingredient_group
