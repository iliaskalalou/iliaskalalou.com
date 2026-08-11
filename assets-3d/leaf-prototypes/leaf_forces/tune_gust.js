/* Pick gust frequencies that minimise the strongest near-recurrence of the
   gust envelope over lags 2..120 s. Measured, not assumed. */
'use strict';

function recur(freqs, amps, phases, maxLag) {
  const DT = 1 / 20, T = 600;                 // 10 min of signal, 20 Hz
  const n = (T / DT) | 0;
  const s = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const t = i * DT;
    let v = 0;
    for (let k = 0; k < freqs.length; k++) v += amps[k] * Math.sin(freqs[k] * t + phases[k]);
    s[i] = v;
  }
  let mu = 0; for (let i = 0; i < n; i++) mu += s[i]; mu /= n;
  let sd = 0; for (let i = 0; i < n; i++) sd += (s[i] - mu) ** 2; sd = Math.sqrt(sd / n);
  let worst = Infinity, worstLag = 0;
  for (let lagS = 2; lagS <= maxLag; lagS += 0.05) {
    const lag = Math.round(lagS / DT);
    let a = 0, c = 0;
    for (let i = 0; i + lag < n; i += 4) { const d = (s[i] - s[i + lag]) / sd; a += d * d; c++; }
    const v = Math.sqrt(a / c) / Math.SQRT2;
    if (v < worst) { worst = v; worstLag = lagS; }
  }
  return { worst, worstLag };
}

const CANDIDATES = {
  'current (4 comp)': {
    f: [0.21130, 0.40900, 0.77170, 1.31090], a: [0.34, 0.30, 0.22, 0.14],
    p: [0.67, 1.31, 4.11, 2.23]
  },
  '5 comp, sqrt ratios': {
    f: [0.15710, 0.22210, 0.35120, 0.59830, 1.08470], a: [0.26, 0.23, 0.20, 0.17, 0.14],
    p: [0.67, 1.31, 4.11, 2.23, 5.02]
  },
  '5 comp, golden': {
    f: [0.14790, 0.23930, 0.38720, 0.62650, 1.01370], a: [0.26, 0.23, 0.20, 0.17, 0.14],
    p: [0.67, 1.31, 4.11, 2.23, 5.02]
  },
  '6 comp spread': {
    f: [0.13370, 0.19910, 0.31730, 0.49870, 0.80090, 1.29310],
    a: [0.23, 0.21, 0.19, 0.15, 0.12, 0.10],
    p: [0.67, 1.31, 4.11, 2.23, 5.02, 3.44]
  },
  '6 comp irrational': {
    f: [0.12790, 0.20730, 0.33590, 0.54410, 0.88130, 1.42790],
    a: [0.24, 0.21, 0.18, 0.15, 0.12, 0.10],
    p: [0.67, 1.31, 4.11, 2.23, 5.02, 3.44]
  },
  '7 comp': {
    f: [0.11310, 0.17690, 0.27670, 0.43290, 0.67730, 1.05950, 1.65750],
    a: [0.22, 0.19, 0.17, 0.14, 0.12, 0.09, 0.07],
    p: [0.67, 1.31, 4.11, 2.23, 5.02, 3.44, 1.88]
  }
};

console.log('worst near-recurrence of the gust envelope (higher = less loopy)');
console.log('0% = the signal exactly repeats at that lag, 100% = unrelated\n');
for (const [name, c] of Object.entries(CANDIDATES)) {
  const r30 = recur(c.f, c.a, c.p, 30);
  const r120 = recur(c.f, c.a, c.p, 120);
  const periods = c.f.map((f) => (2 * Math.PI / f).toFixed(1)).join(' / ');
  console.log(`${name.padEnd(22)}  within 30 s: ${(r30.worst * 100).toFixed(0)}% @${r30.worstLag.toFixed(1)}s` +
              `   within 120 s: ${(r120.worst * 100).toFixed(0)}% @${r120.worstLag.toFixed(1)}s`);
  console.log(`${''.padEnd(22)}  component periods: ${periods} s\n`);
}
