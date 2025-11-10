#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lms.py – Minimal-LMS-Implementierung mit optionalem Overflow-Schutz („safe“)

*   `lms_filter_safe`          – Wrapper für alte Beispiele
*   `lms_filter`               – eigentliche Routine
*   Demo unter  __main__       – läuft nur bei direktem Aufruf, nicht beim Import
"""

import numpy as np

# ------------------------------------------------------------------
# Rückwärts­kompatibilität: alter Funktions­name bleibt erhalten
# ------------------------------------------------------------------
def lms_filter_safe(*args, **kwargs):
    """Alias auf lms_filter (für vorhandene Skripte)."""
    return lms_filter(*args, **kwargs)

# ------------------------------------------------------------------
# Least-Mean-Squares-Filter
# ------------------------------------------------------------------
def lms_filter(
    desired_signal: np.ndarray,
    reference_input: np.ndarray,
    filter_coeff: np.ndarray,
    step_sizes: list[float],
    *,
    num_iterations: int | None = None,
    return_error: bool = True,
    safe: bool = False,
):
    """
    Einfaches LMS-Adaptive-Filter.

    Parameters
    ----------
    desired_signal : ndarray
        Ziel-/Referenz­signal d[n].
    reference_input : ndarray
        Eingangssignal u[n] (Echo-Quelle).
    filter_coeff : ndarray
        Startkoeffizienten f[0].
    step_sizes : list[float]
        Liste zu testender Schrittweiten µ.
    num_iterations : int | None
        Optional: Begrenze Iterationen (Standard = Länge des Signals).
    return_error : bool
        Liefere bei True das Fehler­signal e[n] mit zurück.
    safe : bool
        Clipt e[n] auf ±10 000 und rechnet kritische Schritte in float64.

    Returns
    -------
    e            : ndarray | None
    f_adaptive   : ndarray
    best_mu      : float
    """
    M = len(reference_input)
    if num_iterations is None or num_iterations > M:
        num_iterations = M

    best_total_error = np.inf
    best_mu = step_sizes[0]
    best_coeff = filter_coeff.copy()
    best_err = None

    for mu in step_sizes:
        e = np.zeros_like(reference_input, dtype=np.float32)
        f = filter_coeff.astype(np.float64)      # intern in float64 arbeiten

        for n in range(len(filter_coeff), num_iterations):
            u_block = reference_input[n : n - len(filter_coeff) : -1]

            # --- Fehler berechnen & sofort clippen -----------------------
            err = desired_signal[n] - np.dot(f, u_block)
            if safe:
                err = np.clip(err, -1e4, 1e4)
            e[n] = err

            # --- Koeffizienten­update (float64 → zurückcasten) -----------
            f += (mu * err * u_block).astype(np.float64)

        total_err = np.sum(np.square(e, dtype=np.float64))
        if total_err < best_total_error:
            best_total_error = total_err
            best_mu = mu
            best_coeff = f.astype(filter_coeff.dtype, copy=False)
            best_err = e.copy()

    return (best_err if return_error else None), best_coeff, best_mu


# ------------------------------------------------------------------
# Beispiel-Demo – läuft nur bei direktem Aufruf ---------------------
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("Running built-in LMS demo …")

    rng = np.random.default_rng(42)
    desired_signal  = rng.standard_normal(10_000).astype(np.float32)
    reference_input = rng.standard_normal(10_000).astype(np.float32)
    filter_coeff    = np.zeros(1024, dtype=np.float32)

    step_sizes = [1e-4, 5e-4, 1e-3]          # realistische µ-Werte

    err, f_adaptive, best_mu = lms_filter(
        desired_signal,
        reference_input,
        filter_coeff,
        step_sizes,
        safe=True
    )

    total_error = np.sum(np.square(err, dtype=np.float64))
    print(f"best µ: {best_mu}   |   total_error: {total_error:,.2f}")
