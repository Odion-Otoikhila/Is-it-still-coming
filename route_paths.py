"""Server-side lookups of GTFS shapes matched by trip ID."""
import csv
import sqlite3
from pathlib import Path

DATA = Path(__file__).parent / 'gtfs'
DB = DATA / 'route_shape_index.sqlite'

def build():
    if DB.exists():
        return
    if not (DATA / 'trips.txt').exists() or not (DATA / 'shapes.txt').exists():
        raise FileNotFoundError('Expected gtfs/trips.txt and gtfs/shapes.txt')
    tmp = DATA / 'route_shape_index.tmp.sqlite'
    tmp.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp)
    try:
        conn.execute('CREATE TABLE trips (trip_id TEXT PRIMARY KEY, shape_id TEXT)')
        conn.execute('CREATE TABLE points (shape_id TEXT, seq INTEGER, lat REAL, lon REAL)')
        with (DATA / 'trips.txt').open(newline='', encoding='utf-8-sig') as f:
            rows = ((r['trip_id'], r.get('shape_id') or '') for r in csv.DictReader(f))
            conn.executemany('INSERT OR REPLACE INTO trips VALUES (?, ?)', rows)
        with (DATA / 'shapes.txt').open(newline='', encoding='utf-8-sig') as f:
            batch=[]
            for r in csv.DictReader(f):
                batch.append((r['shape_id'],int(r['shape_pt_sequence']),float(r['shape_pt_lat']),float(r['shape_pt_lon'])))
                if len(batch)>=10000:
                    conn.executemany('INSERT INTO points VALUES (?,?,?,?)',batch)
                    batch.clear()
            if batch:
                conn.executemany('INSERT INTO points VALUES (?,?,?,?)',batch)
        conn.execute('CREATE INDEX idx_points ON points(shape_id, seq)')
        conn.commit()
    finally:
        conn.close()
    tmp.replace(DB)

def install(app):
    from flask import jsonify
    @app.get('/api/shape/<path:trip_id>')
    def shape_for_trip(trip_id):
        if not DB.exists():
            return jsonify({'error': 'GTFS shape index is not ready'}), 503
        with sqlite3.connect(DB) as conn:
            trip = conn.execute('SELECT shape_id FROM trips WHERE trip_id=?',(trip_id,)).fetchone()
            if not trip or not trip[0]:
                return jsonify({'error': 'No scheduled shape for this trip'}), 404
            points=conn.execute('SELECT lat,lon FROM points WHERE shape_id=? ORDER BY seq',(trip[0],)).fetchall()
        if len(points)<2:
            return jsonify({'error':'Missing path points'}),404
        return jsonify({'points':points})

if __name__ == '__main__':
    print('Building GTFS route index (first run only)...')
    build()
    print('Done. Route index created.')
