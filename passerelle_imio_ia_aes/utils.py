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

