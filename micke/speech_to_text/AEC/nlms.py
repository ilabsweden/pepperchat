import numpy as np

def nlms_filter(desired_signal, reference_input, filter_coeff, step_size=0.05):
    """
    NLMS (Normalized Least Mean Squares) adaptive filter implementation.

    NLMS (Normalized LMS): Eine erweiterte Version des LMS, bei der die Schrittgröße normalisiert wird, um Stabilität bei verschiedenen Signalstärken zu gewährleisten.
    
    Args:
    - desired_signal: Desired output signal (d)
    - reference_input: Input reference signal (u)
    - filter_coeff: Initial filter coefficients (f)
    - step_size: Step size for the NLMS algorithm (mu)

    Returns:
    - f_adaptive: Adapted filter coefficients
    """
    M = len(reference_input)
    f_adaptive = filter_coeff
    e = np.zeros(len(reference_input))
    
    # Iterate through the signal and update filter
    for l in range(len(filter_coeff), M):
        u_block = reference_input[l:l - len(filter_coeff):-1]
        y = np.dot(f_adaptive, u_block)
        e[l] = desired_signal[l] - y
        
        # Normalize step size using the power of input signal
        p = np.dot(u_block, u_block)
        normalized_step_size = step_size / (p + 1)  # Adding 1 to avoid division by zero
        
        # Update filter coefficients
        f_adaptive += normalized_step_size * e[l] * u_block

    return f_adaptive, e

# Beispiel-Test: Zufallsdaten für den NLMS-Filter
desired_signal = np.random.randn(1000)
reference_input = np.random.randn(1000)
filter_coeff = np.random.randn(10)  # Anfangswerte für Filterkoeffizienten

# Aufruf der NLMS-Funktion
f_adaptive, error = nlms_filter(desired_signal, reference_input, filter_coeff)

f_adaptive[:10], error[:10]  # Anzeige der ersten 10 Werte der Filterkoeffizienten und Fehler
