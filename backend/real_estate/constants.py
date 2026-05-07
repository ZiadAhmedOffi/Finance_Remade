from decimal import Decimal

# Scenario Adjustments as defined in PLAN.md
SCENARIO_ADJUSTMENTS = {
    "BASE": {
        "appreciation": Decimal("0.00"),
        "rental_growth": Decimal("0.00"),
        "vacancy": Decimal("0.00"),
        "interest_rate": Decimal("0.00"),
    },
    "BULL": {
        "appreciation": Decimal("2.00"),
        "rental_growth": Decimal("1.00"),
        "vacancy": Decimal("-2.00"),
        "interest_rate": Decimal("-0.50"),
    },
    "BEAR": {
        "appreciation": Decimal("-2.00"),
        "rental_growth": Decimal("-1.00"),
        "vacancy": Decimal("3.00"),
        "interest_rate": Decimal("1.00"),
    }
}
