# Russian UI translations for SimplyFive Light.
#
# Every key must be an EXACT English UI string produced by __init__.py, or the
# translation silently never applies. Change an English string here in the same
# edit you change it there. No dead keys (kept in sync with the source).

TRANSLATIONS_RU = {
    "Pre-prune": "Предобрезка",
    "Sloppy (topology-ignoring)": "Грубое (игнорирует топологию)",
    "Regularize": "Регуляризация",
    "Importance Strength": "Сила важности",
    "Details": "Детали",
    "Error Absolute (for multiple materials)": "Абсолютная ошибка (для нескольких материалов)",
    "LOD Preview (distance)": "Просмотр LOD (дистанция)",
    "Lock Open Edges": "Блокировать открытые рёбра",
    "Merge Threshold": "Порог слияния",
    "Merge by Distance": "Слияние по расстоянию",
    "Multiple UV Channels": "Несколько UV-каналов",
    "Mode": "Режим",
    "Naming": "Именование",
    "LOD Name Suffix": "Суффикс имён LOD",
    "Text between the base object name and the LOD index (e.g. '_lod_' gives 'Cube_lod_1'). Changing it does not rename existing LODs - objects named with the old suffix are no longer recognized as part of a LOD family":
        "Текст между базовым именем объекта и номером LOD (например, '_lod_' даёт 'Cube_lod_1'). Изменение не переименовывает существующие LOD — объекты со старым суффиксом перестают распознаваться как часть семейства LOD",
    "Recalculate + Auto Smooth": "Пересчитать + Auto Smooth",
    "Normal Weight": "Вес нормалей",
    "Number of LODs": "Количество LOD",
    "Permissive (aggressive)": "Разрешающий (агрессивно)",
    "Preserve UVs && Normals": "Сохранять UV и нормали",
    "Protect UV Seams": "Защищать UV-швы",
    "Prune (aggressive)": "Обрезка (агрессивно)",
    "Target Error": "Целевая ошибка",
    "UV Weight": "Вес UV",
    "Vertex Update (moves UVs, more aggressive)": "Обновление вершин (сдвигает UV, агрессивнее)",
    "How many LOD objects to generate": "Сколько объектов LOD создать",
    "Keep this small - a large value can weld nearby but intentionally separate geometry (e.g. thin gaps) together":
        "Держите значение небольшим — большое может склеить близко расположенную, но специально разделённую геометрию (например, тонкие щели)",
    "Percentage of the original triangle count to keep for this LOD":
        "Процент треугольников от оригинала, который нужно сохранить для этого LOD",
    "Generate LODs": "Сгенерировать LOD",
    "Generate This LOD": "Сгенерировать этот LOD",
    "Only This LOD": "Только этот LOD",
    "Line Up LODs": "Выстроить LOD в ряд",
    "Lay every existing LOD of this family out in a row, isolated in local view (like pressing '/'), to compare the progression side by side. Press again, move the preview slider or use 'Only This LOD' to restore":
        "Выстраивает все существующие LOD этого семейства в ряд, изолируя их в local view (как нажатие '/'), чтобы сравнить прогрессию со стороны. Повторное нажатие, движение слайдера или 'Only This LOD' возвращают всё на место",
    "Nothing to line up - generate some LODs first.":
        "Нечего выстраивать — сначала сгенерируйте LOD.",
    "Show All LODs": "Показать все LOD",
    "Create every configured LOD, from lod_0": "Создать все настроенные LOD, из lod_0",
    "Hide every other LOD in this family. Use 'Show All LODs' to undo":
        "Скрыть все остальные LOD в этом семействе. Отменить — кнопкой 'Show All LODs'",
    "Regenerate just this LOD from lod_0, replacing it (others untouched)":
        "Перегенерировать только этот LOD из lod_0, заменяя его (остальные не трогаются)",
    "Unhide every LOD in this object's family": "Показать все LOD в семействе этого объекта",
    "Careful": "Осторожный",
    "Most precise: locks open edges, low Target Error, no attribute-crossing":
        "Самый точный: блокирует открытые рёбра, низкий Target Error, без пересечения атрибутов",
    "Standard": "Стандартный",
    "Balanced: keeps UVs/normals, Vertex Update on, moderate Target Error":
        "Сбалансированный: сохраняет UV/нормали, Vertex Update включён, умеренный Target Error",
    "Aggressive": "Агрессивный",
    "Permissive + Prune + protected UV seams, higher Target Error":
        "Permissive + Prune + защищённые UV-швы, более высокий Target Error",
    "Very Aggressive": "Очень агрессивный",
    "Like Aggressive with very low attribute weights and a higher Target Error. meshopt only - may stop above the requested percentage":
        "Как Aggressive, но с очень низкими весами атрибутов и более высоким Target Error. Только meshopt — может остановиться выше запрошенного процента",
    "Very Aggressive Alternative": "Очень агрессивный (альтернативный)",
    "Very Aggressive plus a Decimate pass down to the exact percentage, with UV seams protected. Which of the two works better depends on the model":
        "Очень агрессивный плюс проход Decimate до точного процента, с защитой UV-швов. Какой из двух лучше — зависит от модели",
    "Quality preset for this LOD: how aggressively it is simplified. Careful keeps the most detail; Very Aggressive pushes the triangle count much lower":
        "Пресет качества для этого LOD: насколько агрессивно он упрощается. Careful сохраняет больше всего деталей; Very Aggressive сильнее снижает число треугольников",
    "Show the advanced per-LOD settings for this LOD": "Показать расширенные настройки этого LOD",
    "How strongly the importance mask biases simplification. This is a soft weight (a penalty in the error metric), not a hard guarantee - very aggressive ratios may still touch important areas":
        "Насколько сильно карта важности влияет на упрощение. Это мягкий вес (штраф в метрике ошибки), а не жёсткая гарантия — очень агрессивные проценты всё равно могут затронуть важные области",
    "Importance Source": "Источник важности",
    "Where the per-vertex importance mask is read from":
        "Откуда берётся карта важности по вершинам",
    "Vertex Color": "Цвет вершин",
    "Luminance of the active color attribute (white = important)":
        "Яркость активного слоя цвета (белый = важно)",
    "Vertex Group": "Группа вершин",
    "Weights of a named vertex group (1 = important) - editable in Weight Paint, and never guessed, so bone weights on a rigged mesh are left alone":
        "Веса именованной группы вершин (1 = важно) — правятся в Weight Paint и не угадываются, так что веса костей на скинненой модели не трогаются",
    "Importance Group": "Группа важности",
    "Vertex group whose weights drive the importance mask (used only when Source = Vertex Group)":
        "Группа вершин, чьи веса задают карту важности (только при Источник = Группа вершин)",
    "Advanced - available in Pro": "Расширенные — доступно в Pro",
    "Per-LOD Target Error": "Target Error для каждого LOD",
    "Lock Border / Prune": "Блокировка границ / Prune",
    "Permissive + Protect UV Seams": "Permissive + защита UV-швов",
    "Vertex Update, Normal / UV Weight": "Vertex Update, веса нормалей / UV",
    "Build from Previous LOD (chained)": "Строить из предыдущего LOD (цепочка)",
    "Vertex Color hard-lock": "Жёсткая блокировка по цвету вершин",
    "Hard-Lock Above Threshold (Pro)": "Жёсткая блокировка по порогу (Pro)",
    "Treat Target Error as an absolute distance instead of relative to mesh extents - gives more precise control for very aggressive LODs, especially with multiple materials":
        "Трактует Target Error как абсолютное расстояние, а не относительно габаритов меша — даёт более точный контроль для очень агрессивных LOD, особенно при нескольких материалах",
    "Get SimplyFive Pro": "Получить SimplyFive Pro",
    "Simplification library: ready": "Библиотека упрощения: готова",
    "Simplification library not found": "Библиотека упрощения не найдена",
    "Reinstall the add-on to restore the bundled library.":
        "Переустановите аддон, чтобы восстановить встроенную библиотеку.",
    "Importance Mask": "Маска важности",
    "Bias simplification with a per-vertex importance map: important areas cost more to collapse, so they keep more detail. Pick the source with Importance Source":
        "Смещает упрощение картой важности по вершинам: важные области дороже схлопывать, поэтому в них сохраняется больше деталей. Источник выбирается в Importance Source",
    "Carry every UV channel onto the LODs, keeping names and active/render flags. All of them enter the error metric with the same UV Weight, so extra seams constrain simplification. Off = only the active channel is copied":
        "Переносит на LOD все UV-каналы, сохраняя имена и флаги active/render. Все они входят в метрику ошибки с тем же UV Weight, поэтому лишние швы ограничивают упрощение. Выкл = копируется только активный канал",
    "Weld coincident vertices on the result (Blender's Merge by Distance). UVs and normals are stored per face-corner, so welding does not blend them":
        "Сваривает совпадающие вершины результата (штатный Merge by Distance Blender). UV и нормали хранятся по углу грани, поэтому сварка их не смешивает",
    "Simulates moving away from the object: 0 = lod_0 (closest), higher = further/more aggressive LODs. Same effect as the 'Only This LOD' buttons":
        "Имитирует отдаление от объекта: 0 = lod_0 (ближайший), больше = дальние/более агрессивные LOD. То же, что кнопки 'Only This LOD'",
    "Select a mesh to begin.": "Выберите меш, чтобы начать.",
    "meshoptimizer: not built yet": "meshoptimizer: ещё не собран",
    "Build it in Edit > Preferences > Add-ons": "Соберите его в Edit > Preferences > Add-ons",
    "Credits": "Благодарности",
    "Uses meshoptimizer by Arseny Kapoulkine (MIT License).":
        "Использует meshoptimizer от Arseny Kapoulkine (лицензия MIT).",
}


def _build_translations_dict():
    result = {}
    for source, translated in TRANSLATIONS_RU.items():
        result[("*", source)] = translated
    return {"ru_RU": result}
