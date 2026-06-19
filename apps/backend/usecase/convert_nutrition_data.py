from apps.backend.domain.ingredient_group import IngredientGroup
from apps.backend.domain.nutrition import Nutrition, NutritionItem
from apps.backend.infrastructure.database.raw_nutrition_record import RawNutritionRecord


def convert_nutrition_data(
    record: RawNutritionRecord,
) -> tuple[Nutrition, IngredientGroup]:

    group = IngredientGroup(
        group_id=record.group_id,
        group_name=record.group_name,
    )

    nutrition = Nutrition(
        nutrition_id=record.nutrition_id,
        nutrition_name=record.nutrition_name,
        energy=NutritionItem("energy", record.energy),
        protein=NutritionItem("protein", record.protein),
        fat=NutritionItem("fat", record.fat),
        carbs=NutritionItem("carbs", record.carbs),
        fiber=NutritionItem("fiber", record.fiber),
        salt=NutritionItem("salt", record.salt),
    )
    return nutrition, group
