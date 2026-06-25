from apps.backend.domain.nutrition import Nutrition, NutritionItem
from apps.backend.infrastructure.database.raw_nutrition_record import RawNutritionRecord


def convert_nutrition_data(
    record: RawNutritionRecord,
) -> Nutrition:

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
