# Russian UI translations for simplyFive.

TRANSLATIONS_RU = {
    "Carry UVs / Materials / Colors": "Переносить UV / материалы / цвета",
    "Sloppy ignores attributes while simplifying: Lock Border, Sparse, Prune, Permissive, Regularize, weights and Vertex Update don't apply. The checkbox above only carries UVs, material IDs and vertex colors onto the result.":
        "Sloppy игнорирует атрибуты при упрощении: Lock Border, Sparse, Prune, Permissive, Regularize, веса и Vertex Update не действуют. Галочка выше лишь переносит UV, ID материалов и цвета вершин на результат.",
    "Mode Presets (editable)": "Пресеты режимов (редактируемые)",
    "Preset": "Пресет",
    "Reset Preset to Factory": "Сбросить пресет к заводским",
    "Restore this Mode preset's values to the add-on's built-in factory defaults":
        "Восстанавливает значения этого пресета режима к встроенным заводским настройкам аддона",
    "Note: changes apply when switching Mode in the panel. Slot defaults for brand-new scenes refresh after a Blender restart.":
        "Примечание: изменения применяются при переключении Mode в панели. Стартовые значения слотов для новых сцен обновятся после перезапуска Blender.",
    "Vertex Update": "Обновление вершин",
    "Pre-prune": "Предобрезка",
    "meshopt_simplifyPrune as a separate pre-pass: removes small disconnected components whose size relative to the whole mesh is below this threshold, BEFORE the main simplification. 0 = off. Unlike the Prune checkbox (whose threshold is tied to Target Error), this knob is independent - e.g. strip debris aggressively while keeping the main simplification precise":
        "meshopt_simplifyPrune отдельным предварительным проходом: удаляет мелкие отсоединённые компоненты, чей размер относительно всего меша ниже этого порога, ДО основного упрощения. 0 = выключено. В отличие от галочки Prune (порог которой привязан к Target Error), эта настройка независима — например, можно агрессивно срезать мусор, сохранив точность основного упрощения",
    "Sloppy (topology-ignoring)": "Грубое (игнорирует топологию)",
    "meshopt_simplifySloppy: ignores topology entirely - far more aggressive than normal edge-collapse, and can merge or destroy features freely. For very distant LODs only. Replaces the normal algorithm (Vertex Update and attribute weights don't apply)":
        "meshopt_simplifySloppy: полностью игнорирует топологию — гораздо агрессивнее обычного схлопывания рёбер, может свободно сливать и уничтожать детали. Только для очень дальних LOD. Заменяет обычный алгоритм (Vertex Update и веса атрибутов не действуют)",
    "Regularize": "Регуляризация",
    "meshopt_SimplifyRegularize: produce more uniform triangles, at some cost to appearance/triangle count. Useful for deformable meshes and raytracing performance":
        "meshopt_SimplifyRegularize: делает треугольники более равномерными ценой внешнего вида/числа треугольников. Полезно для деформируемых мешей и производительности рейтрейсинга",
    "Off": "Выключена",
    "No regularization": "Без регуляризации",
    "Regularize Light": "Лёгкая регуляризация",
    "meshopt_SimplifyRegularizeLight: milder uniformity bias": "meshopt_SimplifyRegularizeLight: более мягкое выравнивание",
    "meshopt_SimplifyRegularize: full uniformity bias": "meshopt_SimplifyRegularize: полное выравнивание",
    "Build Tools (advanced)": "Инструменты сборки (для продвинутых)",
    "Rebuilding the meshoptimizer library from source. Only needed by developers or if the bundled library has a problem - most users never need this":
        "Пересборка библиотеки meshoptimizer из исходников. Нужна только разработчикам или при проблемах с приложенной библиотекой — большинству пользователей не требуется",
    "Restore Defaults": "Сбросить по умолчанию",
    "Reset every LOD setting (count, percentages, all options) back to the add-on's built-in defaults":
        "Сбрасывает все настройки LOD (количество, проценты, все опции) к встроенным значениям аддона по умолчанию",
    "Use Vertex Color as Importance": "Вес важности по цвету вершин",
    "Read the active vertex color layer as a per-vertex importance map (luminance: white = important, black = unimportant). Important areas become costlier to collapse, so they keep more detail. Needs 'Preserve UVs & Normals' on. Paint it with Blender's Vertex Paint mode":
        "Читает активный слой цвета вершин как карту важности по вершинам (яркость: белый = важно, чёрный = неважно). Важные области дороже схлопывать, поэтому в них сохраняется больше деталей. Нужна включённая 'Сохранять UV и нормали'. Красьте в режиме Vertex Paint",
    "Importance Strength": "Сила важности",
    "How strongly vertex color importance biases simplification. This is a soft weight (a penalty in the error metric), not a hard guarantee - very aggressive ratios may still touch important areas. Use the hard lock below for a guarantee":
        "Насколько сильно важность по цвету вершин влияет на упрощение. Это мягкий вес (штраф в метрике ошибки), а не жёсткая гарантия — очень агрессивные проценты всё равно могут затронуть важные области. Для гарантии используйте жёсткую блокировку ниже",
    "Hard-Lock Above Threshold": "Жёсткая блокировка выше порога",
    "In addition to the soft weight, fully protect (never collapse) any vertex whose color importance is above the threshold below. A hard guarantee, unlike the soft weight":
        "Дополнительно к мягкому весу — полностью защищает (никогда не схлопывает) вершины, чья важность по цвету выше порога ниже. Жёсткая гарантия, в отличие от мягкого веса",
    "Lock Threshold": "Порог блокировки",
    "Vertices with color importance (luminance) at or above this value are fully locked and never collapsed":
        "Вершины с важностью по цвету (яркостью) на уровне этого значения или выше полностью блокируются и никогда не схлопываются",
    "How much surface normals count in the collapse error metric, as a fraction (0-1) pre-multiplying the normal vector before it's combined with position error. 0 = normals are ignored (shading can distort freely); higher = collapses that would visibly change shading are avoided more strongly. Not passed to meshoptimizer directly - it scales the attribute values before simplification":
        "Насколько сильно нормали поверхности влияют на метрику ошибки при схлопывании — доля (0-1), на которую умножается вектор нормали перед объединением с ошибкой позиции. 0 = нормали игнорируются (затенение может искажаться свободно); выше = схлопывания, заметно меняющие затенение, избегаются сильнее. Напрямую в meshoptimizer не передаётся — масштабирует значения атрибутов перед упрощением",
    "How much UV coordinates count in the collapse error metric, as a fraction (0-1) pre-multiplying the UV values before they're combined with position error. 0 = UVs are ignored (texture can stretch freely); higher = collapses that would visibly distort the texture are avoided more strongly. Not passed to meshoptimizer directly - it scales the attribute values before simplification":
        "Насколько сильно UV-координаты влияют на метрику ошибки при схлопывании — доля (0-1), на которую умножаются значения UV перед объединением с ошибкой позиции. 0 = UV игнорируются (текстура может растягиваться свободно); выше = схлопывания, заметно искажающие текстуру, избегаются сильнее. Напрямую в meshoptimizer не передаётся — масштабирует значения атрибутов перед упрощением",
    "Details": "Детали",
    "Error Absolute (for multiple materials)": "Абсолютная ошибка (для нескольких материалов)",
    "LOD Preview (distance)": "Просмотр LOD (дистанция)",
    "Lock Open Edges": "Блокировать открытые рёбра",
    "Merge Threshold": "Порог слияния",
    "Merge by Distance": "Слияние по расстоянию",
    "Multiple UV Channels": "Несколько UV-каналов",
    "Carry every UV channel of the source mesh (not just the active one) onto the LODs, keeping the original layer names and active/render flags. All channels count in the error metric with the same UV Weight. Off = only the active UV channel is kept and other channels are not copied. On = geometric quality can drop slightly at the same percentage, because extra UV seams (e.g. lightmap islands in UV2) constrain simplification":
        "Переносит на LOD все UV-каналы исходного меша (а не только активный), сохраняя оригинальные имена слоёв и флаги active/render. Все каналы участвуют в метрике ошибки с тем же весом UV Weight. Выкл = сохраняется только активный UV-канал, остальные не копируются. Вкл = геометрическое качество может немного снизиться при том же проценте, так как дополнительные UV-швы (например, островки лайтмапа в UV2) ограничивают упрощение",
    "Mode": "Режим",
    "Naming": "Именование",
    "LOD Name Suffix": "Суффикс имён LOD",
    "Text between the base object name and the LOD index (e.g. '_lod_' gives 'Cube_lod_1'). Changing it does not rename existing LODs - objects named with the old suffix are no longer recognized as part of a LOD family":
        "Текст между базовым именем объекта и номером LOD (например, '_lod_' даёт 'Cube_lod_1'). Изменение не переименовывает существующие LOD — объекты со старым суффиксом перестают распознаваться как часть семейства LOD",
    "Normals": "Нормали",
    "What normals the finished LOD gets. Source normals stop matching the geometry at very low polycounts - recalculating usually shades corners better on aggressively simplified LODs":
        "Какие нормали получит готовый LOD. Нормали исходника перестают соответствовать геометрии на очень низком поликаунте — пересчёт обычно даёт лучшее затенение углов на агрессивно упрощённых LOD",
    "Preserve (from source)": "Сохранить (из исходника)",
    "Carry the source mesh's normals onto the LOD. Best while simplification is moderate":
        "Перенести нормали исходного меша на LOD. Лучший вариант при умеренном упрощении",
    "Recalculate + Auto Smooth": "Пересчитать + Auto Smooth",
    "Discard source normals and recompute from the LOD's own geometry, marking edges sharp above the angle threshold (Shade Smooth by Angle). Predictable at very low polycounts":
        "Отбросить нормали исходника и пересчитать из собственной геометрии LOD, помечая рёбра острыми выше порога угла (Shade Smooth by Angle). Предсказуемо на очень низком поликаунте",
    "Smooth Angle": "Угол сглаживания",
    "For 'Recalculate + Auto Smooth': edges whose faces meet at a sharper angle than this are shaded sharp":
        "Для 'Пересчитать + Auto Smooth': рёбра, чьи грани сходятся под углом острее этого, затеняются как острые",
    "Build from Previous LOD": "Строить из предыдущего LOD",
    "Simplify this LOD from the previous LOD's mesh instead of from lod 0 (chained LODs, recommended by meshoptimizer for aggressive targets: each step is gentler, so far LODs come out cleaner, at the cost of slightly accumulating error). The percentage still means % of lod 0's triangles. Falls back to lod 0 if the previous LOD doesn't exist yet":
        "Упрощать этот LOD из меша предыдущего LOD, а не из lod 0 (цепочка LOD, рекомендация meshoptimizer для агрессивных целей: каждый шаг мягче, дальние LOD получаются чище, ценой небольшого накопления ошибки). Процент по-прежнему означает % треугольников lod 0. Если предыдущий LOD ещё не создан — используется lod 0",
    "Normal Weight": "Вес нормалей",
    "Number of LODs": "Количество LOD",
    "Permissive (aggressive)": "Разрешающий (агрессивно)",
    "Preserve UVs && Normals": "Сохранять UV и нормали",
    "Protect UV Seams": "Защищать UV-швы",
    "Prune (aggressive)": "Обрезка (агрессивно)",
    "Sparse": "Разреженный",
    "Target Error": "Целевая ошибка",
    "UV Weight": "Вес UV",
    "Vertex Update (moves UVs, more aggressive)": "Обновление вершин (сдвигает UV, агрессивнее)",

    "Attribute-aware simplification (meshopt_simplifyWithAttributes): keeps UV seams and hard edges as an attribute-discontinuity term in the error metric, rather than needing them locked":
        "Упрощение с учётом атрибутов (meshopt_simplifyWithAttributes): UV-швы и жёсткие рёбра учитываются как разрыв атрибута в метрике ошибки, а не блокируются жёстко",
    "How many LOD objects to generate": "Сколько объектов LOD создать",
    "Keep this small - a large value can weld nearby but intentionally separate geometry (e.g. thin gaps) together":
        "Держите значение небольшим — большое может склеить близко расположенную, но специально разделённую геометрию (например, тонкие щели)",
    "Max allowed deviation relative to mesh extents; the simplifier stops early for this LOD if it would exceed this even before hitting the target percentage":
        "Максимально допустимое отклонение относительно размеров меша; упрощение для этого LOD останавливается раньше, если превышен этот порог, даже до достижения целевого процента",
    "Only relevant with Permissive: build a vertex_lock (meshopt_SimplifyVertex_Protect) marking vertices whose UV differs across a shared position, so Permissive can collapse freely everywhere except explicitly-protected UV seams":
        "Актуально только с Permissive: строит vertex_lock (meshopt_SimplifyVertex_Protect), помечая вершины, чьи UV различаются в общей позиции — тогда Permissive может свободно упрощать везде, кроме явно защищённых UV-швов",
    "Percentage of the original triangle count to keep for this LOD": "Процент треугольников от оригинала, который нужно сохранить для этого LOD",
    "Prevent open/boundary edges from moving during simplification": "Не позволяет открытым/граничным рёбрам двигаться во время упрощения",
    "Show Target Error / Lock Border / Sparse / Prune / Permissive / attribute settings for this LOD":
        "Показать настройки Target Error / Lock Border / Sparse / Prune / Permissive / атрибутов для этого LOD",
    "Simulates moving away from the object: 0 = lod_0 (closest), higher = further/more aggressive LODs. Same effect as the 'Only This LOD' buttons below":
        "Имитирует отдаление от объекта: 0 = lod_0 (ближайший), больше = дальние/более агрессивные LOD. То же самое, что кнопки 'Only This LOD' ниже",
    "Switching this sets the checkboxes below directly - so you can always see exactly what's on. Manually changing any of them switches this to Custom":
        "Переключение сразу выставляет галочки ниже — всегда видно, что именно включено. Ручное изменение любой из них переключает режим на Custom",
    "Weld coincident-position vertices on the result (Blender's own Merge by Distance). Safe for UV seams - UVs/normals are stored per face-corner, not per vertex, so welding topology doesn't blend or lose them. Keep the threshold small":
        "Сваривает совпадающие по позиции вершины результата (штатный Merge by Distance Blender). Безопасно для UV-швов — UV/нормали хранятся по углу грани, а не по вершине, поэтому сварка топологии их не портит. Держите порог небольшим",
    "meshopt_SimplifyErrorAbsolute: treat Target Error as an absolute distance instead of relative to mesh extents - gives more precise control for very aggressive LODs":
        "meshopt_SimplifyErrorAbsolute: трактовать Target Error как абсолютное расстояние, а не относительное к размеру меша — даёт более точный контроль для очень агрессивных LOD",
    "meshopt_SimplifyPermissive: allows collapsing across attribute (UV/normal) seams when the resulting error is acceptable, instead of getting stuck. Use this for far/simple LODs where some UV distortion is acceptable in exchange for a much lower triangle count. Still experimental upstream":
        "meshopt_SimplifyPermissive: разрешает схлопывание через швы атрибутов (UV/нормали), если итоговая ошибка приемлема, вместо остановки. Используйте для дальних/простых LOD, где допустимо искажение UV ради значительно меньшего числа треугольников. Всё ещё экспериментально в самой библиотеке",
    "meshopt_SimplifyPrune: allows the simplifier to fully discard cheap disconnected bits of geometry instead of only collapsing edges - use this if this LOD gets stuck at a poly count well above its target percentage":
        "meshopt_SimplifyPrune: позволяет полностью отбрасывать дешёвые отсоединённые куски геометрии, а не только схлопывать рёбра — используйте, если этот LOD застревает на поликаунте намного выше целевого процента",
    "meshopt_SimplifySparse: improves simplification quality on meshes made of several disconnected pieces":
        "meshopt_SimplifySparse: улучшает качество упрощения на мешах из нескольких несвязанных частей",
    "meshopt_simplifyWithUpdate: actually moves vertex positions and UVs to fit the new topology, instead of only choosing among original vertices. Reduces distortion at very aggressive ratios - recommended for far/simple LODs where some UV drift is acceptable":
        "meshopt_simplifyWithUpdate: реально сдвигает позиции вершин и UV под новую топологию, а не только выбирает среди исходных вершин. Уменьшает искажения на очень агрессивных процентах — рекомендуется для дальних/простых LOD, где допустим сдвиг UV",

    "Build meshoptimizer (one-time)": "Собрать meshoptimizer (разово)",
    "Generate LODs": "Сгенерировать LOD",
    "Generate This LOD": "Сгенерировать этот LOD",
    "LOD Generator (meshoptimizer)": "Генератор LOD (meshoptimizer)",
    "Only This LOD": "Только этот LOD",
    "Line Up LODs": "Выстроить LOD в ряд",
    "Lay every existing LOD of this family out in a row, isolated in local view (like pressing '/'), to compare the progression side by side. Press again, move the preview slider or use 'Only This LOD' to restore":
        "Выстраивает все существующие LOD этого семейства в ряд, изолируя их в local view (как нажатие '/'), чтобы сравнить прогрессию со стороны. Повторное нажатие, движение слайдера или 'Only This LOD' возвращают всё на место",
    "Nothing to line up - generate some LODs first.": "Нечего выстраивать — сначала сгенерируйте LOD.",
    "Show All LODs": "Показать все LOD",

    "Create every configured LOD, from lod_0": "Создать все настроенные LOD, из lod_0",
    "Downloads meshoptimizer's C++ source via pip and compiles a small native binding for this add-on to use. Needs the same compiler you already used for other add-ons, plus internet access. Only needs to run once":
        "Скачивает исходники meshoptimizer через pip и компилирует небольшой нативный биндинг для аддона. Нужен тот же компилятор, что и раньше, плюс интернет. Достаточно один раз",
    "Hide every other LOD in this family. Use 'Show All LODs' to undo": "Скрыть все остальные LOD в этом семействе. Отменить — кнопкой 'Show All LODs'",
    "Regenerate just this LOD from lod_0, replacing it (others untouched)": "Перегенерировать только этот LOD из lod_0, заменяя его (остальные не трогаются)",
    "Unhide every LOD in this object's family": "Показать все LOD в семействе этого объекта",

    "Careful": "Осторожный",
    "Most precise: locks open edges, low Target Error, no attribute-crossing": "Самый точный: блокирует открытые рёбра, низкий Target Error, без пересечения атрибутов",
    "Standard": "Стандартный",
    "Balanced: keeps UVs/normals, Vertex Update on, moderate Target Error": "Сбалансированный: сохраняет UV/нормали, Vertex Update включён, умеренный Target Error",
    "Aggressive": "Агрессивный",
    "Permissive + Prune + Sparse + protected UV seams, higher Target Error": "Permissive + Prune + Sparse + защищённые UV-швы, более высокий Target Error",
    "Very Aggressive": "Очень агрессивный",
    "Like Aggressive but UV seams not protected and attribute weights are very low - pushes triangle count much lower, more UV drift":
        "Как Aggressive, но UV-швы не защищены, а веса атрибутов очень низкие — сильнее снижает число треугольников, больше сдвиг UV",
    "Clear Simplify": "Чистое упрощение",
    "Pure geometry only (no UV/normal preservation at all) at a high Target Error - the most aggressive reduction, for very far/simple LODs":
        "Только геометрия (без сохранения UV/нормалей вообще) при высоком Target Error — самое агрессивное упрощение, для очень дальних/простых LOD",
    "Custom": "Пользовательский",
    "Checkboxes were changed manually": "Галочки были изменены вручную",

    # --- Light-specific strings ---
    "Quality preset for this LOD: how aggressively it is simplified. Careful keeps the most detail; Very Aggressive pushes the triangle count much lower":
        "Пресет качества для этого LOD: насколько агрессивно он упрощается. Careful сохраняет больше всего деталей; Very Aggressive сильнее снижает число треугольников",
    "Show the advanced per-LOD settings for this LOD": "Показать расширенные настройки этого LOD",
    "Read the active vertex color layer as a per-vertex importance map (luminance: white = important, black = unimportant) for every LOD. Important areas become costlier to collapse, so they keep more detail. Paint it with Blender's Vertex Paint mode":
        "Читает активный слой цвета вершин как карту важности по вершинам (яркость: белый = важно, чёрный = неважно) для всех LOD. Важные области дороже схлопывать, поэтому в них сохраняется больше деталей. Красьте в режиме Vertex Paint",
    "How strongly vertex color importance biases simplification. This is a soft weight (a penalty in the error metric), not a hard guarantee - very aggressive ratios may still touch important areas":
        "Насколько сильно важность по цвету вершин влияет на упрощение. Это мягкий вес (штраф в метрике ошибки), а не жёсткая гарантия — очень агрессивные проценты всё равно могут затронуть важные области",
    "Advanced - available in Pro": "Расширенные — доступно в Pro",
    "Per-LOD Target Error": "Target Error для каждого LOD",
    "Lock Border / Sparse / Prune": "Блокировка границ / Sparse / Prune",
    "Permissive + Protect UV Seams": "Permissive + защита UV-швов",
    "Vertex Update, Normal / UV Weight": "Vertex Update, веса нормалей / UV",
    "Build from Previous LOD (chained)": "Строить из предыдущего LOD (цепочка)",
    "Vertex Color hard-lock": "Жёсткая блокировка по цвету вершин",
    "Multiple UV Channels (Pro)": "Несколько UV-каналов (Pro)",
    "Hard-Lock Above Threshold (Pro)": "Жёсткая блокировка по порогу (Pro)",
    "Treat Target Error as an absolute distance instead of relative to mesh extents - gives more precise control for very aggressive LODs, especially with multiple materials":
        "Трактует Target Error как абсолютное расстояние, а не относительно габаритов меша — даёт более точный контроль для очень агрессивных LOD, особенно при нескольких материалах",
    "Get SimplyFive Pro": "Получить SimplyFive Pro",
    "Simplification library: ready": "Библиотека упрощения: готова",
    "Simplification library not found": "Библиотека упрощения не найдена",
    "Reinstall the add-on to restore the bundled library.":
        "Переустановите аддон, чтобы восстановить встроенную библиотеку.",
}


def _build_translations_dict():
    result = {}
    for source, translated in TRANSLATIONS_RU.items():
        result[("*", source)] = translated
    return {"ru_RU": result}

