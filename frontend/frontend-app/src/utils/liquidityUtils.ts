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
 * Formula: LI = (Σ(LS_i * V_i) / Σ(V_i)) * exp(-k * t) * 100
 */
export const calculateLiquidityIndex = (
  currentDeals: any[],
  inceptionYear: number,
  decayConstant: number = 0.20
): LiquidityIndexResult => {
  if (!currentDeals || currentDeals.length === 0) {
    return { finalLI: 0, portfolioL: 0, ageFactor: 1, age: 0 };
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
  const ageFactor = Math.exp(-decayConstant * age);

  const finalLI = 100 - (portfolioL * ageFactor * 100);

  return { 
    finalLI: Math.min(100, Math.max(0, finalLI)), 
    portfolioL, 
    ageFactor, 
    age 
  };
};
