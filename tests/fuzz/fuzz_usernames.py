"""Fuzz customer username normalisation and validation (public kiosk input)."""

import sys

import atheris

with atheris.instrument_imports():
    import _paths  # noqa: F401
    from fastapi import HTTPException

    from kiosk_common.usernames import MAX_USERNAME_LENGTH, normalize_username, validate_new_username


def TestOneInput(data: bytes) -> None:
    text = atheris.FuzzedDataProvider(data).ConsumeUnicodeNoSurrogates(256)
    name = normalize_username(text)
    # Normalising is idempotent and never leaves surrounding whitespace or capitals.
    assert normalize_username(name) == name
    assert name == name.strip()
    try:
        validate_new_username(name)
    except HTTPException as exc:
        assert exc.status_code == 422
    else:
        assert len(name) <= MAX_USERNAME_LENGTH


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
