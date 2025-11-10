#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mic_demo.py – Live-AEC-Demo (Mikrofon ↔ Lautsprecher)
-----------------------------------------------------
Voraussetzungen:
    pip install numpy sounddevice

Starte das Skript am besten mit Kopfhörer + externem Lautsprecher, damit ein
spürbares Echo existiert, das der LMS-Filter unterdrücken kann.
"""

import numpy as np
import sounddevice as sd
from lms import lms_filter  # <-- setzt die gepatchte Version voraus

FS = 48_000        # Abtastrate
BLOCK = 1024       # Blocklänge = Filterlänge
MU = 5e-4          # Schrittweite (µ)

coeffs = np.zeros(BLOCK, dtype=np.float32)  # Startkoeffizienten


def callback(indata, outdata, frames, time, status):
    """Sounddevice-Callback pro Audioblock."""
    global coeffs
    mic = indata[:, 0]           # Mikro-Kanal
    ref = outdata[:, 0].copy()   # Lautsprecher-Signal als Referenz

    # Einmaliges LMS-Update für diesen Block
    err, coeffs, _ = lms_filter(
        desired_signal=mic,
        reference_input=ref,
        filter_coeff=coeffs,
        step_sizes=[MU],
        safe=True
    )

    # Fehler (Echo-reduziertes Signal) ausgeben
    outdata[:, 0] = err.astype(np.float32)


print("Starte Live-Echo-Canceller … (Strg+C zum Abbrechen)")
try:
    with sd.Stream(channels=1, samplerate=FS, blocksize=BLOCK, callback=callback):
        while True:
            sd.sleep(1000)
except KeyboardInterrupt:
    print("Beendet.")

