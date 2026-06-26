from .ingredient import Ingredient
from .step import Step


class RecipePublishedAt:
    def __init__(
        self,
        recipe_published_at_year: int,
        recipe_published_at_month: int,
        recipe_published_at_day: int,
    ) -> None:
        self.recipe_published_at_year = recipe_published_at_year
        self.recipe_published_at_month = recipe_published_at_month
        self.recipe_published_at_day = recipe_published_at_day


class RecipeServing:
    def __init__(
        self,
        recipe_serving_text: str,
        recipe_serving_count: int,
    ) -> None:
        self.recipe_serving_text = recipe_serving_text
        self.recipe_serving_count = recipe_serving_count


class Recipe:
    def __init__(
        self,
        recipe_id: int,
        recipe_attribute: str,
        recipe_title: str,
        recipe_description: str | None,
        recipe_ingredient: list[Ingredient],
        recipe_step: list[Step],
        recipe_cooking_time: str | None,
        recipe_serving: RecipeServing,
        recipe_published_at: RecipePublishedAt,
    ) -> None:
        self.recipe_id = recipe_id
        self.recipe_attribute = recipe_attribute
        self.recipe_title = recipe_title
        self.recipe_description = recipe_description
        self.recipe_ingredient = recipe_ingredient
        self.recipe_step = recipe_step
        self.recipe_cooking_time = recipe_cooking_time
        self.recipe_serving = recipe_serving
        self.recipe_published_at = recipe_published_at
