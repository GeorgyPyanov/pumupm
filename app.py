import calendar
import io
import traceback
from functools import lru_cache
import requests
from flask import Flask, request, jsonify, render_template, make_response
from geopy.geocoders import Nominatim
import datetime
import logging
from logging.handlers import RotatingFileHandler
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from flask_cors import CORS

from recommend_logic import get_shop_link, recommend_configuration

app = Flask(__name__)
CORS(app)
geolocator = Nominatim(user_agent="aips_configurator")

SEASONS = {
    'Зима': [12, 1, 2],
    'Весна': [3, 4, 5],
    'Лето': [6, 7, 8],
    'Осень': [9, 10, 11]
}


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]')
    file_handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


logger = setup_logging()


# Дебаггер
class DebugTracker:
    def __init__(self):
        self.debug_data = {
            'start_time': datetime.datetime.now(),
            'steps': [],
            'warnings': [],
            'errors': []
        }

    def add_step(self, message):
        self.debug_data['steps'].append({
            'time': datetime.datetime.now(),
            'message': message,
            'type': 'step'
        })
        logger.debug(f"Step: {message}")

    def add_warning(self, message):
        self.debug_data['warnings'].append({
            'time': datetime.datetime.now(),
            'message': message,
            'type': 'warning',
            'trace': traceback.format_stack()
        })
        logger.warning(f"Warning: {message}")

    def add_error(self, message, exc_info=None):
        self.debug_data['errors'].append({
            'time': datetime.datetime.now(),
            'message': message,
            'type': 'error',
            'trace': traceback.format_exc() if exc_info else traceback.format_stack()
        })
        logger.error(f"Error: {message}", exc_info=exc_info)

    def get_debug_report(self):
        return {
            'execution_time': str(datetime.datetime.now() - self.debug_data['start_time']),
            'steps': self.debug_data['steps'][-10:],
            'warnings': self.debug_data['warnings'][-5:],
            'errors': self.debug_data['errors']
        }


pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSansCondensed.ttf'))


