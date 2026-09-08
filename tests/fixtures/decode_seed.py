"""Decode compact seed lines 'T|first|n|weekend:0|skipped,weekdays|c1,c2,...' into data/prices/T.csv."""
import csv, sys
from datetime import date, timedelta
for line in open(sys.argv[1]):
    line=line.strip()
    if not line: continue
    t, first, n, _, skip, closes = line.split('|')
    skip = set(skip.split(',')) if skip else set()
    closes = closes.split(','); n=int(n)
    rows=[]; d=date.fromisoformat(first); i=0
    while i < len(closes):
        if d.weekday() < 5 and d.isoformat() not in skip:
            rows.append((d, closes[i])); i += 1
        d += timedelta(days=1)
    assert len(rows)==n, (t, len(rows), n)
    with open(f'data/prices/{t}.csv','w',newline='') as f:
        w=csv.writer(f); w.writerow(['date','close'])
        for d,c in rows: w.writerow([d.isoformat(), c])
    print(t, len(rows), rows[0][0], rows[-1][0], 'last', rows[-1][1])
