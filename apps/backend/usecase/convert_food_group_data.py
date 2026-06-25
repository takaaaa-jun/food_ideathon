from apps.backend.domain.food_group import FoodGroup
from apps.backend.infrastructure.database.raw_food_group_record import (
    RawFoodGroupRecord,
)


def convert_food_group_data(
    record: RawFoodGroupRecord,
) -> FoodGroup:

    food_group = FoodGroup(
        food_id=record.food_id,
        group_id=record.group_id,
        group_name=record.group_name,
    )
    return food_group
