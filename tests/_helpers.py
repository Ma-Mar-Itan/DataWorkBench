"""
Shared test helpers.

Building a tiny in-memory .xlsx once per test is much cheaper than
reading fixtures off disk, and makes the tests self-contained.
"""
from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook


def make_test_workbook(sheets: dict[str, list[list]]) -> bytes:
    """
    Build an .xlsx from a dict of {sheet_name: [[header_row], [data_row], ...]}.

    Returns the raw bytes.
    """
    wb = Workbook()
    # Remove the default sheet; we'll add our own
    default = wb.active
    wb.remove(default)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
