# BadgeGenerator

## Подпись фотографий именами файлов

Скрипт `add_filename_to_photos.py` обрабатывает все изображения в указанной папке:

- добавляет белые поля вокруг фотографии;
- снизу по центру пишет имя файла без расширения;
- сохраняет результат в отдельную папку, не меняя исходные файлы.

Например, для `IMG_3251-3.jpg` подпись будет `IMG_3251-3`.

### Установка

```bash
python -m pip install -r requirements.txt
```

### Запуск

```bash
python add_filename_to_photos.py "/путь/к/папке/с/фото"
```

По умолчанию рядом появится папка `<имя исходной папки>_with_names`. Можно явно указать папку результата:

```bash
python add_filename_to_photos.py "/путь/к/фото" --output-dir "/путь/к/результату"
```

Если фотографии находятся в текущей папке, путь можно не указывать:

```bash
python add_filename_to_photos.py
```

Дополнительные параметры:

```bash
# Обработать также вложенные папки
python add_filename_to_photos.py ./photos --recursive

# Задать поля 50 пикселей и размер шрифта 42 пикселя
python add_filename_to_photos.py ./photos --margin 50 --font-size 42

# Использовать другой шрифт
python add_filename_to_photos.py ./photos --font ./my-font.ttf
```

Поддерживаются файлы JPG/JPEG, PNG, WEBP, BMP, GIF и TIFF. Для анимированного GIF обрабатывается первый кадр.
