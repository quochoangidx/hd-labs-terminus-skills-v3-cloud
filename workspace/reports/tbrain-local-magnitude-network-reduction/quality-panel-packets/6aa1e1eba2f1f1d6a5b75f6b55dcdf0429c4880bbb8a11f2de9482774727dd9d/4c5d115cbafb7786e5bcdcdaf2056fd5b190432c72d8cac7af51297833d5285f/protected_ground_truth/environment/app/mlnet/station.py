"""Channel and station magnitudes."""

from .amplitude import log_record_amplitude
from .attenuation import minus_log_a0


def channel_magnitude(amplitude_nm, distance_km, correction):
    """Local magnitude from one channel's amplitude at a station.

    ``correction`` is the station's entry in the station table.
    """
    return log_record_amplitude(amplitude_nm) + minus_log_a0(distance_km) - correction


def station_magnitude(amplitudes, distance_km, correction):
    """Local magnitude of one station from the amplitudes of its recording.

    ``amplitudes`` is the recording's list of amplitude objects, each with its
    ``channel``, ``amplitude_nm`` and ``noise_nm``.
    """
    largest = max(float(item["amplitude_nm"]) for item in amplitudes)
    return channel_magnitude(largest, distance_km, correction)
