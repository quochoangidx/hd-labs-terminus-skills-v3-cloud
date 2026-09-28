# SOP QP-7: Relative expression from a real-time PCR plate

Molecular Biology Core Facility, standard operating procedure QP-7, edition 4.

This procedure governs how a plate export and its plate map are reduced to the
relative-expression report the facility returns to its users. Where the
reduction package and this procedure disagree, this procedure governs. Rule
numbers do not move between editions.

## 1. Units, figures and limits

1.1 A Ct (threshold cycle) is given in cycles, as a number with at most two
decimal places from 5.00 to 45.00, or as the word `Undetermined` for a well
whose signal never crossed the threshold. A standard's quantity is a relative
amount of template from 0.001 to 100000000.

1.2 No figure is rounded at any step. Mean Cts, amplification factors and fold
changes are carried and reported as computed.

1.3 This procedure provides for plates with one to four reference genes and one
to eight target genes, all gene names distinct; one to forty-eight samples, the
calibrator among them; one to six unknown wells for every sample and every gene;
for each gene, from no standards up to eight dilution levels of one to four
wells each, no two levels of a gene sharing a quantity; for each gene, from none
to four NTC wells; and at most 384 wells on the plate.

1.4 Wherever a gene has two or more curve points (2.4), the least-squares slope
through them lies from -4.20 to -2.90 cycles per decade.

1.5 No reportable replicate lies exactly 0.50 cycles from the median of the
reportable replicates of its sample and gene.

## 2. Terms

2.1 A well is determined when its Ct is a number. An `Undetermined` well is not
determined.

2.2 The cut-off cycle is 35.00. A reportable replicate of a gene in a sample is
an unknown well of that sample and gene that is determined and whose Ct is from
10.00 up to and including the cut-off cycle. A Ct earlier than 10.00 comes from
a baseline or saturation fault and is not reportable.

2.3 A gene is not detected in a sample when the sample has no reportable
replicate of it.

2.4 A dilution level of a gene is the set of the gene's standard wells that
share one quantity. A curve point is a dilution level with two or more
determined wells. Its Ct is the arithmetic mean of the Cts of those determined
wells, and its position is the base-10 logarithm of the level's quantity.
Standard wells that are not determined play no part in a curve point.

2.5 A gene's standard curve is the least-squares straight line of curve-point
Ct against position, fitted through the gene's curve points where the gene has
three or more of them. The slope of the line is in cycles per decade.

2.6 A gene is contaminated on the plate when one of its NTC wells has a Ct at or
below the cut-off cycle. An NTC well that is not determined, or whose Ct is
later than the cut-off cycle (primer-dimer signal), does not contaminate.

2.7 The calibrator is the sample the plate map names as calibrator. The
reference genes and the target genes are the genes the plate map lists under
those names.

## 3. Amplification

3.1 A gene's amplification factor is 10^(-1/s), where s is the slope of the
gene's standard curve. A factor above 2 (an efficiency above 100 per cent, as
inhibited concentrated standards often give) is used as it is; no ceiling is
put on the factor.

## 4. Replicates

4.1 Where a gene has three or more reportable replicates in a sample, each of
those replicates that lies more than 0.50 cycles from their median is an
outlier. The median of an even number of replicates is the mean of the middle
two.

4.2 A sample's mean Ct for a gene is the arithmetic mean of the sample's
reportable replicates of that gene that are not outliers.

4.3 A gene that is not detected in a sample has no mean Ct in that sample.
Nothing, neither the cut-off cycle nor the run length, is put in its place.

## 5. Relative expression

5.1 The relative quantity of a gene in a sample is A^(Ccal - Cs), where A is the
gene's amplification factor, Ccal the calibrator's mean Ct for the gene and Cs
the sample's mean Ct for it. Every gene, reference or target, is raised to its
own amplification factor.

5.2 A sample's normalisation factor is the geometric mean of the relative
quantities of all the reference genes in that sample.

5.3 A target's fold change in a sample is the target's relative quantity in the
sample divided by the sample's normalisation factor. The calibrator's fold
change is therefore 1.

5.4 A fold change needs the mean Ct of the target and of every reference gene,
both in the sample and in the calibrator, and needs none of those genes to be
contaminated. A result that lacks any of these has no fold change.

## 6. Report

6.1 The report gives one gene entry for every gene, the reference genes first
and then the target genes, each in plate-map order. A gene entry gives the
gene's amplification factor and whether the gene is contaminated.

6.2 The report gives one result for every sample and every target gene: the
samples in code-point order of their names and, within a sample, the target
genes in plate-map order. A result gives the target's mean Ct in the sample
(`null` when the target is not detected in the sample), the fold change
(`null` when there is none) and the flags.

6.3 A result's flags are drawn from these, in this order and each at most once:
`ntc` when the target or a reference gene is contaminated; `ref` when a
reference gene is not detected in the sample or in the calibrator; `nd` when the
target is not detected in the sample or in the calibrator. A result has a fold
change exactly when it has no flag.
