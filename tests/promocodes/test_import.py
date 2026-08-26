from __future__ import annotations

import io

import openpyxl
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict

from apps.promocodes.forms import MAX_UPLOAD_SIZE_MB, PromoCodeUploadForm
from apps.promocodes.models import PromoCode
from apps.promocodes.services import import_promo_codes_from_xlsx

XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _build_xlsx(codes: list[str]) -> bytes:
    """Собирает xlsx-файл с одним кодом в каждой строке первого столбца."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    for code in codes:
        sheet.append([code])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_import_counts_added_rows_without_duplicates(db) -> None:
    """added считает реально новые коды, дубли и мусор не засчитываются."""
    PromoCode.objects.create(code="AAAA1111")
    content = _build_xlsx(
        ["AAAA1111", "BBBB2222", "BBBB2222", "не-код", "CCCC3333"]
    )
    upload = SimpleUploadedFile(
        "codes.xlsx", content, content_type=XLSX_CONTENT_TYPE
    )

    result = import_promo_codes_from_xlsx(upload)

    assert result.added == 2
    assert result.rejected_duplicate == 2
    assert result.rejected_invalid_format == 1
    assert PromoCode.objects.filter(code="BBBB2222").exists()
    assert PromoCode.objects.filter(code="CCCC3333").exists()


def test_upload_form_rejects_oversized_file() -> None:
    """Файл больше лимита отклоняется формой с понятным сообщением."""
    oversized_content = b"0" * (MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    upload = SimpleUploadedFile(
        "codes.xlsx", oversized_content, content_type=XLSX_CONTENT_TYPE
    )

    form = PromoCodeUploadForm(files=MultiValueDict({"file": [upload]}))

    assert not form.is_valid()
    assert "file" in form.errors
