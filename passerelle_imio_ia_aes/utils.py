from datetime import date
from datetime import timedelta
from typing import Literal

def compute_amount_with_balance(order_amount, balance_amount, already_reserved_balance_amount):
    # Arrondir...
    order_amount = round(order_amount * 100)
    balance_amount = round(balance_amount * 100)
    already_reserved_balance_amount = round(already_reserved_balance_amount * 100)
    due_amount = 0
    spent_balance = 0
    remaining_balance = 0
    # Si le montant de la commande est supérieur ou égal au montant du solde...
    if order_amount >= balance_amount:
        # ... le montant à payer est le montant de la commande moins le montant du solde...
        due_amount = order_amount - balance_amount
        # ... le solde à réserver est le montant de la balance moins le montant déjà réserver...
        spent_balance = balance_amount - already_reserved_balance_amount
        # ... il ne reste plus de solde
        remaining_balance = 0
    # Sinon (si le montant de la commande est inférieur au montant du solde)...
    else:
        # ... le montant à payé est nul
        due_amount = 0
        remaining_balance = balance_amount - order_amount
        # ... si le montant de la commande est supérieur au montant du solde déjà réservé...
        if order_amount > already_reserved_balance_amount:
            # ... le montant à réserver est le montant de la commande moins le montant du solde déjà réservé
            spent_balance = order_amount - already_reserved_balance_amount
        # ... sinon (si le montant de la commande est inférieur ou égal au montant du solde déjà réservé)
        else:
            spent_balance = 0
    # Retourner les résultats, avec les bonnes valeurs
    return {"due_amount": round(due_amount / 100, 2), "spent_balance": round(spent_balance / 100, 2), "remaining_balance": round(remaining_balance / 100, 2)}


def compute_generic_activity_parameters(
        selection_mode: Literal["static", "dynamic"] = "dynamic",
        start_date: date | None = None,
        end_date: date | None = None,
        start_delay: int | None = None,
        end_delay: int | None = None
    ) -> dict[str, str]:
    """Détermine les dates de début et fin pour filtrer les activités.

    Requires:
        si selection_mode == static → start_date <= end_date and start_date >= date.today()
        si selection_mode == dynamic → start_delay <= end_delay and start_delay >= 0

    Args:
        selection_mode: choix entre une période fixe (static) ou dynamique (dynamic)
        start_date: date de début de la période fixe
        end_date: date de fin de la période fixe
        start_delay: début de la période dynamique
        end_delay: fin de la période dynamique

    Raises:
        ValueError: Si selection_mode n'est ni "static", ni "dynamic" ou si la start_date calculée
            est plus lointaine que la end_date calculée

    Returns:
        Un dictionnaire contenant les clés "start_date" et "end_date" dont les valeurs sont des
            dates au format ISO (YYYY-MM-DD).
    """
    if selection_mode not in ("static", "dynamic"):
        raise ValueError(f"selection_mode must be 'static' or 'dynamic', got '{selection_mode}'")
    if selection_mode == "dynamic":
        today = date.today()
        start_date = today + timedelta(days=start_delay)
        end_date = today + timedelta(days=end_delay)
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
