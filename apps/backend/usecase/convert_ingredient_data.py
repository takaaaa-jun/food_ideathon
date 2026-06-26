from apps.backend.domain.ingredient import Ingredient
from apps.backend.infrastructure.database.raw_ingredient_record import RawIngredientRecord

def convert_ingredient_data(
    record: RawIngredientRecord,
) -> Ingredient:
    
    ingredient = Ingredient(
        ingredient_id=record.ingredient_id,
        recipe_id=record.recipe_id,
        ingredient_name=record.ingredient_name,
        ingredient_quantity=record.ingredient_quantity,
    )
    return ingredient