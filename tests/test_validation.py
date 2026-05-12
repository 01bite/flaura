from __future__ import annotations

from flaura.plugins.registry import validate_args


def test_enum_passes():
    schema = {"type": "object", "properties": {"x": {"enum": ["a", "b"]}}}
    assert validate_args({"x": "a"}, schema) is None


def test_enum_fails():
    schema = {"type": "object", "properties": {"x": {"enum": ["a", "b"]}}}
    err = validate_args({"x": "c"}, schema)
    assert err is not None
    assert "x" in err


def test_pattern_passes():
    schema = {"type": "object", "properties": {"v": {"type": "string", "pattern": r"^\d+$"}}}
    assert validate_args({"v": "123"}, schema) is None


def test_pattern_fails():
    schema = {"type": "object", "properties": {"v": {"type": "string", "pattern": r"^\d+$"}}}
    err = validate_args({"v": "abc"}, schema)
    assert err is not None


def test_oneof():
    schema = {
        "type": "object",
        "properties": {
            "value": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "integer"},
                ]
            }
        },
    }
    assert validate_args({"value": "hi"}, schema) is None
    assert validate_args({"value": 7}, schema) is None
    assert validate_args({"value": 1.5}, schema) is not None


def test_nested_object():
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer", "minimum": 0},
                },
                "required": ["name"],
            }
        },
        "required": ["user"],
    }
    assert validate_args({"user": {"name": "Alice", "age": 30}}, schema) is None
    # missing nested required
    assert validate_args({"user": {"age": 30}}, schema) is not None
    # negative age violates minimum
    assert validate_args({"user": {"name": "Alice", "age": -1}}, schema) is not None


def test_ref_with_defs():
    schema = {
        "$defs": {
            "Email": {"type": "string", "pattern": r"^[^@]+@[^@]+$"},
        },
        "type": "object",
        "properties": {"email": {"$ref": "#/$defs/Email"}},
        "required": ["email"],
    }
    assert validate_args({"email": "alice@example.com"}, schema) is None
    assert validate_args({"email": "not-an-email"}, schema) is not None
