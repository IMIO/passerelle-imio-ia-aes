import pytest
from datetime import date, timedelta

from passerelle_imio_ia_aes.utils import split_order_amount_against_balance, compute_activity_date_range, enrich_activity_items, resolve_activity_date_range_with_floor

# Cas de test pour split_order_amount_against_balance, groupés par branche métier :
#   - branche 1 (b1) : commande >= solde -> un dû reste à payer
#   - branche 2 (b2) : commande < solde, et > déjà réservé -> réserver le complément
#   - branche 3 (b3) : commande < solde, et <= déjà réservé -> rien de nouveau à réserver
#
# Les valeurs comme 4.56, 9.12, 35.10, 2.28 et 13.68 ne sont pas exactement
# représentables en float binaire (par ex. 4.56 * 100 = 455.99999999999994).
# Elles vérifient que la conversion en centimes via round(x*100) dans la
# fonction gère correctement ces imprécisions.
# Voir https://docs.python.org/3/tutorial/floatingpoint.html
split_order_amount_against_balance_cases = [
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
    split_order_amount_against_balance_cases,
)
def test_split_order_amount_against_balance(
    order_amount,
    balance_amount,
    already_reserved_balance_amount,
    expected_due,
    expected_spent,
    expected_remaining,
):
    result = split_order_amount_against_balance(order_amount, balance_amount, already_reserved_balance_amount)
    assert result["due_amount"] == expected_due
    assert result["spent_balance"] == expected_spent
    assert result["remaining_balance"] == expected_remaining


# Cas de test pour compute_activity_date_range, groupés par branche :
#   - static   : les dates fournies sont retournées telles quelles au format ISO
#   - dynamic  : les dates sont calculées à partir de date.today() + délai
#
# Les dates sont calculées avec date.today() à la collecte des tests.
# Les valeurs changent d'un jour à l'autre mais les assertions restent valides :
# l'output du test reflète exactement ce que fait la fonction en conditions réelles.
compute_activity_date_range_cases = [
    # --- Mode static ---
    pytest.param(
        "static",
        date.today() + timedelta(days=1), date.today() + timedelta(days=30),
        None, None,
        (date.today() + timedelta(days=1)).isoformat(),
        (date.today() + timedelta(days=30)).isoformat(),
        id="static_nominal",
    ),
    pytest.param(
        "static",
        date.today() + timedelta(days=1), date.today() + timedelta(days=1),
        None, None,
        (date.today() + timedelta(days=1)).isoformat(),
        (date.today() + timedelta(days=1)).isoformat(),
        id="static_start_equals_end",
    ),

    # --- Mode dynamic ---
    pytest.param(
        "dynamic",
        None, None,
        1, 30,
        (date.today() + timedelta(days=1)).isoformat(),
        (date.today() + timedelta(days=30)).isoformat(),
        id="dynamic_nominal",
    ),
    pytest.param(
        "dynamic",
        None, None,
        0, 90,
        date.today().isoformat(),
        (date.today() + timedelta(days=90)).isoformat(),
        id="dynamic_start_delay_zero",
    ),
    pytest.param(
        "dynamic",
        None, None,
        5, 5,
        (date.today() + timedelta(days=5)).isoformat(),
        (date.today() + timedelta(days=5)).isoformat(),
        id="dynamic_start_equals_end",
    ),
]


@pytest.mark.parametrize(
    "selection_mode,start_date,end_date,start_delay,end_delay,expected_start,expected_end",
    compute_activity_date_range_cases,
)
def test_compute_activity_date_range(
    selection_mode, start_date, end_date, start_delay, end_delay, expected_start, expected_end,
):
    result = compute_activity_date_range(
        selection_mode=selection_mode,
        start_date=start_date,
        end_date=end_date,
        start_delay=start_delay,
        end_delay=end_delay,
    )
    assert result["start_date"] == expected_start
    assert result["end_date"] == expected_end


# Cas qui doivent lever une ValueError :
#   - selection_mode invalide
#   - start_date > end_date en mode static
#   - start_delay > end_delay en mode dynamic
compute_activity_date_range_raises_cases = [
    pytest.param(
        "foo", None, None, None, None,
        id="invalid_selection_mode",
    ),
    pytest.param(
        "static",
        date.today() + timedelta(days=30), date.today() + timedelta(days=1),
        None, None,
        id="static_start_after_end",
    ),
    pytest.param(
        "dynamic", None, None, 30, 1,
        id="dynamic_start_delay_above_end_delay",
    ),
]


