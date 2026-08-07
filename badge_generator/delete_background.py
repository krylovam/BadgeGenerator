"""Вырезание человека с фото (удаление фона) библиотекой rembg.

Единственный способ — как в оригинальном приложении:

    from rembg import remove
    result = remove(image)

Модель rembg скачивает сама при первом вызове (в папку ~/.u2net),
дальше использует из кэша.
"""
from __future__ import annotations

from PIL import Image


def remove_background_rembg(image: Image.Image) -> Image.Image:
    """Вырезает человека с фото библиотекой rembg (как в оригинальном приложении).

    :param image: исходное фото (RGB/RGBA).
    :returns: RGBA-изображение с прозрачным фоном.
    :raises ImportError: если rembg/onnxruntime не установлены.
    """
    try:
        from rembg import remove
    except ImportError as e:
        raise ImportError(
            "Библиотека rembg не установлена. Установите: pip install 'rembg[cpu]'"
        ) from e
    return remove(image)
