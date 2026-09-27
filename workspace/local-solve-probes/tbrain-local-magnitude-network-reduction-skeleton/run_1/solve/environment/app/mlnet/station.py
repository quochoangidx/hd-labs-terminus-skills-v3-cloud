"""Channel and station magnitudes."""

from .amplitude import log_record_amplitude
from .attenuation import minus_log_a0

# An amplitude is a reading when it is at least this many times its channel's
# noise (manual rule 2.3).
NOISE_FACTOR = 3.0


def is_reading(amplitude):
    """Whether one amplitude object of a recording is a reading (rule 2.3)."""
    return float(amplitude["amplitude_nm"]) >= NOISE_FACTOR * float(amplitude["noise_nm"])


def channel_magnitude(amplitude_nm, distance_km, correction):
    """Local magnitude from one channel's amplitude at a station (rule 4.1).

    ``correction`` is the station's entry in the station table, added as it
    stands (rule 4.2).
    """
    return log_record_amplitude(amplitude_nm) + minus_log_a0(distance_km) + float(correction)


def reading_magnitudes(amplitudes, distance_km, correction):
    """Channel magnitudes of the readings among ``amplitudes`` (rules 2.3, 4.1)."""
    return [
        channel_magnitude(item["amplitude_nm"], distance_km, correction)
        for item in amplitudes
        if is_reading(item)
    ]


def mean_magnitude(channel_magnitudes):
    """Mean of channel magnitudes, or ``None`` when there are none (rule 4.3)."""
    values = [float(value) for value in channel_magnitudes]
    if not values:
        return None
    return sum(values) / len(values)


def station_magnitude(amplitudes, distance_km, correction):
    """Local magnitude of one station from the amplitudes of its recording.

    ``amplitudes`` is the recording's list of amplitude objects, each with its
    ``channel``, ``amplitude_nm`` and ``noise_nm``.  The station's magnitude is
    the mean of the channel magnitudes of its readings (rule 4.3).
    """
    return mean_magnitude(reading_magnitudes(amplitudes, distance_km, correction))
