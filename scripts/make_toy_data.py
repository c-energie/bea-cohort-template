"""Write the template's toy data: two households, one week, hourly. Stdlib only, deterministic.

Not rendered: it lives in the template repository and writes into ``template/``, so the rendered
CSVs are committed files. Rerun it only to change the toy, and commit what it writes::

    python scripts/make_toy_data.py

Each household's heat is ``H * (temp_int - temp_ext) - g * solar`` W, metered as gas, over a flat
electrical base load, with a little noise. The MLR fit in the rendered toy test finds about these
``H`` values plus 17-20 W/K, the base load counted as heat; the toy test's tolerance assumes so.
"""
import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOY_DIR = Path(__file__).resolve().parents[1] / 'template' / 'src' / '{{ import_name }}' / 'toy_data'

START = datetime(2024, 1, 8, tzinfo=timezone.utc)
HOURS = 7 * 24

#: ``{puprn: (H in W/K, g in m2, floor area in m2)}``.
HOUSEHOLDS = {'TOY01': (180.0, 2.0, 95.0), 'TOY02': (120.0, 1.5, 70.0)}

ELEC_BASE_KWH = 0.3


def stamp(hour: int) -> str:
    return (START + timedelta(hours=hour)).strftime('%Y-%m-%dT%H:%M:%SZ')


#: Each day's mean outdoor temperature (degC) and clear-sky fraction. A static model fits daily
#: means, so H and g are only told apart by weather that differs from one day to the next.
DAYS = [(6.0, 0.3), (2.0, 0.9), (-1.0, 1.0), (3.0, 0.5), (8.0, 0.1), (5.0, 0.7), (0.0, 0.4)]


def weather(hour: int, rng: random.Random) -> tuple:
    """``(temp_ext degC, solar W/m2)`` at ``hour``."""
    mean_temp, clear_sky = DAYS[hour // 24]
    of_day = hour % 24
    temp_ext = mean_temp + 3 * math.sin(2 * math.pi * (of_day - 9) / 24) + rng.gauss(0, 0.3)
    solar = clear_sky * max(0.0, 400 * math.sin(math.pi * (of_day - 8) / 8)) if 8 <= of_day <= 16 else 0.0
    return round(temp_ext, 2), round(solar, 1)


def writer_of(file):
    """A CSV writer with LF line endings, so the committed files are the same on every OS."""
    return csv.writer(file, lineterminator='\n')


def main():
    rng = random.Random(20240108)
    TOY_DIR.mkdir(parents=True, exist_ok=True)
    climate = [weather(hour, rng) for hour in range(HOURS)]

    with open(TOY_DIR / 'climate.csv', 'w', newline='') as file:
        writer = writer_of(file)
        writer.writerow(['timestamp', 'air_temp_c', 'solar_w_m2'])
        writer.writerows([stamp(hour), *climate[hour]] for hour in range(HOURS))

    energy, in_home = [], []
    for puprn, (htc, aperture, _) in HOUSEHOLDS.items():
        for hour in range(HOURS):
            temp_ext, solar = climate[hour]
            temp_int = 20 + 0.5 * math.sin(2 * math.pi * (hour % 24 - 14) / 24) + rng.gauss(0, 0.2)
            heat_w = max(0.0, htc * (temp_int - temp_ext) - aperture * solar)
            gas_kwh = heat_w / 1000 * (1 + rng.gauss(0, 0.03))
            elec_kwh = ELEC_BASE_KWH * (1 + rng.gauss(0, 0.1))
            energy.append([puprn, stamp(hour), round(elec_kwh, 3), round(max(gas_kwh, 0.0), 3)])
            in_home.append([puprn, stamp(hour), round(temp_int, 2)])

    with open(TOY_DIR / 'energy.csv', 'w', newline='') as file:
        writer = writer_of(file)
        writer.writerow(['puprn', 'timestamp', 'elec_kwh', 'gas_kwh'])
        writer.writerows(energy)

    with open(TOY_DIR / 'in_home.csv', 'w', newline='') as file:
        writer = writer_of(file)
        writer.writerow(['puprn', 'timestamp', 'living_room_temp_c'])
        writer.writerows(in_home)

    with open(TOY_DIR / 'households.csv', 'w', newline='') as file:
        writer = writer_of(file)
        writer.writerow(['puprn', 'floor_area_m2'])
        writer.writerows([puprn, area] for puprn, (_, _, area) in HOUSEHOLDS.items())

    print(f'wrote {sum(path.stat().st_size for path in TOY_DIR.iterdir())} bytes to {TOY_DIR}')


if __name__ == '__main__':
    main()
