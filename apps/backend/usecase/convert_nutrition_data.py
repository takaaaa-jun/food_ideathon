from apps.backend.domain.nutrition import Nutrition
from apps.backend.domain.ingredient_group import IngredientGroup

def convert_nutrition_data(
    record: RawNutiritionRecord
    ) -> tuple[Nutrition, IngredientGroup]:
    group = IngredientGroup(
        group_id = record.group,
        group_name = group_name,
    )
    
    nutrition = Nutrition(
        nutrition_id = record.id,
        nutrition_name = record.name
        energy = NutiritionItem("energy", record.ENERC_KCAL)
        
    )