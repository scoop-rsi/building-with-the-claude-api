# Functions to validate the output structure
import ast
import json
import re


def _validate_json(text: str) -> float:
    try:
        json.loads(text.strip())
        return 10
    except json.JSONDecodeError:
        return 0


def _validate_python(text: str) -> float:
    try:
        ast.parse(text.strip())
        return 10
    except SyntaxError:
        return 0


def _validate_regex(text: str) -> float:
    try:
        re.compile(text.strip())
        return 10
    except re.error:
        return 0


def syntax_score(response: str, test_case) -> float:
    format = test_case["format"]
    if format == "json":
        return _validate_json(response)
    elif format == "python":
        return _validate_python(response)
    else:
        return _validate_regex(response)
