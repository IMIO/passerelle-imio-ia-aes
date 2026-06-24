from datetime import date, datetime, time, timedelta
from typing import Literal

JOURS = ('lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche')
MOIS = ('janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre')

def split_order_amount_against_balance(order_amount, balance_amount, already_reserved_balance_amount):
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


def compute_activity_date_range(
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


def resolve_activity_date_range_with_floor(
        selection_mode: Literal["static", "dynamic"] = "dynamic",
        start_date: str | None = None,
        end_date: str | None = None,
        start_delay: int | None = None,
        end_delay: int | None = None,
        no_later_than: str = "23:59",
    ) -> dict[str, str] | None:
    """Calcule la période effective en appliquant le plancher horaire.

    Le plancher garantit qu'on ne propose jamais une date déjà passée par rapport
    à l'heure limite : si l'heure actuelle >= no_later_than, la date de début
    effective est avancée d'un jour.

    Returns:
        Dict avec 'start_date' et 'end_date' au format ISO, ou None si la période
        résultante est vide (effective_start > end_date).
    """
    now = datetime.now()
    period = compute_activity_date_range(
        selection_mode=selection_mode,
        start_date=None if start_date is None else date.fromisoformat(start_date),
        end_date=None if end_date is None else date.fromisoformat(end_date),
        start_delay=None if start_delay is None else int(start_delay),
        end_delay=None if end_delay is None else int(end_delay),
    )
    limit_time = time.fromisoformat(no_later_than)
    floor_date = max(date.fromisoformat(period['start_date']), date.today())
    effective_start = floor_date + timedelta(days=1) if now.time() >= limit_time else floor_date
    if effective_start > date.fromisoformat(period['end_date']):
        return None
    return {"start_date": effective_start.isoformat(), "end_date": period['end_date']}


def enrich_activity_items(items: list) -> list:
    """Enrichit les items d'activité pour leur utilisation dans un formulaire.

    Ajoute les champs text, disabled, id et group_by à chaque item.
    """
    for item in items:
        item['text'] = f"{item['child_lastname']} {item['child_firstname']}"
        item['disabled'] = item.get('is_child_already_registered') or not item.get('invoiceable_parent_id')
        item['id'] = f"{item['activity_id']}_{item.get('activity_date_id') or item['date']}_{item['child_id']}"
        d = date.fromisoformat(item['date'])
        item['group_by'] = f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year}".capitalize()
    return items
