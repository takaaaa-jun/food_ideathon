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


class Recipe:
    def __init__(
        self,
        recipe_id: int,
        recipe_title: str,
        recipe_description: str | None,
        recipe_ingredient: list[Ingredient],
        resipe_step: list[Step],
        recipe_cooking_time: str | None,
        recipe_published_at: RecipePublishedAt,
    ) -> None:
        self.recipe_id = recipe_id
        self.recipe_title = recipe_title
        self.recipe_description = recipe_description
        self.recipe_ingredient = recipe_ingredient
        self.resipe_step = resipe_step
        self.recipe_cooking_time = recipe_cooking_time
        self.recipe_published_at = recipe_published_at
