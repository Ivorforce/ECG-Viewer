import functools
from typing import Literal
from scipy.signal import iirfilter, sosfilt, sosfiltfilt

import numpy as np

fclasses = Literal['bessel', 'butter', 'ellip', 'cheby1', 'cheby2']


def filter(
    x: np.ndarray,
    fs: float,
    *,
    lower_bound_hz: float = None,
    upper_bound_hz: float = None,
    band_stop: bool = False,
    fclass: fclasses,
    order: int,
    two_way: bool,
    max_ripple: float = None,
    min_attenuation: float = None,
    padtype='odd',
    padlen=None,
    axis=-1
):
    """
    Apply a highpass or lowpass filter to a signal.

    - ... - optional batch dimensions
    - T - number of signal samples

    Args:
        x: signal [..., T]
        fs: sampling rate of the signal in Hz
        lower_bound_hz: lower bound in Hz
        upper_bound_hz: upper bound in Hz
        band_stop: if true, stop the band instead of retain it
        fclass: class of the filter
        order: order of the filter
        two_way: True to use the two-directional `filtfilt` instead of `filt`
        max_ripple: For Chebyshev and elliptic filters, provides the maximum ripple
            in the passband. (dB)
        min_attenuation: For Chebyshev and elliptic filters, provides the minimum
            attenuation in the stop band. (dB)
        padtype: See filtfilt docs. Does not apply to single-direction filters.
        padlen: See filtfilt docs. Does not apply to single-direction filters.
        axis: axis of x to apply filter to

    Returns:
        filtered x, [..., T]
    """
    if lower_bound_hz is None and upper_bound_hz is None:
        # No action; if bandstop is used however no frequencies are accepted, so 0 is the answer
        return x if not band_stop else np.zeros_like(x)

    if lower_bound_hz is not None and upper_bound_hz is not None:
        btype = "bandstop" if band_stop else "bandpass"
        Wn = [lower_bound_hz, upper_bound_hz]
    elif upper_bound_hz is not None:
        btype = "highpass" if band_stop else "lowpass"
        Wn = upper_bound_hz
    else:  # lower_bound_hz is not None
        btype = "lowpass" if band_stop else "highpass"
        Wn = lower_bound_hz

    sos = iirfilter(
        N=order, Wn=Wn, fs=fs,
        btype=btype, output="sos", ftype=fclass, rp=max_ripple, rs=min_attenuation
    ).astype(x.dtype)
    filter_fn = functools.partial(sosfiltfilt, padtype=padtype, padlen=padlen) if two_way else sosfilt

    return filter_fn(sos, x, axis=axis)
