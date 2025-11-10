import numpy as np

def rls_filter(desired_signal, reference_input, filter_coeff, reg_param, lambda_val=0.9):
    """
    RLS (Recursive Least Squares) adaptive filter implementation.

    RLS (Recursive Least Squares): Ein rekursiver Algorithmus, der eine inverse Korrelationsmatrix verwendet, um die Filterkoeffizienten schnell und präzise anzupassen.
    
    Args:
    - desired_signal: Desired output signal (d)
    - reference_input: Input reference signal (u)
    - filter_coeff: Initial filter coefficients (f)
    - reg_param: Regularization parameter for the inverse correlation matrix
    - lambda_val: Forgetting factor (default is 0.9)

    Returns:
    - f_adaptive: Adapted filter coefficients
    - error: Error between desired and estimated signal
    """
    f_len = len(filter_coeff)
    s_len = len(desired_signal)
    
    P = np.eye(f_len) / reg_param  # Inverse correlation matrix, initialized with regularization
    w = np.zeros(f_len)  # Initial filter weights
    e = np.zeros(s_len)  # Error signal
    
    # Iterate through the signal and update filter
    for l in range(f_len, s_len):
        u_block = reference_input[l:l - f_len:-1]  # Take a block of reference input
        k = np.dot(P, u_block) / (lambda_val + np.dot(u_block.T, np.dot(P, u_block)))  # Gain vector
        prior_e = desired_signal[l] - np.dot(w.T, u_block)  # Prior estimation error
        w = w + k * prior_e  # Update filter weights
        P = (1 / lambda_val) * (P - np.outer(k, np.dot(u_block.T, P)))  # Update inverse correlation matrix
        e[l] = desired_signal[l] - np.dot(w.T, u_block)  # Final estimation error
    
    return w, e

# Beispiel-Test: Zufallsdaten für den RLS-Filter
desired_signal = np.random.randn(1000)
reference_input = np.random.randn(1000)
filter_coeff = np.random.randn(10)  # Anfangswerte für Filterkoeffizienten
reg_param = 0.1  # Regularisierungsparameter

# Aufruf der RLS-Funktion
f_adaptive, error = rls_filter(desired_signal, reference_input, filter_coeff, reg_param)

f_adaptive[:10], error[:10]  # Anzeige der ersten 10 Werte der Filterkoeffizienten und Fehler
