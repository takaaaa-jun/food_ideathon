from apps.backend.domain.ingredient_group import IngredientGroup
from apps.backend.infrastructure.database.raw_ingredient_group_record import (
    RawIngredientGroupRecord,
)


def convert_ingredient_group_data(
    record: RawIngredientGroupRecord,
) -> IngredientGroup:

    ingredient_group = IngredientGroup(
        food_id=record.food_id,
        group_id=record.group_id,
        group_name=record.group_name,
    )
    return ingredient_group
