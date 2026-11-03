"""Synthetic reviewed revision with intentionally defective boundaries."""
LIMIT = 100


def charge(amount, effects):
    effects.append(amount)


def fetch_item(actor_tenant, item_tenant):
    return "item"


def policy(value):
    if value != "allow":
        raise ValueError("unknown policy")
    return True
