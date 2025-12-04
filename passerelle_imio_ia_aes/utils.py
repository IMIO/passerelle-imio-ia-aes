
def compute_amount_with_balance(order_amount, total_balance_amount, unreserved_balance_amount, already_reserved_balance_amount):
    # Si le montant de la commande est inférieur au solde déjà réservé,
    # alors le parent n'a rien à payer 
    # et qu'il n'y a pas besoin de réserver du solde
    if order_amount <= already_reserved_balance_amount:
        due_amount = 0
        spent_balance = 0
    # Sinon si le montant de la commande est supérieur au montant déjà réservé
    # et que le montant de la commande est inférieur au montant total du solde,
    # alors le parent n'a toujours rien à payer
    # et la différence entre le montant de la commande et le solde déjà réservé doit être réservé
    elif order_amount > already_reserved_balance_amount and order_amount < total_balance_amount:
        due_amount = 0
        spent_balance = order_amount - already_reserved_balance_amount
    # Sinon si le montant de la commande est supérieur au montant de la commande est supérieur au solde total,
    # alors le parent doit payer la différence entre le montant de la commande et le montant du solde réservé
    # et le solde non réservé doit être réservé.
    elif order_amount >= total_balance_amount:
        due_amount = order_amount - total_balance_amount
        spent_balance = unreserved_balance_amount
    return {"due_amount": due_amount, "spent_balance": spent_balance}