def generate_pdf_reportlab(data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    x_margin = 20 * mm
    y = height - 20 * mm

    # Заголовок
    c.setFont('DejaVuSans', 16)
    c.drawCentredString(width / 2, y, 'Конфигурация автономных источников энергии')
    y -= 15 * mm

    # Координаты
    c.setFont('DejaVuSans', 12)
    coords = data['coords']
    c.drawString(x_margin, y, f"Координаты: {coords['lat']:.4f}°, {coords['lon']:.4f}°")
    y -= 10 * mm

    # Климатические данные
    c.setFont('DejaVuSans', 14)
    c.drawString(x_margin, y, "Климатические данные по сезонам:")
    y -= 8 * mm
    c.setFont('DejaVuSans', 12)

    # Таблица климатических данных
    col_widths = [30 * mm, 25 * mm, 25 * mm, 25 * mm]
    headers = ['Сезон', 'Темп. (°C)', 'Ветер (м/с)', 'Солнце']

    # Заголовки таблицы
    for i, header in enumerate(headers):
        c.drawString(x_margin + sum(col_widths[:i]), y, header)
    y -= 6 * mm

    # Данные таблицы
    for season in ['Зима', 'Весна', 'Лето', 'Осень']:
        vals = data['climate'].get(season, {'temp': 0, 'wind': 0, 'solar': 0})
        c.drawString(x_margin + 0 * col_widths[0], y, season)
        c.drawString(x_margin + 1 * col_widths[0], y, str(vals['temp']))
        c.drawString(x_margin + 2 * col_widths[0], y, str(vals['wind']))
        c.drawString(x_margin + 3 * col_widths[0], y, str(vals['solar']))
        y -= 6 * mm
    y -= 5 * mm

    # Оборудование
    c.setFont('DejaVuSans', 14)
    c.drawString(x_margin, y, "Рекомендуемое оборудование:")
    y -= 8 * mm
    c.setFont('DejaVuSans', 12)

    # Основное оборудование с ссылками
    line_height = 6 * mm
    for name, val in data['config']['main'].items():
        link = data['config']['mainLinks'].get(name, '')

        # Рисуем текст как ссылку
        c.setFillColorRGB(0, 0, 1)  # Синий цвет для ссылок
        text = f"{name}: {val}"
        c.drawString(x_margin, y, text)

        # Добавляем активную ссылку
        if link:
            text_width = c.stringWidth(text, 'DejaVuSans', 12)
            print(str(link))
            c.linkURL(str(link), (x_margin, y - 2, x_margin + text_width, y + 10), relative=0)

        y -= line_height

    # Сбрасываем цвет обратно на черный
    c.setFillColorRGB(0, 0, 0)

    # Дополнительное оборудование
    extras = data['config'].get('extras', [])
    if extras:
        y -= 3 * mm
        c.setFont('DejaVuSans', 14)
        c.drawString(x_margin, y, "Дополнительное оборудование:")
        y -= 8 * mm
        c.setFont('DejaVuSans', 12)

        for item in extras:
            link = item.get('link', '')
            text = f"- {item['name']}"

            # Рисуем текст как ссылку
            c.setFillColorRGB(0, 0, 1)  # Синий цвет для ссылок
            c.drawString(x_margin, y, text)

            # Добавляем активную ссылку
            if link:
                text_width = c.stringWidth(text, 'DejaVuSans', 12)
                c.linkURL(link, (x_margin, y, x_margin + text_width, y + 4 * mm), relative=1)

            y -= line_height

        # Снова сбрасываем цвет
        c.setFillColorRGB(0, 0, 0)

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def get_season_dates(season: str, base_year: int):
    """Возвращает даты начала и конца сезона"""
    today = datetime.date.today()
    months = SEASONS[season]

    if season == 'Зима':
        # Зима: декабрь прошлого года + январь-февраль текущего
        start = datetime.date(base_year - 1, 12, 1)
        end = datetime.date(base_year, 2, calendar.monthrange(base_year, 2)[1])
    else:
        # Весна, Лето, Осень в пределах одного года
        start = datetime.date(base_year, months[0], 1)
        end_month = months[-1]
        end = datetime.date(base_year, end_month, calendar.monthrange(base_year, end_month)[1])

    # Корректировка для текущего года, если даты в будущем
    if start > today:
        start = start.replace(year=start.year - 1)
        end = end.replace(year=end.year - 1)
    if end > today:
        end = today

    return start, end


@lru_cache(maxsize=128)
def fetch_climate(lat, lon, season, base_year):
    """Получение климатических данных за весь сезон"""
    start, end = get_season_dates(season, base_year)
    days = (end - start).days + 1

    if days <= 0:
        return 0.0, 0.0, 0.0

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': start.isoformat(),
        'end_date': end.isoformat(),
        'daily': 'temperature_2m_max,temperature_2m_min,windspeed_10m_min,shortwave_radiation_sum',
        'timezone': 'auto'
    }

    try:
        response = requests.get(url, params=params, timeout=25)
        response.raise_for_status()
        data = response.json().get('daily', {})\
        # Проверка наличия данных
        if not data or 'time' not in data or len(data['time']) == 0:
            return 0.0, 0.0, 0.0

        temps_max = data.get('temperature_2m_max', [])
        temps_min = data.get('temperature_2m_min', [])
        winds = data.get('windspeed_10m_min', [])
        sols = data.get('shortwave_radiation_sum', [])  # В МДж/м²

        # Рассчитываем среднесезонные показатели
        valid_days = 0
        temp_sum = wind_sum = solar_sum = 0.0

        for i in range(len(data['time'])):
            # Пропускаем дни с отсутствующими данными
            if (i >= len(temps_max) or temps_max[i] is None or
                    i >= len(temps_min) or temps_min[i] is None or
                    i >= len(winds) or winds[i] is None or
                    i >= len(sols) or sols[i] is None):
                continue

            temp_avg = (temps_max[i] + temps_min[i]) / 2
            temp_sum += temp_avg
            wind_sum += winds[i]
            solar_kwh = sols[i] * 0.277778
            solar_sum += solar_kwh

            valid_days += 1

        if valid_days == 0:
            return 0.0, 0.0, 0.0

        return (
            round(temp_sum / valid_days, 1),
            round(wind_sum / valid_days, 1),
            round(solar_sum / valid_days, 2)
        )
    except Exception as e:
        logger.error(f"Climate API error for {season} {base_year}: {str(e)}")
        return 0.0, 0.0, 0.0


