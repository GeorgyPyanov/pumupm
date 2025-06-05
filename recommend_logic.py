import math
import random
import sqlite3


def get_shop_link(item_name, value):
    """Получение ссылки на товар из БД configurator.db (таблица links)"""
    try:
        conn = sqlite3.connect("configurator.db")
        cursor = conn.cursor()

        query = "SELECT link FROM links WHERE name = ?"
        params = [item_name]

        if len(value) == 2:
            query += " AND value1 = ? AND value2 = ?"
            params.extend(value)
        elif len(value) == 1:
            query += " AND value1 = ? AND (value2 IS NULL OR value2 = '-')"
            params.append(value[0])
        else:
            query += " AND (value1 IS NULL OR value1 = '-') AND (value2 IS NULL OR value2 = '-')"

        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()

        if row:
            return row[0]
    except Exception as e:
        print(f"[DB ERROR] {e}")

    return "https://microart.ru/products/vse-tovary"


def recommend_configuration(power_max_kw, usage_wh_hour, inverter_v):
    battery_variants = {
        "12В 100А·ч": 12 * 100,
        "12В 200А·ч": 12 * 200,
        "12В 300А·ч": 12 * 300,
        "24В 230А·ч": 24 * 230
    }
    panel_power_options = [540, 435, 320, 360, 450, 400, 600, 480, 240, 250, 300, 370, 440]  # Вт, от больших к меньшим
    panel_hours = 4
    solar_target_wh = usage_wh_hour * 24  # Вт·ч суточная норма
    wind_models = [3000, 2000, 1000, 500]  # Вт
    inverter_options = [(48, 10), (48, 15), (24, 3.5), (24, 5), (24, 7), (24, 10), (12, 3.5)]  #кВт
    dgu_options = [5.5, 6, 7, 8, 10, 12.5]  # кВт

    # 1. АКБ: (потребление в час * 30) + 40%
    battery_required_wh = math.ceil(usage_wh_hour * 30 * 1.4)
    # Выбираем минимальный аккумулятор, чтобы покрыть нужную емкость
    battery_name, battery_capacity_wh = min(
        battery_variants.items(), key=lambda x: -(-battery_required_wh // x[1]))  # округление вверх делением
    battery_count = math.ceil(battery_required_wh / battery_capacity_wh)

    # 2. Солнечные панели — считаем сколько панелей нужно чтобы выдать энергию за 4 часа пика
    required_pv_kw = solar_target_wh / panel_hours / 1000  # кВт
    random.shuffle(panel_power_options)
    for p in panel_power_options:
        count = math.ceil(required_pv_kw * 1000 / p)
        # Выбираем первый вариант, где общая мощность не превышает power_max_kw, иначе берем минимальный
        if count * p / 1000 <= power_max_kw and count % 2 == 0:
            panel_power = p
            panel_count = count
            break
    else:
        # Если не подошёл ни один вариант, берем минимальный по мощности панели и нужное количество
        panel_power = panel_power_options[-1]
        panel_count = math.ceil(required_pv_kw * 1000 / panel_power)

    total_pv_kw = panel_power * panel_count / 1000

    # 3. Ветрогенераторы — выбираем одну мощность, максимально близкую
    random.shuffle(wind_models)
    usage_wh_day = usage_wh_hour * 24

    # Подбираем минимально достаточную мощность ветрогенератора из списка
    for power in wind_models:
        needed_count = math.ceil(usage_wh_day / (power * 4))
        # Берем первый вариант, где количество не слишком большое (например, меньше 10)
        if needed_count <= 10:
            chosen_wind_power = power
            wind_count = needed_count
            break
    else:
        # Если слишком много, берем самый мощный и считаем сколько надо
        chosen_wind_power = max(wind_models)
        wind_count = math.ceil(usage_wh_day / (chosen_wind_power * 4))

    total_wind_kw = chosen_wind_power * wind_count / 1000

    # 4. Инвертор — покрывает максимум из нагрузки и ВИЭ (солнечные + ветровые)
    max_vie_kw = total_pv_kw + total_wind_kw
    max_load_kw = max(max_vie_kw, power_max_kw)
    for inv in sorted(inverter_options):
        if inverter_v <= inv[0] and inv[1] >= max_load_kw:
            inverter_v, suitable_inverter = inv
            break
    else:
        inverter_v, suitable_inverter = sorted(inverter_options)[-1]

    # 5. ДГУ — выбираем одну мощность, несколько штук чтобы покрыть max_load_kw
    dgu_capacity = None
    dgu_count = 0
    for option in dgu_options:
        if option >= max_load_kw:
            dgu_capacity = option
            dgu_count = 1
            break
    if dgu_capacity is None:
        dgu_capacity = dgu_options[-1]
        dgu_count = math.ceil(max_load_kw / dgu_capacity)

    # Пожарная система и доп оборудование
    fire_systems = [
        "Порошковая система пожаротушения",
        "Водяная система",
        "Автоматическая система с датчиками температуры"
    ]
    fire_system = random.choice(fire_systems)

    controllers = [
        "MPPT контроллер 40A",
        "Солнечный контроллер",
        "Стабилизатор напряжения",
        "УЗИП",
        "Батарейный модуль"
    ]
    extras = random.sample(controllers, 3)

    # Структурируем вывод
    main_equipment = {
        "АКБ": f"{battery_count} шт. {battery_name} (общая емкость: {battery_required_wh} Вт·ч)",
        "Инвертор": f"{suitable_inverter} кВт / {inverter_v} В",
        "Солнечные панели": f"{panel_count} шт. по {panel_power} Вт",
        "Ветрогенераторы": f"{wind_count} шт. по {chosen_wind_power} Вт",
        "ДГУ": f"{dgu_count} шт. по {dgu_capacity} кВт",
        "Пожарная система": fire_system
    }

    data_equipment = {
        "АКБ": [battery_name],
        "Инвертор": [inverter_v, suitable_inverter],
        "Солнечные панели": [panel_power],
        "Ветрогенераторы": [chosen_wind_power],
        "ДГУ": [dgu_capacity],
        "Пожарная система": [fire_system]
    }

    extras_with_links = [{"name": e, "link": get_shop_link(e, [])} for e in extras]

    return {
        "main": main_equipment,
        "extras": extras_with_links,
        "links": data_equipment
    }