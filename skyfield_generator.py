#!/usr/bin/env python3

import argparse
from datetime import datetime
from pytz import timezone

from geopy import Nominatim
from tzwhere import tzwhere

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle

from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos, stellarium
from skyfield.projections import build_stereographic_projection


def load_data():
    eph = load('de421.bsp')
    with load.open(hipparcos.URL) as f:
        stars = hipparcos.load_dataframe(f)

    url = 'https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/indian/constellationship.fab'
    with load.open(url) as f:
        constellations = stellarium.parse_constellations(f)

    return eph, stars, constellations


def parse_args():
    parser = argparse.ArgumentParser(description='Generate a star chart from given location and time.')
    parser.add_argument('--latitude', type=float, required=True, help='Latitude of observer (e.g. 28.679079)')
    parser.add_argument('--longitude', type=float, required=True, help='Longitude of observer (e.g. 77.069710)')
    parser.add_argument('--date', type=str, default=None,
                        help='Date in format YYYY-MM-DD (e.g. 2025-01-01)')
    parser.add_argument('--timezone', type=str, default='Asia/Kolkata',
                        help='Timezone string (e.g. Asia/Kolkata). Default: Asia/Kolkata')
    parser.add_argument('--magnitude', type=float, default=1.0,
                        help='Limiting magnitude for stars. Default: 1.0')
    return parser.parse_args()


def main():
    args = parse_args()
    ts = load.timescale()

    if args.date:
        try:
            dt = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD.")
    else:
        dt = datetime.utcnow()

    tz = timezone(args.timezone)
    localized_dt = tz.localize(dt)
    t = ts.from_datetime(localized_dt)

    # Load skyfield data
    eph, stars, constellations = load_data()

    observer = wgs84.latlon(latitude_degrees=args.latitude, longitude_degrees=args.longitude).at(t)
    ra, dec, distance = observer.radec()
    center_object = Star(ra=ra, dec=dec)

    center = eph['earth'].at(t).observe(center_object)
    projection = build_stereographic_projection(center)

    star_positions = eph['earth'].at(t).observe(Star.from_dataframe(stars))
    stars['x'], stars['y'] = projection(star_positions)

    edges = [edge for name, edges in constellations for edge in edges]
    edges_star1 = [star1 for star1, star2 in edges]
    edges_star2 = [star2 for star1, star2 in edges]

    bright_stars = (stars.magnitude <= args.magnitude)
    magnitude = stars['magnitude'][bright_stars]

    xy1 = stars[['x', 'y']].loc[edges_star1].values
    xy2 = stars[['x', 'y']].loc[edges_star2].values
    lines_xy = np.rollaxis(np.array([xy1, xy2]), 1)

    # Plotting
    fig, ax = plt.subplots(figsize=(10, 10))
    border = plt.Circle((0, 0), 1, color='navy', fill=True)
    ax.add_patch(border)

    ax.add_collection(LineCollection(lines_xy, colors='#FDFFFC', alpha=0.5))

    marker_size = 100 * 40 ** (magnitude / -2.5)
    ax.scatter(stars['x'][bright_stars], stars['y'][bright_stars],
               s=marker_size, color='white', marker='.', linewidths=0, zorder=2)

    horizon = plt.Circle((0, 0), radius=1, transform=ax.transData)
    for col in ax.collections:
        col.set_clip_path(horizon)

    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    plt.axis('off')
    plt.title(f"Star Chart\n{localized_dt.strftime('%Y-%m-%d %H:%M %Z')} at ({args.latitude}, {args.longitude})")
    plt.show()


if __name__ == '__main__':
    main()
