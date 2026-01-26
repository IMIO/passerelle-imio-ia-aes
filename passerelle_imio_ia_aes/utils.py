def compute_amount_with_balance(order_amount, balance_amount, already_reserved_balance_amount):
    # Arrondir...
    order_amount = round(order_amount * 100)
    balance_amount = round(balance_amount * 100)
    already_reserved_balance_amount = round(already_reserved_balance_amount * 100)
    due_amount = 0
    spent_balance = 0
    # Si le montant de la commande est supérieur ou égal au montant du solde...
    if order_amount >= balance_amount:
        # ... le montant à payer est le montant de la commande moins le montant du solde...
        due_amount = order_amount - balance_amount
        # ... le solde à réserver est le montant de la balance moins le montant déjà réserver.
        spent_balance = balance_amount - already_reserved_balance_amount
    # Sinon (si le montant de la commande est inférieur au montant du solde)...
    else:
        # ... le montant à payé est nul
        due_amount = 0
        # ... si le montant de la commande est supérieur au montant du solde déjà réservé...
        if order_amount > already_reserved_balance_amount:
            # ... le montant à réserver est le montant de la commande moins le montant du solde déjà réservé
            spent_balance = order_amount - already_reserved_balance_amount
        # ... sinon (si le montant de la commande est inférieur ou égal au montant du solde déjà réservé)
        else:
            spent_balance = 0
    # Retourner les résultats, avec les bonnes valeurs
    return {"due_amount": round(due_amount / 100, 2), "spent_balance": round(spent_balance / 100, 2)}

test_compute_amount_with_balance_compute_dataset = [
    # order_amount, balance_amount, already_reserved_balance_amount
    (0.00, 0.00, 0.00, 0.00, 0.00),
    (10.50, 10.50, 10.50, 0.00, 0.00),
    (20.75, 30.00, 20.00, 0.00, 0.75),
    (35.10, 40.00, 30.00, 0.00, 5.10),
    (50.25, 70.00, 50.00, 0.00, 0.25),
    (100.00, 100.00, 0.00, 0.00, 100.00),
    (5.00, 10.00, 5.00, 0.00, 0.00),
    (10.00, 5.00, 5.00, 5.00, 0.00),
    (10.00, 5.00, 0.00, 5.00, 5.00),
    (10.00, 5.00, 2.50, 5.00, 2.50),
    (4.56, 4.56, 2.28, 0.00, 2.28),
    (9.12, 2.28, 2.28, 6.84, 0.00),
    (9.12, 2.28, 0.00, 6.84, 2.28),
    (9.12, 0.00, 0.00, 9.12, 0.00),
    (9.12, 6.84, 2.28, 2.28, 4.56),
]

def test_compute_amount_with_balance(dataset=test_compute_amount_with_balance_compute_dataset):
    result = True
    tests = []
    for i in range(0, len(dataset)):
        computed = compute_amount_with_balance(dataset[i][0], dataset[i][1], dataset[i][2])
        line_result = True
        detail = f"Order amount: {computed['due_amount']}/{dataset[i][3]}, Spent balance: {computed['spent_balance']}/{dataset[i][4]}"
        if computed["due_amount"] != dataset[i][3] or computed["spent_balance"] != dataset[i][4]:
            result = False
            line_result = False
        tests.append(
            {
                "line_result": line_result,
                "detail": detail,
                "parameters": {
                    "order_amount": dataset[i][0],
                    "balance_amount": dataset[i][1],
                    "already_reserved_balance_amount": dataset[i][2]
                },
                "due_amount": {
                    "expected": dataset[i][3],
                    "obtained": computed["due_amount"],
                },
                "results": {
                    "expected": dataset[i][4],
                    "obtained": computed["spent_balance"]
                }
            }
        )
    return {"result": result, "tests": tests}