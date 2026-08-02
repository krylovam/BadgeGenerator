# BadgeGenerator

Генератор бейджей: берёт фото участников и макет бейджа, наносит имя/фамилию,
встраивает фото (с автоматической детекцией лица) и сохраняет результат —
отдельными PNG или PDF-листом для печати с линиями отреза.

Стек: **PySide6 (Qt 6)** для интерфейса, **OpenCV + YuNet (ONNX)** для
детекции лица, Pillow для отрисовки.

## Запуск

```bash
pip install -r requirements.txt
python design/application_controller.py
```

## Как подключить новый макет бейджа

1. Положите PNG-макет в любую папку (например, `templates/`).
2. Запустите приложение, выберите папку с фото и макет.
3. Нажмите **«Настроить шаблон…»** — откроется мастер, в котором мышью
   расставляются текстовые поля (имя, фамилия, произвольные) и область фото,
   задаётся размер бейджа в миллиметрах.
4. Мастер сохранит JSON-конфиг рядом с макетом (`<имя_макета>.json`).
   В следующий раз конфиг подхватится автоматически — код менять не нужно.

Конфиг можно редактировать и вручную. Пример:

```json
{
  "template_file": "макет.png",
  "badge_size_mm": [100, 70],
  "dpi": 300,
  "text_fields": [
    {
      "id": "name",
      "label": "Имя",
      "anchor": [240, 520],
      "align": "left",
      "font": "assets/Montserrat.ttf",
      "font_size": 200,
      "color": [0, 0, 0],
      "max_width": 700,
      "auto_shrink": true,
      "uppercase": false
    }
  ],
  "photo": {
    "place_on_badge": [285, 1102, 1290, 1470],
    "crop_size": [1290, 1470],
    "face_scale": 0.5,
    "face_offset_y": 1.1,
    "remove_background": false
  }
}
```

Параметры:

- `badge_size_mm` — физический размер бейджа для печати;
- `dpi` — разрешение печати;
- `text_fields` — текстовые поля: `anchor` — позиция (x, y), `align` —
  left/center/right, `font_size`, `max_width` (0 = без ограничения),
  `auto_shrink` — уменьшать шрифт, если текст не влезает, `uppercase`,
  `color` — [r, g, b]. Значение берётся из имени файла: первый токен —
  фамилия, остальные — имя (разделители: пробел, `_`, `-`);
- `photo` — область фото на макете `place_on_badge` (x, y, w, h), размер
  кадрирования из исходного фото `crop_size`, `face_scale` — во сколько раз
  ширина лица меньше ширины кадра, `face_offset_y` — смещение центра лица
  по вертикали, `remove_background` — удалять светлый фон с фото
  (алгоритм в `badge_generator/delete_background.py`).

## Детекция лица

Основной движок — **YuNet** (CNN-модель `face_detection_yunet_2023mar.onnx`,
лежит в `detector/utils/`, ~230 КБ). Она точнее каскада Хаара и дополнительно
возвращает 5 ключевых точек лица, по которым фото центрируется по глазам
(а не по прямоугольнику). Если файл модели удалить, детектор автоматически
откатится на каскад `cascade.xml`.

## Печать

Кнопка **«Сохранить PDF для печати»** собирает A4-листы (300 dpi) с реальным
размером бейджей из конфига. Вокруг каждого бейджа рисуется пунктирная линия
отреза (можно отключить галочкой в окне сохранения). Сетка на листе
рассчитывается автоматически; при желании можно ограничить число бейджей
на странице через `max_per_page` в `design/pdf_output.py`.

## Тесты

```bash
python -m pytest
```

UI-тесты работают в offscreen-режиме и пропускаются, если PyQt5 недоступен.

## Структура

```
badge_generator/          # ядро (без Qt)
    template.py           # конфиг шаблона (JSON)
    BadgeGenerator.py     # генерация бейджа
    delete_background.py  # удаление светлого фона с фото
detector/
    FaceDetection.py      # детекция лица: YuNet (ONNX) + каскад Хаара
    utils/                # модели: face_detection_yunet_2023mar.onnx, cascade.xml
design/                   # интерфейс (PySide6 / Qt 6)
    application_controller.py
    main_menu.py / main_menu.ui / ui_main_menu.py
    template_wizard.py    # мастер настройки шаблона
    constructor.py / constructor_controller.py
    saver.py / saver_controller.py
    pdf_output.py         # PDF с линиями отреза
assets/Montserrat.ttf     # шрифт по умолчанию
```

`ui_main_menu.py` сгенерирован из `main_menu.ui`:

```bash
pyside6-uic design/main_menu.ui -o design/ui_main_menu.py
```
