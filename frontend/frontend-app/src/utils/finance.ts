
/**
 * Financial utility functions for IRR and NAV calculations using forward-compounding.
 */

export interface Investment {
  year: number;
  amount: number;
}

/**
 * Solves for the implied annual return rate (r) using a forward-compounding model.
 * 
 * Formula: V_T = sum_{t=0 to T-1} I_t * (1 + r)^(T - t)
 * We solve for r such that: f(r) = sum(I_t * (1 + r)^(T - t)) - V_T = 0
 * 
 * @param investments Array of {year, amount} objects.
 * @param finalYear The year T at which the final value is known.
 * @param finalValue The known final exit value V_T.
 * @returns The implied annual return rate r.
 */
export function computeImpliedReturnRate(
  investments: Investment[],
  finalYear: number,
  finalValue: number
): number {
  if (investments.length === 0) return 0;
  if (finalValue <= 0) return -1.0; // Total loss

  // Function to evaluate: f(r) = sum(I_i * (1 + r)^(T - t_i)) - V_T
  const f = (r: number): number => {
    let total = 0;
    const factor = 1 + r;
    for (const inv of investments) {
      // Only consider investments made up to T-1 (as per prompt)
      // or at T with power 0.
      if (inv.year <= finalYear) {
        total += inv.amount * Math.pow(factor, finalYear - inv.year);
      }
    }
    return total - finalValue;
  };

  // Binary search (bisection) for r
  let low = -0.99;
  let high = 10.0;
  const tolerance = 1e-7;
  const maxIterations = 100;

  // Initial checks to ensure the solution is within bounds
  if (f(low) > 0) return low; // Even at -99% return, we exceed finalValue
  if (f(high) < 0) {
    // If 1000% return is not enough, return high or continue search if needed.
    // We'll stick to the requested range but could be expanded.
    return high;
  }

  for (let i = 0; i < maxIterations; i++) {
    const mid = (low + high) / 2;
    const val = f(mid);

    if (Math.abs(val) < tolerance) {
      return mid;
    }

    if (val > 0) {
      // r is too high, value exceeds V_T
      high = mid;
    } else {
      // r is too low
      low = mid;
    }
  }

  return (low + high) / 2;
}

/**
 * Calculates Net Asset Value (NAV) per year using forward-compounding.
 * 
 * Formula: NAV_t = sum_{i=0 to t} I_i * (1 + r)^(t - i)
 * 
 * @param investments Array of {year, amount} objects.
 * @param r The implied annual return rate.
 * @param startYear Optional start year for the result set.
 * @param endYear Optional end year for the result set.
 * @returns An array of {year, nav} objects.
 */
export function computeNAVByYear(
  investments: Investment[],
  r: number,
  startYear?: number,
  endYear?: number
): Array<{year: number, nav: number}> {
  if (investments.length === 0) return [];

  const years = investments.map(inv => inv.year);
  const minYear = startYear ?? Math.min(...years);
  const maxYear = endYear ?? Math.max(...years);
  
  const results: Array<{year: number, nav: number}> = [];
  const factor = 1 + r;

  for (let t = minYear; t <= maxYear; t++) {
    let nav = 0;
    for (const inv of investments) {
      if (inv.year <= t) {
        nav += inv.amount * Math.pow(factor, t - inv.year);
      }
    }
    results.push({ year: t, nav });
  }

  return results;
}
