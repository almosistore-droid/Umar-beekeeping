"""Russian labels used in server-built texts (timeline summaries, reminder titles)."""
from app.models.enums import (
    DiseaseCaseStatus,
    DiseaseSeverity,
    FamilyStrength,
    FeedType,
    FeedUnit,
    FoodLevel,
    HiveStatus,
    InspectionHealth,
)

STRENGTH = {
    FamilyStrength.VERY_WEAK: "очень слабая", FamilyStrength.WEAK: "слабая", FamilyStrength.MEDIUM: "средняя",
    FamilyStrength.STRONG: "сильная", FamilyStrength.VERY_STRONG: "очень сильная",
}
FEED_TYPE = {
    FeedType.SUGAR_SYRUP: "Сахарный сироп", FeedType.CANDY: "Канди", FeedType.HONEY: "Мёд",
    FeedType.PROTEIN: "Белковая подкормка", FeedType.POLLEN_SUBSTITUTE: "Заменитель перги",
    FeedType.MEDICATED: "Лечебная подкормка", FeedType.OTHER: "Другое",
}
FEED_UNIT = {FeedUnit.KG: "кг", FeedUnit.G: "г", FeedUnit.L: "л", FeedUnit.ML: "мл", FeedUnit.PCS: "шт"}
FOOD_LEVEL = {FoodLevel.CRITICAL: "критически мало", FoodLevel.LOW: "мало", FoodLevel.NORMAL: "достаточно",
              FoodLevel.ABUNDANT: "много"}
HEALTH = {InspectionHealth.HEALTHY: "здорова", InspectionHealth.SUSPICIOUS: "есть подозрения",
          InspectionHealth.SICK: "болеет"}
SEVERITY = {DiseaseSeverity.LIGHT: "лёгкая", DiseaseSeverity.MODERATE: "средняя", DiseaseSeverity.SEVERE: "тяжёлая"}
CASE_STATUS = {DiseaseCaseStatus.SUSPECTED: "подозрение", DiseaseCaseStatus.CONFIRMED: "подтверждено",
               DiseaseCaseStatus.TREATING: "лечение", DiseaseCaseStatus.RESOLVED: "вылечено"}
HIVE_STATUS = {
    HiveStatus.ACTIVE: "активный", HiveStatus.WEAK: "слабый", HiveStatus.STRONG: "сильный", HiveStatus.SICK: "болеет",
    HiveStatus.QUEENLESS: "без матки", HiveStatus.EMPTY: "пустой", HiveStatus.QUARANTINE: "карантин",
    HiveStatus.MERGED: "объединён", HiveStatus.SPLIT: "разделён", HiveStatus.SOLD: "продан", HiveStatus.LOST: "потерян",
}

# ---------- stage 6: reports ----------
from app.models.enums import ProductType  # noqa: E402

PRODUCT_TYPE = {
    ProductType.WAX: "Воск", ProductType.PROPOLIS: "Прополис", ProductType.BEE_BREAD: "Перга",
    ProductType.POLLEN: "Пыльца", ProductType.ROYAL_JELLY: "Маточное молочко", ProductType.QUEENS: "Матки",
    ProductType.COLONIES: "Пчелосемьи", ProductType.PACKAGES: "Пчелопакеты",
}
MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь",
          "Ноябрь", "Декабрь"]

# ---------- stage 7: CRM ----------
from app.models.enums import ExpenseCategory, OrderStatus, PaymentMethod, SaleCategory  # noqa: E402

EXPENSE_CATEGORY = {
    ExpenseCategory.HIVES: "Ульи", ExpenseCategory.FRAMES: "Рамки", ExpenseCategory.FOUNDATION: "Вощина",
    ExpenseCategory.FEED: "Корм", ExpenseCategory.MEDICINE: "Лекарства", ExpenseCategory.EQUIPMENT: "Оборудование",
    ExpenseCategory.TRANSPORT: "Транспорт", ExpenseCategory.FUEL: "Топливо", ExpenseCategory.QUEENS: "Матки",
    ExpenseCategory.COLONIES: "Семьи", ExpenseCategory.REPAIR: "Ремонт", ExpenseCategory.OTHER: "Другое",
}
SALE_CATEGORY = {
    SaleCategory.HONEY: "Мёд", SaleCategory.WAX: "Воск", SaleCategory.PROPOLIS: "Прополис",
    SaleCategory.BEE_BREAD: "Перга", SaleCategory.POLLEN: "Пыльца", SaleCategory.QUEENS: "Матки",
    SaleCategory.COLONIES: "Семьи", SaleCategory.PACKAGES: "Пчелопакеты", SaleCategory.OTHER: "Другое",
}
PAYMENT_METHOD = {PaymentMethod.CASH: "наличные", PaymentMethod.CARD: "карта", PaymentMethod.TRANSFER: "перевод"}
ORDER_STATUS = {OrderStatus.NEW: "новый", OrderStatus.READY: "собран", OrderStatus.DELIVERED: "выдан",
                OrderStatus.CANCELLED: "отменён"}