def process_request(lat, lon, power_max, usage_wh, inverter_v):
    debug = DebugTracker()
    debug.add_step("Starting request processing")

    try:
        climate = {}
        base_year = datetime.date.today().year - 1  # Для стабильных исторических данных

        for season in SEASONS.keys():
            try:
                temp, wind, solar = fetch_climate(lat, lon, season, base_year)
                climate[season] = {
                    'temp': temp,
                    'wind': wind,
                    'solar': solar
                }
                debug.add_step(f"Fetched climate for {season}: {temp}, {wind}, {solar}")
            except Exception as e:
                debug.add_error(f"Error fetching data for {season}: {e}")
                climate[season] = {'temp': 0.0, 'wind': 0.0, 'solar': 0.0}

        # Средние значения по сезонам
        avg_temp = sum(s['temp'] for s in climate.values()) / 4
        avg_wind = sum(s['wind'] for s in climate.values()) / 4
        avg_solar = sum(s['solar'] for s in climate.values()) / 4
        debug.add_step(f"Averages: temp={avg_temp}, wind={avg_wind}, solar={avg_solar}")

        config = recommend_configuration(power_max, usage_wh, inverter_v)
        debug.add_step("Configuration recommended")

        # Добавляем ссылочки
        config['mainLinks'] = {name: get_shop_link(name, val) for name, val in config['links'].items()}
        debug.add_step("Main links added")

        return {
            'coords': {'lat': lat, 'lon': lon},
            'climate': climate,
            'config': config,
            'debug': debug.get_debug_report()
        }

    except Exception as e:
        debug.add_error("Unhandled error in process_request", exc_info=True)
        return {
            'error': str(e),
            'debug': debug.get_debug_report()
        }


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/get_config')
def get_config():
    debug = DebugTracker()
    debug.add_step("Starting /get_config request")

    try:
        params = {
            'lat': request.args.get('lat'),
            'lon': request.args.get('lon'),
            'power_max': request.args.get('power_max', '12'),
            'usage_wh': request.args.get('usage', '300'),
            'inverter_v': request.args.get('inverter_v', '220')
        }
        debug.add_step(f"Received params: {params}")

        # Валидация параметров
        try:
            validated = {
                'lat': float(params['lat']),
                'lon': float(params['lon']),
                'power_max': float(params['power_max']),
                'usage_wh': float(params['usage_wh']),
                'inverter_v': float(params['inverter_v'])
            }
        except (TypeError, ValueError) as e:
            debug.add_error(f"Invalid parameters: {str(e)}")
            return jsonify({
                'error': "Invalid parameters",
                'debug': debug.get_debug_report() if app.debug else None
            }), 400

        debug.add_step("Parameters validated successfully")

        try:
            data = process_request(**validated)
            debug.add_step("Configuration generated successfully")
            return jsonify(data)

        except Exception as e:
            debug.add_error(f"Configuration generation failed: {str(e)}", exc_info=True)
            return jsonify({
                'error': "Configuration generation failed",
                'debug': debug.get_debug_report() if app.debug else None
            }), 500

    except Exception as e:
        debug.add_error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({
            'error': "Internal server error",
            'debug': debug.get_debug_report() if app.debug else None
        }), 500


@app.route('/get_pdf', methods=['POST'])
def get_pdf():
    try:
        data = request.get_json()
        if not data:
            return jsonify(error="No data"), 400
        pdf_bytes = generate_pdf_reportlab(data)
        resp = make_response(pdf_bytes)
        resp.headers['Content-Type'] = 'application/pdf'
        resp.headers['Content-Disposition'] = 'attachment; filename=config.pdf'
        return resp
    except Exception as e:
        logger.exception("get_pdf error")
        return jsonify(error=str(e)), 500


if __name__ == '__main__':
    app.run(debug=True)
