#!/usr/bin/env python3
"""HPA 동작 확인용 CPU 부하. 생성한 자식만 종료하며 각 자식에도 종료 시각을 둔다."""
import argparse
import datetime as dt
import json
import multiprocessing as mp
import time

def burn(seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        sum(i * i for i in range(20000))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--seconds', type=int, default=180)
    p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    if not 1 <= a.seconds <= 300 or not 1 <= a.workers <= 8:
        p.error('seconds 1..300, workers 1..8')
    workers = [mp.Process(target=burn, args=(a.seconds,)) for _ in range(a.workers)]
    print(json.dumps({'event':'start','at':dt.datetime.now(dt.timezone.utc).isoformat(),'seconds':a.seconds,'workers':a.workers}), flush=True)
    try:
        for w in workers:
            w.start()
        for w in workers:
            w.join(a.seconds + 5)
    finally:
        for w in workers:
            if w.is_alive():
                w.terminate()
            if w.pid is not None:
                w.join(5)
        print(json.dumps({'event':'stop','at':dt.datetime.now(dt.timezone.utc).isoformat(),'children_alive':sum(w.is_alive() for w in workers)}), flush=True)
