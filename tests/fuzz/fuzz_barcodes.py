"""Fuzz barcode normalisation of the product admin API."""

import sys

import atheris

with atheris.instrument_imports():
    import _paths  # noqa: F401

    from catalog_service.schemas import normalize_barcodes


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    values = [fdp.ConsumeUnicodeNoSurrogates(160) for _ in range(fdp.ConsumeIntInRange(0, 60))]
    try:
        result = normalize_barcodes(values)
    except ValueError:
        return
    assert result is not None
    assert len(result) == len(set(result))
    for code in result:
        assert code and code == code.strip().casefold() and len(code) <= 128


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