@pytest.mark.parametrize(
    "selection_mode,start_date,end_date,start_delay,end_delay",
    compute_activity_date_range_raises_cases,
)
def test_compute_activity_date_range_raises(
    selection_mode, start_date, end_date, start_delay, end_delay,
):
    with pytest.raises(ValueError):
        compute_activity_date_range(
            selection_mode=selection_mode,
            start_date=start_date,
            end_date=end_date,
            start_delay=start_delay,
            end_delay=end_delay,
        )


# ──────────────────────────────────────────────
# resolve_activity_date_range_with_floor
# ──────────────────────────────────────────────

# Sans mock de datetime.now(), les deux branches du plancher horaire sont
# couvertes via no_later_than :
#   - "23:59" → heure courante < limite : effective_start = floor_date
#   - "00:00" → heure courante >= limite (toujours vrai) : effective_start = floor_date + 1 jour
# Les dates attendues sont calculées à la collecte des tests (même logique que
# compute_activity_date_range_cases ci-dessus).
resolve_activity_date_range_with_floor_cases = [
    # --- Mode dynamic, heure < limite (no_later_than="23:59") ---
    pytest.param(
        "dynamic", None, None, 1, 30, "23:59",
        {"start_date": (date.today() + timedelta(days=1)).isoformat(), "end_date": (date.today() + timedelta(days=30)).isoformat()},
        id="dynamic_before_limit_delay_one",
    ),
    pytest.param(
        "dynamic", None, None, 0, 30, "23:59",
        {"start_date": date.today().isoformat(), "end_date": (date.today() + timedelta(days=30)).isoformat()},
        id="dynamic_before_limit_delay_zero",
    ),

    # --- Mode dynamic, heure >= limite (no_later_than="00:00") ---
    pytest.param(
        "dynamic", None, None, 1, 30, "00:00",
        {"start_date": (date.today() + timedelta(days=2)).isoformat(), "end_date": (date.today() + timedelta(days=30)).isoformat()},
        id="dynamic_past_limit_delay_one",
    ),
    pytest.param(
        "dynamic", None, None, 0, 30, "00:00",
        {"start_date": (date.today() + timedelta(days=1)).isoformat(), "end_date": (date.today() + timedelta(days=30)).isoformat()},
        id="dynamic_past_limit_delay_zero",
    ),

    # --- Mode dynamic, période vide après plancher → None ---
    pytest.param(
        "dynamic", None, None, 0, 0, "00:00",
        None,
        id="dynamic_empty_period_after_floor",
    ),

    # --- Mode static, date début future (plancher = start_date configurée) ---
    pytest.param(
        "static",
        (date.today() + timedelta(days=10)).isoformat(), (date.today() + timedelta(days=30)).isoformat(),
        None, None, "23:59",
        {"start_date": (date.today() + timedelta(days=10)).isoformat(), "end_date": (date.today() + timedelta(days=30)).isoformat()},
        id="static_future_start_before_limit",
    ),
    pytest.param(
        "static",
        (date.today() + timedelta(days=10)).isoformat(), (date.today() + timedelta(days=30)).isoformat(),
        None, None, "00:00",
        {"start_date": (date.today() + timedelta(days=11)).isoformat(), "end_date": (date.today() + timedelta(days=30)).isoformat()},
        id="static_future_start_past_limit",
    ),

    # --- Mode static, date début passée (plancher = aujourd'hui) ---
    pytest.param(
        "static",
        (date.today() - timedelta(days=5)).isoformat(), (date.today() + timedelta(days=30)).isoformat(),
        None, None, "23:59",
        {"start_date": date.today().isoformat(), "end_date": (date.today() + timedelta(days=30)).isoformat()},
        id="static_past_start_before_limit",
    ),
    pytest.param(
        "static",
        (date.today() - timedelta(days=5)).isoformat(), (date.today() + timedelta(days=30)).isoformat(),
        None, None, "00:00",
        {"start_date": (date.today() + timedelta(days=1)).isoformat(), "end_date": (date.today() + timedelta(days=30)).isoformat()},
        id="static_past_start_past_limit",
    ),

    # --- Mode static, période vide après plancher → None ---
    pytest.param(
        "static",
        date.today().isoformat(), date.today().isoformat(),
        None, None, "00:00",
        None,
        id="static_empty_period_after_floor",
    ),
]


