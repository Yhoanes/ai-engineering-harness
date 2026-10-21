from engine.execution.models import AccessMode, ScopedAccess


def normalize_access_scope(raw_value: list[str] | dict | None) -> ScopedAccess:
    if raw_value is None:
        return ScopedAccess(AccessMode.DENY_ALL, frozenset())

    if isinstance(raw_value, list):
        if not raw_value:
            return ScopedAccess(AccessMode.DENY_ALL, frozenset())
        return ScopedAccess(AccessMode.ALLOW_LIST, frozenset(raw_value))

    if isinstance(raw_value, dict):
        mode_str = raw_value.get("mode")

        if mode_str == "deny_all":
            if "values" in raw_value:
                raise ValueError("deny_all mode does not accept values")
            return ScopedAccess(AccessMode.DENY_ALL, frozenset())

        elif mode_str == "unrestricted":
            if "values" in raw_value:
                raise ValueError("unrestricted mode does not accept values")
            return ScopedAccess(AccessMode.UNRESTRICTED, frozenset())

        elif mode_str == "allow_list":
            if "values" not in raw_value:
                raise ValueError("allow_list mode requires values")
            values = raw_value.get("values", [])
            if not values:
                raise ValueError("allow_list mode requires non-empty values")
            return ScopedAccess(AccessMode.ALLOW_LIST, frozenset(values))

        else:
            raise ValueError(f"Unknown mode: {mode_str}")

    raise TypeError(f"Invalid access scope format: {type(raw_value)}")
