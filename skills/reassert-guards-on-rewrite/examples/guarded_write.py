"""Synthetic teaching example; deliberately unsafe variants are not recipes.

Run with Python 3. The recorder stands in for a protected write. A real test
must observe the consumer's actual effect, not just an exception or return code.
"""


def original(channel, actor_tenant, item_tenant, effects):
    if actor_tenant != item_tenant:
        raise PermissionError("tenant mismatch")
    effects.append((channel, item_tenant))


def dropped(channel, actor_tenant, item_tenant, effects):
    effects.append((channel, item_tenant))


def unsafe_move(channel, actor_tenant, item_tenant, effects):
    effects.append((channel, item_tenant))
    if actor_tenant != item_tenant:
        raise PermissionError("tenant mismatch")


def tenant_wrapper(action, actor_tenant, item_tenant):
    if actor_tenant != item_tenant:
        raise PermissionError("tenant mismatch")
    action()


def safe_move(channel, actor_tenant, item_tenant, effects):
    # Both supported entry paths reach the wrapper before their effect.
    if channel not in ("api", "batch"):
        raise ValueError("unknown entry point")
    tenant_wrapper(lambda: effects.append((channel, item_tenant)),
                   actor_tenant, item_tenant)


def demonstrate():
    for candidate in (original, dropped, unsafe_move, safe_move):
        for channel in ("api", "batch"):
            allowed = []
            candidate(channel, "tenant-a", "tenant-a", allowed)
            assert allowed == [(channel, "tenant-a")]
            denied, effects = False, []
            try:
                candidate(channel, "tenant-a", "tenant-b", effects)
            except PermissionError:
                denied = True
            binding = denied and not effects
            assert binding == (candidate in (original, safe_move))
            print(f"{candidate.__name__}/{channel}: denial-before-effect={binding}")


if __name__ == "__main__":
    demonstrate()
