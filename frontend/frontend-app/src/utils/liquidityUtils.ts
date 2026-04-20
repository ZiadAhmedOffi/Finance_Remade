/**
 * Liquidity Index Calculation Utilities
 */

export interface LiquidityIndexResult {
  finalLI: number;
  portfolioL: number;
  ageFactor: number;
  age: number;
}

/**
 * Maps company stage strings to Liquidity Scores (LS).
 * Lower % -> more liquid (better)
 */
export const getVentureLS = (type: string): number => {
  const t = (type || "").toUpperCase().trim();
  if (t.includes("PMF -") || t === "PMF-") return 0.90;
  if (t.includes("PMF +") || t === "PMF+") return 0.75;
  if (t.includes("BMF -") || t === "BMF-") return 0.60;
  if (t.includes("BMF +") || t === "BMF+") return 0.45;
  if (t.includes("SCALING -") || t === "SCALING-") return 0.30;
  if (t.includes("SCALING +") || t === "SCALING+") return 0.15;
  return 0.50; // Default fallback
};

/**
 * Computes the complete Liquidity Index for a portfolio.
 * New Formula: LI = weightedBase * (1 + timeFactor) * 100
 * timeFactor is a distributed percentage over the fund's lifetime (default 10 years).
 * Risk Distribution:
 * - First 3/5 of lifetime: 50% distribution
 * - Final 2/5 of lifetime: 50% distribution
 */
export const calculateLiquidityIndex = (
  currentDeals: any[],
  inceptionYear: number,
  fundLife: number = 10
): LiquidityIndexResult => {
  if (!currentDeals || currentDeals.length === 0) {
    return { finalLI: 0, portfolioL: 0, ageFactor: 0, age: 0 };
  }

  let totalWeightedLS = 0;
  let totalValuation = 0;

  currentDeals.forEach((d) => {
    const val = parseFloat(d.latest_valuation) || 0;
    const ls = getVentureLS(d.company_type);
    totalWeightedLS += ls * val;
    totalValuation += val;
  });

  const portfolioL = totalValuation > 0 ? totalWeightedLS / totalValuation : 0.5;

  const currentYear = new Date().getFullYear();
  const age = Math.max(0, currentYear - inceptionYear);
  
  // Time Factor Calculation: Distributed risk/stability over lifetime
  let timeFactor = 0;
  const unit = fundLife / 5;
  
  if (age <= 3 * unit) {
    // First 3/5 gets 50%
    timeFactor = (age / (3 * unit)) * 0.5;
  } else {
    // Final 2/5 gets 50% (Total 100%)
    const remainingAge = Math.min(age - 3 * unit, 2 * unit);
    timeFactor = 0.5 + (remainingAge / (2 * unit)) * 0.5;
  }
  
  timeFactor = Math.min(1.0, timeFactor);

  // Overall Index Calculation: multiply the portfolio weighted base (1 - portfolioL) by (1 + timeFactor)
  const weightedBase = 1 - portfolioL;
  const finalLI = weightedBase * (1 + timeFactor) * 100;

  return { 
    finalLI: Math.min(100, Math.max(0, finalLI)), 
    portfolioL, // Returning the Risk-based portfolioL (Aggregate Companies Factor)
    ageFactor: timeFactor, 
    age 
  };
};
