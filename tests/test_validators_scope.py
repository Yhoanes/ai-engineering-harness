import pytest

from engine.execution.models import AccessMode, ScopedAccess
from engine.validators.scope import normalize_access_scope


def test_normalize_none():
    assert normalize_access_scope(None) == ScopedAccess(mode=AccessMode.DENY_ALL)


def test_normalize_empty_list():
    assert normalize_access_scope([]) == ScopedAccess(mode=AccessMode.DENY_ALL)


def test_normalize_populated_list():
    res = normalize_access_scope(["pytest", "git"])
    assert res.mode == AccessMode.ALLOW_LIST
    assert res.values == frozenset({"pytest", "git"})


def test_normalize_list_duplicates():
    res = normalize_access_scope(["a", "a", "b"])
    assert res.mode == AccessMode.ALLOW_LIST
    assert res.values == frozenset({"a", "b"})


def test_normalize_list_wildcards():
    res = normalize_access_scope(["*", "**"])
    assert res.mode == AccessMode.ALLOW_LIST
    assert res.values == frozenset({"*", "**"})


def test_normalize_dict_deny_all():
    res = normalize_access_scope({"mode": "deny_all"})
    assert res.mode == AccessMode.DENY_ALL
    assert res.values == frozenset()


def test_normalize_dict_unrestricted():
    res = normalize_access_scope({"mode": "unrestricted"})
    assert res.mode == AccessMode.UNRESTRICTED
    assert res.values == frozenset()


def test_normalize_dict_allow_list():
    res = normalize_access_scope({"mode": "allow_list", "values": ["pytest"]})
    assert res.mode == AccessMode.ALLOW_LIST
    assert res.values == frozenset({"pytest"})


def test_normalize_invalid_mode():
    with pytest.raises(ValueError, match="Unknown mode: garbage"):
        normalize_access_scope({"mode": "garbage"})


def test_normalize_invalid_type():
    with pytest.raises(TypeError):
        normalize_access_scope(123)


def test_normalize_deny_all_with_values_fails():
    with pytest.raises(ValueError, match="deny_all mode does not accept values"):
        normalize_access_scope({"mode": "deny_all", "values": ["x"]})


def test_normalize_unrestricted_with_values_fails():
    with pytest.raises(ValueError, match="unrestricted mode does not accept values"):
        normalize_access_scope({"mode": "unrestricted", "values": ["x"]})


def test_normalize_allow_list_without_values_fails():
    with pytest.raises(ValueError, match="allow_list mode requires values"):
        normalize_access_scope({"mode": "allow_list"})


def test_normalize_allow_list_with_empty_values_fails():
    with pytest.raises(ValueError, match="allow_list mode requires non-empty values"):
        normalize_access_scope({"mode": "allow_list", "values": []})
