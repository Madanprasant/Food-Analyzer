# Nutrition data pipeline

## Source and coverage

The seed at `backend/data/platesignal_nutrition_seed.json` contains all 239 PLATESIGNAL model classes.

- 36 records are `verified` direct IFCT foods.
- 87 recipe/composite mappings have no documented ingredient quantities yet and remain `nutrition_pending`.
- 116 foods require a suitable secondary source and remain `nutrition_pending`.

The mapping file has one documented classification difference: it marks **turnip** as a usable direct match while the supplied nutrition seed marks it `SECONDARY_SOURCE_REQUIRED`. The import follows the supplied nutrition seed, so turnip remains pending until a reviewed source decision resolves4 the discrepancy.

Direct records cite **ICMR-NIN Indian Food Composition Tables (IFCT) 2017**, the supplied machine-readable IFCT index, and their IFCT food code. The seed’s source energy is retained as `energy_kj`. The interface displays kcal only as the deterministic conversion `kJ / 4.184`, recorded in `calculationMethod`.
## MongoDB nutrition record


`nutritionFoods` holds one record per model class. Important fields are:

```text
modelClass, canonicalFood, aliases, status, source, sourceReference,
sourceFoodCode, nutritionBasis, servingSizeG, nutrients, micronutrients,
recipeComponents, confidence, notes, calculationMethod
```

Pending records contain null nutrients—not zeros.

## Import and validation

From `backend`:

```powershell
python scripts/validate_nutrition_seed.py
python scripts/import_nutrition_seed.py
```

The import is idempotent and uses `modelClass` as its unique key.

## Serving calculation

Verified IFCT entries are stored per 100 g. Because the supplied seed provides no defensible prepared serving sizes, the user enters grams. The service calculates each shown nutrient as:

```text
per-serving nutrient = per-100g nutrient × grams / 100
```

Composite and secondary-source foods continue to display nutrition pending until documented source data is imported.

## Meal history and aggregates

At confirmation, the system saves a nutrition snapshot, source, serving grams, and deterministic Meal Balance Score when nutrition is available. Daily and weekly totals aggregate only saved snapshots. Pending meals are counted as unavailable rather than assumed to be zero.

## Meal Balance Score

`meal-balance-v1` is a transparent rule-based support score, not a medical assessment. It checks the meal’s share of daily calories, share of daily protein target when configured, and the 4 g fiber support threshold. It returns `insufficient_data` when sourced meal nutrition or a calorie target is unavailable.
