from apps.backend.domain.nutrition import Nutrition, NutritionItem
from apps.backend.infrastructure.database.raw_nutrition_record import RawNutritionRecord


def convert_nutrition_data(
    record: RawNutritionRecord,
) -> Nutrition:

    nutrition = Nutrition(
        food_id=record.food_id,
        food_name=record.food_name,
        energy=NutritionItem("energy", record.energy),
        protein=NutritionItem("protein", record.protein),
        fat=NutritionItem("fat", record.fat),
        carbs=NutritionItem("carbs", record.carbs),
        fiber=NutritionItem("fiber", record.fiber),
        salt=NutritionItem("salt", record.salt),
    )
    return nutrition
