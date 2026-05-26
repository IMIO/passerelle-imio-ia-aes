import pytest

from passerelle_imio_ia_aes.utils import compute_amount_with_balance

# Cas de test pour compute_amount_with_balance, groupés par branche métier :
#   - branche 1 (b1) : commande >= solde -> un dû reste à payer
#   - branche 2 (b2) : commande < solde, et > déjà réservé -> réserver le complément
#   - branche 3 (b3) : commande < solde, et <= déjà réservé -> rien de nouveau à réserver
#
# Les valeurs comme 4.56, 9.12, 35.10, 2.28 et 13.68 ne sont pas exactement
# représentables en float binaire (par ex. 4.56 * 100 = 455.99999999999994).
# Elles vérifient que la conversion en centimes via round(x*100) dans la
# fonction gère correctement ces imprécisions.
# Voir https://docs.python.org/3/tutorial/floatingpoint.html
compute_amount_with_balance_cases = [
    pytest.param(0.00, 0.00, 0.00, 0.00, 0.00, 0.00, id="zero_everything"),

    # --- Branche 1 : commande >= solde (un dû reste) ---
    pytest.param(4.56, 4.56, 2.28, 0.00, 2.28, 0.00, id="b1_order_equals_balance_partial_reserve"),
    pytest.param(9.12, 6.84, 2.28, 2.28, 4.56, 0.00, id="b1_order_above_balance_partial_reserve"),
    pytest.param(9.12, 2.28, 2.28, 6.84, 0.00, 0.00, id="b1_order_above_balance_fully_reserved"),
    pytest.param(4.56, 2.28, 0.00, 2.28, 2.28, 0.00, id="b1_order_above_balance_no_previous_reserve"),
    pytest.param(9.12, 0.00, 0.00, 9.12, 0.00, 0.00, id="b1_order_above_zero_balance"),

    # --- Branche 2 : commande < solde, et > déjà réservé (réserver le delta) ---
    pytest.param(4.56, 9.12, 2.28, 0.00, 2.28, 4.56, id="b2_covers_new_reserve"),
    pytest.param(4.56, 9.12, 0.00, 0.00, 4.56, 4.56, id="b2_no_previous_reserve"),

    # --- Branche 3 : commande < solde, et <= déjà réservé (aucune nouvelle réserve) ---
    pytest.param(2.28, 9.12, 2.28, 0.00, 0.00, 6.84, id="b3_order_equals_existing_reserve"),
    pytest.param(4.56, 13.68, 13.68, 0.00, 0.00, 9.12, id="b3_order_below_existing_reserve"),
]


@pytest.mark.parametrize(
    "order_amount,balance_amount,already_reserved_balance_amount,expected_due,expected_spent,expected_remaining",
    compute_amount_with_balance_cases,
)
def test_compute_amount_with_balance(
    order_amount,
    balance_amount,
    already_reserved_balance_amount,
    expected_due,
    expected_spent,
    expected_remaining,
):
    result = compute_amount_with_balance(order_amount, balance_amount, already_reserved_balance_amount)
    assert result["due_amount"] == expected_due
    assert result["spent_balance"] == expected_spent
    assert result["remaining_balance"] == expected_remaining
