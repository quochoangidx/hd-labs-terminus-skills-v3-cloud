# NPM-4: local magnitude

Brennock Range Seismic Network, Network Processing Manual, part 4.

This part says how the bulletin's local magnitudes (ML) are worked out from the
amplitude picks of a located event. Where the bulletin package and this part
disagree, this part governs. Section and rule numbers do not change between
editions, because analysts cite them in review notes.

## 0. Units and figures

0.1 Distances and depths are in kilometres. Amplitudes and noise are in
nanometres of ground displacement as seen through a simulated Wood–Anderson
seismometer. Record amplitudes are in millimetres on that seismometer's record.

0.2 Logarithms are to base ten.

0.3 Nothing in this part is rounded. The bulletin rounds magnitudes to one
decimal when it is published; that step belongs to the publishing manual, not to
this part, and the package reports every figure unrounded.

## 1. The bulletin file

1.1 A bulletin file is a JSON object with two keys.

- `stations`, the station table: one to two hundred entries, each with a `code`
  (one to five capital letters or digits, distinct within the table) and a
  `correction`, the station's magnitude correction, from −1.0 to +1.0.
- `events`: one to fifty events in the order the locator released them. Each
  has an `id` (one to twenty characters, distinct within the file), a
  `depth_km` from 0 to 60, and `recordings`, one to forty of them.

1.2 A recording is one sensor's share of an event at a station. It names the
station by `code` (a station of the table), gives the station's epicentral
distance `epi_km` from 0 to 1000, and lists one or two `amplitudes`, one for
each horizontal channel of that sensor the picker measured. Sites whose
broadband and strong-motion sensors are processed separately send one recording
for each, so a station has one or two recordings in an event; two recordings of
one station in one event give the same `epi_km`. An amplitude gives its
`channel` (a three-character channel code; no two amplitudes of a station in one
event have the same channel), `amplitude_nm` from 0.1 to 10^8, and the noise of that
channel, `noise_nm`, from 0.01 to 10^7. No amplitude comes within one part in a
thousand of three times the noise of its channel (rule 2.3). No station lies
closer than 1 km to the hypocentre (rule 3.1), and none lies within a metre of
either end of the distance table, 10 km or 600 km (rule 3.2).

1.3 Every recording carries at least one reading (rule 2.3).

## 2. Amplitudes

2.1 The network's picker measures every amplitude on a horizontal component of
the simulated Wood–Anderson record, peak to peak: from the largest swing of the
S wave train to the opposite swing next to it. It measures a channel's noise the
same way, peak to peak, over the window before the P arrival.

2.2 The record amplitude of an amplitude is half of its peak-to-peak value,
expressed in millimetres on a record of static magnification 2080:
`amplitude_nm / 2 × 2080 × 10^-6` mm. Richter's tables assumed the nominal
magnification of 2800; the network uses the 2080 the instrument actually
delivers.

2.3 A reading is an amplitude at least three times the noise of its channel.

## 3. Distance

3.1 A station's distance is its hypocentral distance: the square root of the sum
of the squares of its epicentral distance and the event's depth. Richter drew his
correction against epicentral distance; the network uses hypocentral distance at
every range. Station elevation is not used.

3.2 The distance correction −log A0 is the network's own calibration of 2019:

| distance (km) | −log A0 |
|---:|---:|
| 10 | 1.700 |
| 20 | 2.060 |
| 30 | 2.290 |
| 50 | 2.580 |
| 75 | 2.820 |
| 100 | 3.000 |
| 150 | 3.300 |
| 200 | 3.530 |
| 300 | 3.900 |
| 400 | 4.220 |
| 500 | 4.510 |
| 600 | 4.790 |

The table runs from 10 km to 600 km, and this part gives no correction for a
distance outside it. It is close to the Hutton–Boore curve and to the IASPEI
formula without being either, and neither is used in its place.

3.3 At a listed distance the correction is the listed value. Between two listed
distances it is interpolated linearly in distance. Some agencies interpolate on
the logarithm of distance; the network does not.

## 4. Station magnitude

4.1 Each reading gives a channel magnitude: the logarithm of its record
amplitude, plus the distance correction at the station's distance, plus the
station's correction.

4.2 A station's correction is added as it stands in the table, so a station that
reads high carries a negative correction.

4.3 A station's magnitude is the mean of the channel magnitudes of its readings.
The network does not take the largest channel alone, as some agencies do.

## 5. Network magnitude

5.1 A station contributes to the network magnitude when its distance lies within
the table, from 10 km to 600 km, both ends included.

5.2 The network magnitude of an event is the median of the station magnitudes of
its contributing stations: the middle one of an odd number of them, the mean of
the two middle ones of an even number. A mean over the stations is not used, so
that one misbehaving station cannot move the event far.

5.3 An event with fewer than three contributing stations has no network
magnitude.

## 6. The report

6.1 The report is a JSON object with the single key `events`, listing the
bulletin's events in file order. Each event is an object with its `id`; `ml`, its
network magnitude, or null when it has none; and `stations`, one object per
recording in the order of its recordings. Each of those has the station's `code`,
`distance_km` (rule 3.1), `ml` (the station magnitude, rule 4.3) and
`contributes` (true or false, rule 5.1).

6.2 The report carries no other keys.
