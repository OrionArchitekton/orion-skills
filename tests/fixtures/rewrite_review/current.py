"""Synthetic current revision; overflow remains, other protections improved."""
LIMIT = 100


def charge(amount, effects):
    if amount < 0:
        raise ValueError("negative amount")
    effects.append(amount)


def read_item(actor_tenant, item_tenant):
    if actor_tenant != item_tenant:
        raise PermissionError("tenant mismatch")
    return "item"


def policy(value):
    if value != "allow":
        raise ValueError("unknown policy")
    return True