@pytest.mark.parametrize(
    "selection_mode,start_date,end_date,start_delay,end_delay,no_later_than,expected",
    resolve_activity_date_range_with_floor_cases,
)
def test_resolve_activity_date_range_with_floor(
    selection_mode, start_date, end_date, start_delay, end_delay, no_later_than, expected,
):
    result = resolve_activity_date_range_with_floor(
        selection_mode=selection_mode,
        start_date=start_date,
        end_date=end_date,
        start_delay=start_delay,
        end_delay=end_delay,
        no_later_than=no_later_than,
    )
    assert result == expected


# ──────────────────────────────────────────────
# enrich_activity_items
# ──────────────────────────────────────────────

def make_item(**overrides):
    """Item minimal calqué sur la structure réelle retournée par l'API AES.

    activity_date_id est volontairement absent : les données réelles ne le
    contiennent pas, si bien que l'id est toujours construit avec item['date'].
    """
    item = {
        "child_lastname": "AYADI",
        "child_firstname": "Emma",
        "is_child_already_registered": False,
        "invoiceable_parent_id": 279,
        "activity_id": 17,
        "child_id": 280,
        "date": "2026-06-24",
    }
    item.update(overrides)
    return item


def test_enrich_activity_items_empty_list():
    assert enrich_activity_items([]) == []


def test_enrich_activity_items_returns_same_list():
    # la fonction mute les items et retourne la même liste (pas une copie)
    items = [make_item()]
    assert enrich_activity_items(items) is items


def test_enrich_activity_items_text():
    item = make_item(child_lastname="AYADI", child_firstname="Emma")
    enrich_activity_items([item])
    assert item["text"] == "AYADI Emma"


# --- disabled ---
# disabled vaut True si is_child_already_registered OU si invoiceable_parent_id est falsy
enrich_disabled_cases = [
    pytest.param(True,  279,  True,  id="already_registered"),
    pytest.param(False, None, True,  id="no_invoiceable_parent"),
    pytest.param(True,  None, True,  id="both_conditions"),
    pytest.param(False, 279,  False, id="not_disabled"),
]

@pytest.mark.parametrize("is_registered,invoiceable_parent_id,expected", enrich_disabled_cases)
def test_enrich_activity_items_disabled(is_registered, invoiceable_parent_id, expected):
    item = make_item(is_child_already_registered=is_registered, invoiceable_parent_id=invoiceable_parent_id)
    enrich_activity_items([item])
    assert item["disabled"] == expected


# --- id ---
# Format nominal : activity_id_date_child_id (activity_date_id absent dans les données réelles)
# Format avec activity_date_id : activity_id_activity_date_id_child_id (cas exceptionnel)

def test_enrich_activity_items_id_nominal():
    item = make_item(activity_id=17, child_id=280, date="2026-06-24")
    enrich_activity_items([item])
    assert item["id"] == "17_2026-06-24_280"


def test_enrich_activity_items_id_with_activity_date_id():
    # activity_date_id truthy → utilisé à la place de la date
    item = make_item(activity_id=17, child_id=280)
    item["activity_date_id"] = 42
    enrich_activity_items([item])
    assert item["id"] == "17_42_280"


# --- group_by ---
# Format : "<Jour> <numéro> <mois> <année>" avec première lettre en majuscule.
# Le numéro de jour n'est pas zéro-padé ("1" et non "01").
enrich_group_by_cases = [
    pytest.param("2026-06-24", "Mercredi 24 juin 2026",   id="wednesday_june"),
    pytest.param("2026-07-01", "Mercredi 1 juillet 2026", id="wednesday_july_no_zero_pad"),
    pytest.param("2025-12-25", "Jeudi 25 décembre 2025",  id="thursday_december"),
]

@pytest.mark.parametrize("date_str,expected_group_by", enrich_group_by_cases)
def test_enrich_activity_items_group_by(date_str, expected_group_by):
    item = make_item(date=date_str)
    enrich_activity_items([item])
    assert item["group_by"] == expected_group_by


# --- plusieurs items ---
def test_enrich_activity_items_multiple():
    items = [
        make_item(child_lastname="AYADI",        child_firstname="Emma", activity_id=17,  child_id=280),
        make_item(child_lastname="DE KELLIWIC'H", child_firstname="Eddy", activity_id=17, child_id=188),
    ]
    result = enrich_activity_items(items)
    assert len(result) == 2
    assert result[0]["text"] == "AYADI Emma"
    assert result[1]["text"] == "DE KELLIWIC'H Eddy"
