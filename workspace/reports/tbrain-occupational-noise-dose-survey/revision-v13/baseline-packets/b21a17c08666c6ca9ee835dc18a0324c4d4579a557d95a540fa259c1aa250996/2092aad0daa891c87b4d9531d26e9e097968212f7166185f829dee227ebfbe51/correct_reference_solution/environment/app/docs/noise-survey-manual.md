# Noise Survey Manual HC-4

Brenmoor Pressings, Hearing Conservation Programme. Fourth edition.

This manual is how the programme turns personal dosimeter surveys into the
exposure figures it reports for each worker and each similar-exposure group.
Where the survey package and this manual disagree, the manual governs. Rule
numbers do not move between editions.

The programme is stricter than the federal occupational noise rule in several
places. Each of those places says so; the programme's figure is the one to use.

## 1 Units, rounding and limits

1.1 A level is an A-weighted equivalent sound level in dBA and a peak is a
C-weighted peak sound level in dBC, each given to one decimal place. A length
of time is a whole number of minutes. A dose is a percentage.

1.2 Every figure is worked out from unrounded figures. A TWA is rounded to the
nearest tenth of a decibel when it is reported, an exact half going up, and a
status is judged on the TWA as reported. A dose is reported as worked out,
without rounding. Nothing else is rounded.

1.3 The mean of some figures is their sum divided by how many there are.

1.4 This manual provides for surveys within these limits, and each limit
includes its ends:

- a survey lists from 1 to 300 workers, under at most 40 different group codes;
- a worker's shift lasts from 60 to 1,440 minutes;
- a worker's log holds from 0 to 1,500 runs; a run lasts from 1 to 1,440
  minutes, and the runs of one log add up to no more than 2,880 minutes;
- a run's level is either 0.0 or from 40.0 to 140.0 dBA;
- a worker has from 0 to 500 peaks, each from 60.0 to 170.0 dBC;
- a worker id is 1 to 12 characters, each a capital letter, a digit or a
  hyphen, and no two workers in a survey share one; a group code is 1 to 8
  characters, each a capital letter or a digit.

## 2 Terms

2.1 A run is one entry of a worker's log: a length of time and the level the
dosimeter logged for it.

2.2 A reading is a run logged at 40.0 dBA or more, the bottom of the
dosimeter's measuring range.

2.3 The threshold level is 80.0 dBA. A counted reading is a reading at or above
the threshold level, and one logged no higher than the ceiling level is counted
at its own level. (The federal rule counts from 90 dBA when it judges the
permissible exposure; the programme counts from 80 dBA for every figure.)

2.4 A worker's sampled time is the total length of the worker's readings.

2.5 A partial survey is a survey whose sampled time is at least three quarters
of the worker's shift but shorter than the shift.

2.6 An impulse is a peak of 140.0 dBC or more.

2.7 A similar-exposure group, or group, is the set of workers in a survey who
share a group code. Those workers are its members.

## 3 Dose

3.1 The reference duration at a level L is 480 / 2^((L - 85) / 3) minutes. The
programme's criterion level is 85 dBA and its exchange rate is 3 dB. (The federal rule uses a 90 dBA criterion and a
5 dB exchange rate; neither applies here.)

3.2 A worker's measured dose is 100 times the sum, over the worker's counted
readings, of each reading's length divided by the reference duration at the
level it is counted at. A reading below the threshold level adds nothing to it.

3.3 A partial survey is projected to the worker's shift: its shift dose is its
measured dose multiplied by the length of the shift and divided by its sampled
time. A survey whose sampled time is the whole shift or longer has its
measured dose as its shift dose.

## 4 Time-weighted average

4.1 The TWA of a shift dose D above nought is 85 + 3 × log2(D / 100) dB, the
steady level that would give the same dose over eight hours. A shift dose of
nought has no TWA. (The federal formula, 90 + 16.61 × log10(D / 100), belongs
to the 90 dBA criterion and the 5 dB exchange rate and does not apply here.)

## 5 Status and flags

5.1 The ceiling level is 115.0 dBA. A worker is flagged for the ceiling when
one of the worker's readings is above the ceiling level.

5.2 A worker is flagged for impulse when one of the worker's peaks is an
impulse.

5.3 A worker's status is "over" when the worker is flagged for the ceiling or
for impulse, or when the worker's TWA is above 85.0 dB. Otherwise it is
"action" when the TWA is from 82.0 dB up to 85.0 dB, and "below" in every
other case, including when the worker has no TWA. (The federal action level
is 85 dB and its permissible exposure 90 dB; the programme acts earlier.)

## 6 Groups

6.1 A group's dose is the mean of its members' shift doses. The group's TWA
follows from that dose by 4.1, and its status is judged on that TWA alone by
the bands of 5.3; a group carries no ceiling or impulse flag.
