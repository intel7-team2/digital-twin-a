"""Validate the Cellect 2A I/O sheet and export GP-Pro EX read symbols."""

import argparse
import csv
import re
from collections import Counter
from pathlib import Path


SHEET = Path(__file__).with_name("io-map.csv")
FIELDS = "symbol screen kind unit owner status device gp_address reference".split()
NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
ADDRESS_TYPES = {"bit": "BIT", "word": "WORD"}
SCREENS = {"B100", "B200", "B210", "B220", "B300", "B400", "B500", "B510"}


def read_sheet(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != FIELDS:
            raise ValueError("Expected columns: " + ", ".join(FIELDS))
        rows = []
        names = set()
        addresses = set()
        for line, raw in enumerate(reader, 2):
            if None in raw or None in raw.values():
                raise ValueError(f"Row {line}: column count does not match header")
            row = {field: value.strip() for field, value in raw.items()}
            validate_row(row, line, names, addresses)
            rows.append(row)
    if not rows:
        raise ValueError("I/O sheet is empty")
    return rows


def validate_row(row, line, names, addresses):
    symbol = row["symbol"]

    def fail(message):
        raise ValueError(f"Row {line} ({symbol}): {message}")

    if not NAME.fullmatch(symbol) or symbol in names:
        fail("invalid or duplicate symbol")
    names.add(symbol)
    if row["screen"] not in SCREENS or row["kind"] not in (*ADDRESS_TYPES, "bridge"):
        fail("unknown screen or kind")
    if row["owner"] != "bridge":
        fail("the source must be a bridge-published observation")
    if row["status"] not in {"pending", "approved"}:
        fail("status must be pending or approved")

    device, address, reference = (row[field] for field in ("device", "gp_address", "reference"))
    if row["kind"] == "bridge":
        if device or address or (row["status"] == "approved" and not reference):
            fail("bridge fields require a contract reference when approved and no GP address")
        return
    if row["status"] == "pending":
        return
    if not (device and address and reference):
        fail("an approved read point requires a device, GP address and approval reference")
    address_key = (device.casefold(), address.casefold())
    if address_key in addresses:
        fail("duplicate address for the selected device")
    addresses.add(address_key)


def export_symbols(rows, device, output):
    selected = [
        row for row in rows
        if row["status"] == "approved" and row["kind"] in ADDRESS_TYPES
        and row["device"] == device
    ]
    if not selected:
        raise ValueError(f"No approved read symbols for device {device!r}; no output written")
    with output.open("x", encoding="utf-16", newline="") as destination:
        writer = csv.writer(destination)
        writer.writerow(("Name", "Type", "Address"))
        writer.writerows(
            (row["symbol"], ADDRESS_TYPES[row["kind"]], row["gp_address"]) for row in selected
        )
    return len(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=SHEET)
    parser.add_argument("--device", help="exact GP-Pro EX device name to export")
    parser.add_argument("--output", type=Path, help="new Unicode CSV file to create")
    args = parser.parse_args()
    if (args.device is None) != (args.output is None):
        parser.error("--device and --output are required together")

    try:
        rows = read_sheet(args.map)
        counts = Counter(row["status"] for row in rows)
        print(f"I/O map: {len(rows)} symbols, {counts['pending']} pending, {counts['approved']} approved")
        if args.output is not None:
            count = export_symbols(rows, args.device, args.output)
            print(f"Wrote {count} read symbols to {args.output}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
