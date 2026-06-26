from apps.backend.domain.ingredient_detail import IngredientDetail
from apps.backend.infrastructure.database.raw_ingredient_structure_record import RawIngredientStructureRecord
from apps.backend.infrastructure.database.raw_ingredient_unit_record import RawIngredientUnitRecord

def convert_ingredient_detail_data(
    structure_record: RawIngredientStructureRecord,
    unit_record: RawIngredientUnitRecord,
) -> IngredientDetail:
    
    ingredient_detail = IngredientDetail(
        ingredient_detail_id=structure_record.ingredient_structure_id,
        ingredient_id=structure_record.ingredient_id,
        ingredient_detail_name=structure_record.ingredient_detail_name,
        ingredient_detail_symbol=structure_record.ingredient_detail_symbol,
        ingredient_detail_supplement=structure_record.ingredient_detail_supplement,
        ingredient_detail_normalized_name=structure_record.ingredient_detail_normalized_name,
        ingredient_detail_amount=unit_record.ingredient_detail_amount,
        ingredient_detail_unit=unit_record.ingredient_detail_unit,
        ingredient_detail_normalized_quantity=unit_record.ingredient_detail_normalized_quantity,
    )
    return ingredient_detail