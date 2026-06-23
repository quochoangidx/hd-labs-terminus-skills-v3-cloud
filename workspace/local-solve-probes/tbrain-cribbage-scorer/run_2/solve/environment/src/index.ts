// Cribbage hand scorer.
//
// Reads four hand cards, one starter card, and an optional --crib flag, then
// prints the total score on the first line and a per-category breakdown JSON on
// the second line. The scoring engine below is only a skeleton: each category
// currently returns zero, so the totals it prints are wrong.

interface Card {
  rank: number; // 1..13 (A=1 .. K=13), used for runs and pair matching
  value: number; // 1..10 face value (A=1, 2..9 face, T/J/Q/K=10), used for fifteens
  suit: string; // one of S H D C
}

const RANKS: { [token: string]: number } = {
  A: 1,
  "2": 2,
  "3": 3,
  "4": 4,
  "5": 5,
  "6": 6,
  "7": 7,
  "8": 8,
  "9": 9,
  T: 10,
  J: 11,
  Q: 12,
  K: 13,
};

const SUITS = new Set(["S", "H", "D", "C"]);

function parseCard(token: string): Card {
  if (token.length !== 2) {
    throw new Error(`invalid card token: ${token}`);
  }
  const rankToken = token[0].toUpperCase();
  const suit = token[1].toUpperCase();
  if (!(rankToken in RANKS)) {
    throw new Error(`invalid rank: ${token}`);
  }
  if (!SUITS.has(suit)) {
    throw new Error(`invalid suit: ${token}`);
  }
  const rank = RANKS[rankToken];
  const value = Math.min(rank, 10);
  return { rank, value, suit };
}

interface Breakdown {
  fifteens: number;
  pairs: number;
  runs: number;
  flush: number;
  nobs: number;
}

function scoreFifteens(cards: Card[]): number {
  // Count every distinct subset of the cards whose face values sum to 15.
  // Each such subset is worth 2 points.
  const n = cards.length;
  let count = 0;
  for (let mask = 1; mask < 1 << n; mask++) {
    let sum = 0;
    for (let i = 0; i < n; i++) {
      if (mask & (1 << i)) {
        sum += cards[i].value;
      }
    }
    if (sum === 15) {
      count++;
    }
  }
  return count * 2;
}

function scorePairs(cards: Card[]): number {
  // Every distinct pair of cards sharing the same rank scores 2 points.
  let count = 0;
  for (let i = 0; i < cards.length; i++) {
    for (let j = i + 1; j < cards.length; j++) {
      if (cards[i].rank === cards[j].rank) {
        count++;
      }
    }
  }
  return count * 2;
}

function scoreRuns(cards: Card[]): number {
  // Runs are scored once per distinct combination of cards forming a maximal
  // run of length >= 3. Duplicated ranks multiply the run (double, triple,
  // double-double, etc). We find the longest run length present, then count
  // how many distinct combinations of cards produce a run of that length by
  // multiplying the counts of each rank in the run.
  const counts: { [rank: number]: number } = {};
  for (const c of cards) {
    counts[c.rank] = (counts[c.rank] || 0) + 1;
  }
  const ranks = Object.keys(counts)
    .map(Number)
    .sort((a, b) => a - b);

  let total = 0;
  let i = 0;
  while (i < ranks.length) {
    // Find a maximal consecutive sequence of distinct ranks.
    let j = i;
    while (j + 1 < ranks.length && ranks[j + 1] === ranks[j] + 1) {
      j++;
    }
    const runLength = j - i + 1;
    if (runLength >= 3) {
      let multiplier = 1;
      for (let k = i; k <= j; k++) {
        multiplier *= counts[ranks[k]];
      }
      total += runLength * multiplier;
    }
    i = j + 1;
  }
  return total;
}

function scoreFlush(hand: Card[], starter: Card, crib: boolean): number {
  const handSameSuit = hand.every((c) => c.suit === hand[0].suit);
  if (!handSameSuit) {
    return 0;
  }
  const starterMatches = starter.suit === hand[0].suit;
  if (crib) {
    // In the crib only a five-card flush counts.
    return starterMatches ? 5 : 0;
  }
  return starterMatches ? 5 : 4;
}

function scoreNobs(hand: Card[], starter: Card): number {
  // One point if the hand holds the jack matching the starter's suit.
  for (const c of hand) {
    if (c.rank === 11 && c.suit === starter.suit) {
      return 1;
    }
  }
  return 0;
}

function score(hand: Card[], starter: Card, crib: boolean): Breakdown {
  const all = [...hand, starter];
  return {
    fifteens: scoreFifteens(all),
    pairs: scorePairs(all),
    runs: scoreRuns(all),
    flush: scoreFlush(hand, starter, crib),
    nobs: scoreNobs(hand, starter),
  };
}

function main(argv: string[]): number {
  const args = argv.slice(2);
  let crib = false;
  const positional: string[] = [];
  for (const a of args) {
    if (a === "--crib") {
      crib = true;
    } else {
      positional.push(a);
    }
  }
  if (positional.length !== 5) {
    process.stderr.write(
      "usage: cribbage-score <c1> <c2> <c3> <c4> <starter> [--crib]\n"
    );
    return 1;
  }
  let cards: Card[];
  try {
    cards = positional.map(parseCard);
  } catch (e) {
    process.stderr.write(`${(e as Error).message}\n`);
    return 1;
  }
  const hand = cards.slice(0, 4);
  const starter = cards[4];
  const breakdown = score(hand, starter, crib);
  const total =
    breakdown.fifteens +
    breakdown.pairs +
    breakdown.runs +
    breakdown.flush +
    breakdown.nobs;
  process.stdout.write(`${total}\n`);
  process.stdout.write(`${JSON.stringify(breakdown)}\n`);
  return 0;
}

process.exit(main(process.argv));
