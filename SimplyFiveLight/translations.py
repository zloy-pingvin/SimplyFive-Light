# Russian UI translations for SimplyFive Light.
#
# Every key must be an EXACT English UI string produced by __init__.py, or the
# translation silently never applies. Change an English string here in the same
# edit you change it there. No dead keys (kept in sync with the source).
#
# Most entries are copied verbatim from Pro: the greyed Details block mirrors
# Pro's per-LOD panel, so it shows Pro's own labels and tooltips. The store
# build (SHOW_PRO_TEASER off) draws no mirror, so those keys go unused there -
# harmless, an entry that matches nothing simply never applies.

TRANSLATIONS_RU = {
    "Pre-prune": "Предобрезка",
    "Available in SimplyFive Pro": "Доступно в SimplyFive Pro",
    "Queue every selected mesh with the settings on screen":
        "Поставить в очередь каждый выделенный меш с текущими настройками",
    "Remove the selected task": "Удалить выбранную задачу",
    "Move the selected task": "Переместить выбранную задачу",
    "Write the settings on screen into the task of every selected mesh":
        "Записать текущие настройки в задачу каждого выделенного меша",
    "Unhide every LOD in the queue": "Показать все LOD из очереди",
    "Generate every enabled task in order": "Обработать все включённые задачи по порядку",
    "Remove every task from the queue": "Удалить из очереди все задачи",
    "Clear Simplify": "Clear Simplify",
    "Scan": "Scan",
    "Geometry only - no UVs, materials or colors carried - at a high Target Error, with normals rebuilt from the result. For very far/simple LODs":
        "Только геометрия — без UV, материалов и цветов — при высоком Target Error, с пересчётом нормалей по результату. Для очень дальних и простых LOD",
    "Photogrammetry: shape, UV layout and vertex colors come first, at the cost of normal accuracy. Also an aggressive pre-prune pass that clears scanning debris":
        "Фотограмметрия: приоритет сохранения формы, UV-развёртки и цвета вершин, ценой корректности нормалей. Также агрессивный проход пре-прун, убирающий мусор скана",
    "Set Mode": "Задать режим",
    "Switches every enabled task in the queue at once: 0 = lod_0 (closest), higher = further LODs. Each family is clamped to its own last level, so a part with fewer LODs shows its furthest one instead of disappearing":
        "Переключает все включённые задачи очереди разом: 0 — lod_0 (ближайший), дальше — более дальние LOD. Каждое семейство зажато по своему последнему уровню, поэтому деталь с меньшим числом LOD показывает свой самый дальний, а не исчезает",
    "Batch queue - available in Pro": "Пакетная очередь — доступна в Pro",
    "Batch Queue": "Пакетная очередь",
    "Queue several objects and generate them in one run":
        "Поставить в очередь несколько объектов и обработать их одним прогоном",
    "Available in SimplyFive Pro": "Доступно в SimplyFive Pro",
    "Add Selected to Queue": "Добавить выделенное в очередь",
    "Apply Settings to Selected": "Применить настройки к выделенным",
    "Generate All Tasks": "Обработать все задачи",
    "Clear Queue": "Очистить очередь",
    "Object": "Объект",
    "Duplicated surfaces do not collapse.": "Дублирующие поверхности не схлопываются.",
    "Turn on removing duplicated surfaces in the preferences.":
        "Включите удаление дублирующих поверхностей в настройках.",
    "An unwrapped UV map locks the mesh.": "Неразвёрнутая UV-карта запирает меш.",
    "Turn on skipping an unwrapped UV map in the preferences.":
        "Включите пропуск неразвёрнутой UV-карты в настройках.",
    "Part of the mesh did not collapse.": "Часть меша не схлопнулась.",
    "Most of this level is geometry that did not collapse.":
        "Большая часть этого уровня — геометрия, которая не схлопнулась.",
    "The error limit stopped it early.": "Упрощение остановил предел ошибки.",
    "Seams and hard edges lock the vertices.": "Швы и жёсткие рёбра запирают вершины.",
    "Try the Aggressive Mode.": "Попробуйте режим Aggressive.",
    "Try the Very Aggressive Mode.": "Попробуйте режим Very Aggressive.",
    "Try Very Aggressive Alternative: it finishes with Decimate.":
        "Попробуйте Very Aggressive Alternative — он доводит через Decimate.",
    "Raise the target, or tune each LOD in SimplyFive Pro.":
        "Поднимите цель — либо настройте каждый LOD отдельно в SimplyFive Pro.",
    "Weights and shape keys are not carried": "Веса и шейпкеи не переносятся",
    "Skinned mesh: weights are not carried": "Скинненый меш: веса не переносятся",
    "The LOD is baked in the current pose and mix.": "LOD запекается в текущей позе и смеси.",
    "The LOD is baked in the current pose.": "LOD запекается в текущей позе.",
    "Transfer is in SimplyFive Pro.": "Перенос есть в SimplyFive Pro.",
    "Shape keys are not carried": "Шейпкеи не переносятся",
    "The LOD is baked at the current mix.": "LOD запекается с текущей смесью.",
    "No triangles left for these materials:": "Не осталось треугольников у материалов:",
    "The importance mask found no vertex group:": "Маска важности не нашла вертексную группу:",
    "Extra UV maps were dropped. Turn on Multiple UV Channels to keep them.":
        "Лишние UV-карты выброшены. Включите «Несколько UV-каналов», чтобы их сохранить.",
    "Generated objects are named <object><suffix><N>. Your object keeps its name; <object><suffix>0 is a copy of it, and it is hidden.":
        "Сгенерированные объекты называются <объект><суффикс><N>. Ваш объект сохраняет имя; <объект><суффикс>0 — его копия, и она скрыта.",
    "Keep the original object": "Сохранять исходный объект",
    "Generate from a copy instead of renaming your object. The original keeps its name and is hidden in the viewport and the render; the file then holds two copies of the mesh":
        "Генерировать с копии, не переименовывая ваш объект. Оригинал сохраняет имя и скрывается во вьюпорте и в рендере; в файле при этом лежат две копии меша",
    "Target": "Цель",
    "Which unit this level's size is asked for in": "В каких единицах задаётся размер этого уровня",
    "Tris": "Тр.",
    "Share of the source triangle count": "Доля от числа треугольников исходника",
    "An absolute triangle count, the way platform budgets are written":
        "Абсолютное число треугольников — так записаны бюджеты платформ",
    "Triangles": "Треугольники",
    "Triangle count to reduce this LOD to. Counted on the finished object, after welding and any Decimate finish":
        "До скольких треугольников упростить этот LOD. Считается по готовому объекту, после сварки и добивки через Decimate",
    "No LOD of their own at some level:": "Без своего LOD на части уровней:",
    "An empty stands in there.": "Там за них стоит пустышка.",
    "Hierarchy Note": "Заметка об иерархии",
    "Parents that have no LOD of their own at some level, so an empty stands in for them there":
        "Родители, у которых на части уровней нет своего LOD, поэтому там за них стоит пустышка",
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
    "Mode:": "Режим:",
    "Naming": "Именование",
    "Return to Edit Mode": "Возвращаться в режим редактирования",
    "Generating leaves Edit Mode, since regeneration replaces the object. With this on, Edit Mode is re-entered on it afterwards":
        "Генерация выходит из режима редактирования, так как перегенерация заменяет объект. С этой опцией режим редактирования включается на нём обратно",
    "LOD Name Suffix": "Суффикс имён LOD",
    "Text between the base object name and the LOD index (e.g. '_lod_' gives 'Cube_lod_1'). Changing it does not rename existing LODs - objects named with the old suffix are no longer recognized as part of a LOD family":
        "Текст между базовым именем объекта и номером LOD (например, '_lod_' даёт 'Cube_lod_1'). Изменение не переименовывает существующие LOD — объекты со старым суффиксом перестают распознаваться как часть семейства LOD",
    "Recalculate + Auto Smooth": "Пересчитать + Auto Smooth",
    "Normal Weight": "Вес нормалей",
    "Number of LODs": "Количество LOD",
    "Permissive (aggressive)": "Разрешающий (агрессивно)",
    "Preserve UVs & Normals": "Сохранять UV и нормали",
    "Protect UV Seams": "Защищать UV-швы",
    "Prune (aggressive)": "Обрезка (агрессивно)",
    "Target Error": "Целевая ошибка",
    "UV Weight": "Вес UV",
    "Vertex Update (moves UVs, more aggressive)":
        "Обновление вершин (сдвигает UV, агрессивнее)",
    "How many LOD objects to generate": "Сколько объектов LOD создать",
    "Keep small: a large value welds intentionally separate geometry across thin gaps":
        "Держите небольшим: большое значение сваривает специально разделённую геометрию через тонкие щели",
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
    "Restore Defaults": "Сбросить настройки",
    "Put every setting in this panel back to the value it ships with. Only the settings - no object is touched, and Ctrl+Z brings the old ones back":
        "Вернуть все настройки этой панели к исходным значениям. Только настройки — объекты не затрагиваются, а Ctrl+Z вернёт прежние",
    "Settings restored to defaults.": "Настройки сброшены к исходным.",
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
    "Recalculate + Smooth": "Пересчитать + сгладить",
    "Crease Angle": "Угол складки",
    "Edges whose faces meet at a sharper angle than this stay hard when normals are recalculated. Lower keeps more edges crisp; higher smooths more of them together":
        "Рёбра, чьи грани сходятся под углом острее этого, остаются жёсткими при пересчёте нормалей. Меньше — больше рёбер сохранит резкость; больше — сильнее сглаживает их вместе",
    "Discard the source normals and generate new ones from the simplified geometry (meshoptimizer, experimental). Edges meeting at a sharp angle stay hard. At very low triangle counts the source normals no longer match the geometry, which is what makes shading look dented":
        "Отбросить нормали исходника и построить новые по упрощённой геометрии (meshoptimizer, экспериментально). Рёбра, сходящиеся под острым углом, остаются жёсткими. На очень низком поликаунте нормали исходника перестают соответствовать геометрии — отсюда и вмятины в затенении",
    "Very Aggressive plus a Decimate pass down to the exact percentage, with UV seams protected. Which of the two works better depends on the model":
        "Очень агрессивный плюс проход Decimate до точного процента, с защитой UV-швов. Какой из двух лучше — зависит от модели",
    "Quality preset for this LOD: how aggressively it is simplified. Careful keeps the most detail; Very Aggressive pushes the triangle count much lower":
        "Пресет качества для этого LOD: насколько агрессивно он упрощается. Careful сохраняет больше всего деталей; Very Aggressive сильнее снижает число треугольников",
    "Show the advanced per-LOD settings for this LOD":
        "Показать расширенные настройки этого LOD",
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
    "Treat Target Error as an absolute distance instead of relative to mesh extents - gives more precise control for very aggressive LODs, especially with multiple materials":
        "Трактует Target Error как абсолютное расстояние, а не относительно габаритов меша — даёт более точный контроль для очень агрессивных LOD, особенно при нескольких материалах",
    "Get SimplyFive Pro": "Получить SimplyFive Pro",
    "Simplification library: ready": "Библиотека упрощения: готова",
    "Simplification library not found": "Библиотека упрощения не найдена",
    "Reinstall the add-on to restore the bundled library.":
        "Переустановите аддон, чтобы восстановить встроенную библиотеку.",
    "Importance Mask": "Маска важности",
    "Carry every UV channel onto the LODs, keeping names and active/render flags. All of them enter the error metric with the same UV Weight, so extra seams constrain simplification. Off = only the active channel is copied":
        "Переносит на LOD все UV-каналы, сохраняя имена и флаги active/render. Все они входят в метрику ошибки с тем же UV Weight, поэтому лишние швы ограничивают упрощение. Выкл = копируется только активный канал",
    "Weld coincident vertices on the result (Blender's Merge by Distance). UVs and normals are stored per face-corner, so welding does not blend them":
        "Сваривает совпадающие вершины результата (штатный Merge by Distance Blender). UV и нормали хранятся по углу грани, поэтому сварка их не смешивает",
    "Simulates distance: 0 = lod_0 (closest), higher = further LODs. Same effect as the 'Only This LOD' buttons":
        "Имитирует дистанцию: 0 = lod_0 (ближайший), больше = дальние LOD. То же, что кнопки 'Only This LOD'",
    "Select a mesh to begin.": "Выберите меш, чтобы начать.",
    "Credits": "Благодарности",
    "Uses meshoptimizer by Arseny Kapoulkine (MIT License).":
        "Использует meshoptimizer от Arseny Kapoulkine (лицензия MIT).",
    "Check UV Maps": "Проверять UV-карты",
    "Look for UV maps that were never unwrapped before generating. Such a map gives most vertices 3 or more UVs, which meshoptimizer treats as unmovable - simplification then does nothing at all. One pass over the mesh per source, cached until the geometry changes":
        "Искать перед генерацией UV-карты, которые не разворачивали. На такой карте у большинства вершин 3 и больше UV, а это для meshoptimizer значит «не двигать» — упрощение перестаёт работать вовсе. Один проход по мешу на источник, кэшируется до изменения геометрии",
    "Ignore Unwrapped UV Maps": "Игнорировать неразвёрнутые UV-карты",
    "Leave such a map out of simplification. The LOD still gets the map - Blender's own fill reproduces it exactly, since there was nothing in it to carry":
        "Не учитывать такую карту при упрощении. LOD её всё равно получит — штатная заливка Blender воспроизводит её в точности, переносить там было нечего",
    "Check Duplicate Surfaces": "Проверять дублирующие поверхности",
    "Look for faces lying exactly on top of other faces (a surface duplicated for a second material). Both copies become unmovable and take their neighbours with them. One pass over the mesh per source, cached":
        "Искать грани, лежащие точно на других гранях (поверхность, задублированная под второй материал). Обе копии становятся неподвижными и тянут за собой соседей. Один проход по мешу на источник, кэшируется",
    "Drop Duplicate Surfaces": "Отбрасывать дублирующие поверхности",
    "Keep one copy of each duplicated face when simplifying. The dropped copy takes its material with it, so a material used only by that copy disappears from the LOD - the panel says which":
        "Оставлять одну копию каждой задублированной грани. Отброшенная копия уносит свой материал, поэтому материал, которым пользовалась только она, из LOD исчезнет — панель скажет, какой",
    "Optimize for GPU": "Оптимизировать под видеокарту",
    "Reorder triangles and vertices the way a GPU reads them: fewer vertex shader runs and less overdraw in the engine. Applies to every mesh of the family, lod_0 included - that one is your own object, so generating modifies it. Geometry is identical: nothing moves, only the order changes, and it is invisible in Blender":
        "Переупорядочивает треугольники и вершины так, как их читает видеокарта: меньше работы вершинного шейдера и меньше перерисовки пикселей в движке. Геометрия не меняется вообще — меняется только порядок, в Blender это невидно. Применяется ко всем мешам семьи, включая lod_0 — а это ваш собственный объект, то есть генерация его изменит",
    "Limit Prune": "Ограничить обрезку",
    "UV map blocks simplification": "UV-карта блокирует упрощение",
    "Every face is its own island, which locks": "Каждая грань — свой островок, это запирает",
    "the mesh. Left as is - it holds real data.":
        "меш. Оставлено как есть — там реальные данные.",
    "UV map not unwrapped: ignored": "UV-карта не развёрнута: игнорируется",
    "Left out of simplification, copied to": "Не учитывается при упрощении, копируется",
    "the LOD as is.": "на LOD как есть.",
    "UV map not unwrapped": "UV-карта не развёрнута",
    "Every face holds the whole 0-1 square,": "На каждой грани весь квадрат 0-1,",
    "which locks the mesh. Unwrap it.": "это запирает меш. Разверните её.",
    "Duplicated surfaces dropped": "Дублирующие поверхности отброшены",
    "One copy per spot was kept. A material": "Оставлено по одной копии. Материал,",
    "used only by the copy is gone with it.": "которым пользовалась только копия, ушёл с ней.",
    "Duplicated surfaces found": "Найдены дублирующие поверхности",
    "Locked by meshoptimizer, these faces": "meshoptimizer их запирает, такие грани",
    "never simplify. Delete one copy.": "не упрощаются. Удалите одну копию.",
    "Accurate Vertex Colors": "Точный перенос цвета вершин",
    "Blend vertex colors along the collapse instead of keeping the surviving vertex's color. 0 is off. Higher values also let the color steer which edges collapse. Switches Vertex Update and Regularize on":
        "Смешивает цвета вершин при схлопывании вместо того, чтобы оставлять цвет уцелевшей вершины. 0 — выключено. Большие значения также дают цвету влиять на выбор схлопываемых рёбер. Включает Обновление вершин и Регуляризацию",
    "Build from Previous LOD": "Строить из предыдущего LOD",
    "Carry the source mesh's normals onto the LOD. Best while simplification is moderate":
        "Перенести нормали исходного меша на LOD. Лучший вариант при умеренном упрощении",
    "Discard source normals and recompute from the LOD's own geometry, marking edges sharp above the angle threshold (Shade Smooth by Angle). Predictable at very low polycounts":
        "Отбросить нормали исходника и пересчитать из собственной геометрии LOD, помечая рёбра острыми выше порога угла (Shade Smooth by Angle). Предсказуемо на очень низком поликаунте",
    "Finish with Decimate": "Доводка через Decimate",
    "Hard-Lock Above Threshold": "Жёсткая блокировка выше порога",
    "Like Auto Smooth, but closes broken feature loops: a second, lower angle continues a line that has already started, short gaps are bridged, and stray fragments are dropped. For decimated meshes where a single threshold leaves loops open":
        "Как Auto Smooth, но достраивает разорванные лупы: второй, более низкий угол продолжает уже начатую линию, короткие разрывы достраиваются, обрывки убираются. Для упрощённых мешей, где одного порога не хватает и луп остаётся разорванным",
    "Max deviation, relative to mesh extents. Simplification stops early if it would exceed this before reaching the target percentage":
        "Максимальное отклонение относительно размеров меша. Упрощение останавливается раньше, если превысит его до достижения целевого процента",
    "No LODs were generated.": "Ни один LOD не был создан.",
    "No active object.": "Нет активного объекта.",
    "No regularization": "Без регуляризации",
    "Normals": "Нормали",
    "Off": "Выключена",
    "Per-LOD settings - available in Pro": "Настройки для каждого LOD — в версии Pro",
    "Preserve (from source)": "Сохранить (из исходника)",
    "Prevent open/boundary edges from moving during simplification":
        "Не позволяет открытым/граничным рёбрам двигаться во время упрощения",
    "Protect Material Borders": "Защищать границы материалов",
    "Reach the target percentage with Blender's Decimate (Collapse) when meshoptimizer stops short. Distorts UVs less than Permissive. Turns on Protect UV Seams and uses the importance mask":
        "Дойти до заданного процента модификатором Decimate (Collapse), когда meshoptimizer остановился раньше. Искажает UV меньше, чем Разрешающий. Включает защиту UV-швов и использует карту важности",
    "Recalculate + Sharp Loops": "Пересчитать + Умные лупы",
    "Recalculate + Smooth (experimental)": "Пересчитать + Сгладить (эксперимент)",
    "Regularize Light": "Лёгкая регуляризация",
    "Same meshopt_SimplifyVertex_Protect flag, on vertices whose material differs across a shared position. Far fewer vertices than UV seams, so it costs much less. Only used together with Permissive - without it material borders are already kept":
        "Тот же флаг meshopt_SimplifyVertex_Protect, но на вершинах, у которых в общей позиции различается материал. Их на порядок меньше, чем UV-швов, поэтому и стоит намного дешевле. Работает только вместе с Permissive — без него границы материалов и так сохраняются",
    "Simplify from the previous LOD instead of lod 0 (chained LODs): gentler steps, accumulating error. The percentage still means % of lod 0. Falls back to lod 0 if the previous LOD is missing":
        "Упрощать из предыдущего LOD, а не из lod 0 (цепочка LOD): шаги мягче, ошибка накапливается. Процент по-прежнему означает % от lod 0. Если предыдущего LOD нет — берётся lod 0",
    "Weight of UV coordinates in the error metric. 0 = texture may stretch freely. UVs are 0-1 while positions are in scene units, so large meshes need values above 1 (meshoptimizer suggests 10-100)":
        "Вес UV-координат в метрике ошибки. 0 = текстура может растягиваться свободно. UV лежат в 0-1, а позиции — в единицах сцены, поэтому крупным моделям нужны значения выше 1 (meshoptimizer советует 10-100)",
    "Weight of surface normals in the error metric. 0 = shading may distort freely. meshoptimizer suggests around 1.0":
        "Вес нормалей поверхности в метрике ошибки. 0 = затенение может искажаться свободно. meshoptimizer советует около 1.0",
    "meshopt_SimplifyPermissive: allows collapsing across UV/normal seams while the error stays acceptable. Lower triangle count for some UV distortion. Experimental upstream":
        "meshopt_SimplifyPermissive: разрешает схлопывание через швы UV и нормалей, пока ошибка приемлема. Меньше треугольников ценой искажения UV. Экспериментально в самой библиотеке",
    "meshopt_SimplifyPrune: lets the simplifier discard cheap disconnected components instead of only collapsing edges. Helps when the LOD stops well above its target":
        "meshopt_SimplifyPrune: позволяет отбрасывать дешёвые отсоединённые компоненты, а не только схлопывать рёбра. Помогает, когда LOD останавливается заметно выше цели",
    "meshopt_SimplifyRegularize: full uniformity bias":
        "meshopt_SimplifyRegularize: полное выравнивание",
    "meshopt_SimplifyRegularizeLight: milder uniformity bias":
        "meshopt_SimplifyRegularizeLight: более мягкое выравнивание",
    "meshopt_SimplifyVertex_Protect: locks vertices whose UV differs across a shared position, so Permissive collapses everywhere except UV seams. Only used together with Permissive":
        "meshopt_SimplifyVertex_Protect: блокирует вершины, чьи UV различаются в общей позиции — Permissive схлопывает везде, кроме UV-швов. Работает только вместе с Permissive",
    "meshopt_simplifyPrune as a pre-pass: drops disconnected components smaller than this fraction of the mesh, before the main simplification. 0 = off. Independent of Target Error, unlike the Prune checkbox":
        "meshopt_simplifyPrune отдельным предпроходом: удаляет отсоединённые компоненты меньше этой доли меша, до основного упрощения. 0 = выключено. Порог не зависит от Target Error, в отличие от галочки Prune",
    "meshopt_simplifyWithAttributes: UV seams and hard edges enter the error metric as attribute discontinuities instead of being locked":
        "meshopt_simplifyWithAttributes: UV-швы и жёсткие рёбра входят в метрику ошибки как разрывы атрибутов, а не блокируются",
    "meshopt_simplifyWithUpdate: moves vertex positions and UVs to fit the new topology instead of only picking among original vertices. Less distortion at aggressive ratios, at the cost of some UV drift":
        "meshopt_simplifyWithUpdate: сдвигает позиции вершин и UV под новую топологию, а не только выбирает среди исходных вершин. Меньше искажений на агрессивных процентах ценой сдвига UV",
    "meshoptimizer generates the normals and then relaxes them, keeping edges above the angle hard. Evens out the blotchy shading an irregular triangulation leaves. Writes custom split normals, so it replaces edge marking instead of adding to it":
        "meshoptimizer сам считает нормали и затем расслабляет их, оставляя рёбра круче угла хардовыми. Выравнивает пятнистое затенение от неровной триангуляции. Пишет кастомные нормали, поэтому заменяет разметку рёбер, а не дополняет её",
    "Generated objects are named <object><suffix><N>. The original becomes <object><suffix>0 on the first Generate.":
        "LOD-объекты называются <объект><суффикс><N>. Исходник при первой генерации получает имя <объект><суффикс>0.",
    "Source Checks": "Проверки исходника",
    "Stop the prunes from deleting whole parts. Pre-prune is capped at a small share of the triangles, and if Prune still drops the result far below the requested percentage, Target Error is lowered and simplification re-run. Turn off when Prune is meant to strip parts on a distant LOD":
        "Не даёт обрезке удалять детали целиком. Предобрезке ставится потолок в небольшую долю треугольников, а если Prune всё равно уронил результат намного ниже запрошенного процента, Target Error снижается и упрощение повторяется. Выключайте, когда Prune должен срезать детали намеренно — на дальнем LOD",
    "A check is already running.": "Проверка уже выполняется.",
    "Ask the product site whether a newer version exists":
        "Спросить у сайта, вышла ли новая версия",
    "Check Now": "Проверить",
    "Check Updates": "Проверять обновления",
    "Download": "Скачать",
    "Once a day, ask the product site whether a newer version exists. One small request on a background thread, nothing is downloaded or installed and no data about you is sent. Works the same offline":
        "Раз в сутки спрашивает у сайта, вышла ли более новая версия. Один небольшой запрос в фоне: ничего не скачивается и не устанавливается, никакие данные о вас не отправляются. Без интернета работает как обычно",
    "Telegram": "Телеграм",
    "User Manual": "Руководство пользователя",
    "Website": "Сайт",
    "no version published yet": "версия ещё не опубликована",
    "up to date": "актуальная версия",
    "Bias simplification with a per-vertex importance map: important areas cost more to collapse, so they keep more detail. Pick the source with Importance Source. One setting for every LOD here; SimplyFive Pro sets the mask per LOD":
        "Смещает упрощение картой важности по вершинам: важные области дороже схлопывать, поэтому в них сохраняется больше деталей. Источник выбирается в Importance Source. Здесь это одна настройка на все LOD; в SimplyFive Pro маска задаётся для каждого LOD отдельно",
    "How much of the painted area is protected: the brightest share of it is marked high-priority for meshoptimizer, so 1.0 covers everything painted and 0.5 the brighter half. Not an absolute guarantee - very aggressive ratios can still reach into those areas. The same strength applies to every LOD here; SimplyFive Pro sets it per LOD, so a near LOD can anchor a little and a distant one all of it":
        "Какая доля закрашенной области защищается: самая яркая её часть помечается для meshoptimizer как приоритетная, поэтому 1.0 покрывает всё закрашенное, а 0.5 — более яркую половину. Не абсолютная гарантия — очень агрессивные проценты всё равно могут в них залезть. Здесь сила одна на все LOD; в SimplyFive Pro она задаётся для каждого LOD, так что близкий LOD может закрепить немного, а дальний — всё",
    "Also lock every vertex above the threshold outright, so it is never collapsed. Available in SimplyFive Pro - the mask here is a weight, which very aggressive ratios can still reach into":
        "Дополнительно жёстко блокирует каждую вершину выше порога, так что она не схлопнется никогда. Доступно в SimplyFive Pro — здесь маска работает как вес, в который очень агрессивные проценты всё равно могут залезть",
    "Normals of the finished LOD. Source normals stop matching the geometry at low polycounts.\nPreserve: carry the source normals over.\nRecalculate + Smooth: meshoptimizer generates them, then relaxes them, keeping edges above the angle hard.\nRecalculate + Auto Smooth: recompute from the LOD's own geometry, sharp above the angle.\nRecalculate + Sharp Loops: the same, but broken feature loops are closed":
        "Нормали готового LOD. На низком полигонаже исходные нормали перестают соответствовать геометрии.\nPreserve: перенести исходные нормали.\nRecalculate + Smooth: meshoptimizer считает их сам, затем расслабляет, оставляя рёбра круче угла хардовыми.\nRecalculate + Auto Smooth: пересчитать по геометрии самого LOD, жёсткие рёбра выше угла.\nRecalculate + Sharp Loops: то же, но разорванные линии деталей замыкаются",
    "meshopt_SimplifyRegularize: more uniform triangles, at some cost to appearance and triangle count.\nOff: no regularization.\nRegularize Light: milder uniformity bias.\nRegularize: full uniformity bias":
        "meshopt_SimplifyRegularize: более равномерные треугольники ценой внешнего вида и количества треугольников.\nOff: без регуляризации.\nRegularize Light: слабее выравнивает.\nRegularize: выравнивает полностью",
}


def _build_translations_dict():
    result = {}
    for source, translated in TRANSLATIONS_RU.items():
        result[("*", source)] = translated
    return {"ru_RU": result}
