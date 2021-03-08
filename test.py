#!/usr/bin/env python3

import requests
import sys
import time

verbose = len(sys.argv) > 1 and sys.argv[1] in ['-v', '--verbose']

start_time = time.monotonic()

#nl = 'buying clothes in Hannover'
nl = 'how many subway stations are there within walking distance of Alexanderplatz in Berlin?'
data = {
    'model': 'will_nlmaps_3delta.noise.plusv2_web2to1_ratio05_pilot.yaml',
    'nl': nl
}

if verbose:
    print(data)
response = requests.post('http://localhost:5050/translate', json=data)
duration = time.monotonic() - start_time
if verbose:
    print(response.status_code)
    print(response.text)
print(duration)
