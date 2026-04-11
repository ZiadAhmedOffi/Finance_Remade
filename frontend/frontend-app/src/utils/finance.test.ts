
import { computeImpliedReturnRate, computeNAVByYear } from './finance';
import type { Investment } from './finance';

/**
 * Simple test runner for financial utilities.
 * Run this with: npx tsx frontend/frontend-app/src/utils/finance.test.ts
 */

function assertEquals(actual: any, expected: any, message: string, tolerance: number = 0) {
  const diff = Math.abs(actual - expected);
  if (diff <= tolerance) {
    console.log(`✅ PASS: ${message}`);
  } else {
    console.error(`❌ FAIL: ${message} | Expected: ${expected}, Actual: ${actual}`);
  }
}

function runTests() {
  console.log("Starting Financial Utility Tests...\n");

  // 1. Basic Case
  // Year 0: 100, Year 1: 100, Final Year: 2, Final Value: 231 (10% return)
  // (Wait, I used 231 because 100*(1.1)^2 + 100*(1.1) = 231. 
  // If the prompt says 242, it's ~13.4% return. Let's test with 242 as per prompt.)
  const basicInvestments: Investment[] = [
    { year: 0, amount: 100 },
    { year: 1, amount: 100 }
  ];
  const rBasic = computeImpliedReturnRate(basicInvestments, 2, 242);
  // With 242, r should be ~13.4%
  assertEquals(rBasic, 0.134, "Basic Case r (Expected ~13.4% for 242)", 0.001);

  // Test with 231 for exact 10%
  const r10Pct = computeImpliedReturnRate(basicInvestments, 2, 231);
  assertEquals(r10Pct, 0.1, "Basic Case r (Exact 10% for 231)", 0.0001);

  // NAV Progression for 10% case, historicalFinalYear = 2, rFuture = 0.05, fundEndYear = 5
  const navs = computeNAVByYear(basicInvestments, 0.1, 2, 0.05, 5, 0, 3);
  assertEquals(navs.find(n => n.year === 0)?.nav, 100, "NAV Year 0");
  assertEquals(navs.find(n => n.year === 1)?.nav, 210, "NAV Year 1 (100*1.1 + 100)");
  assertEquals(navs.find(n => n.year === 2)?.nav, 231, "NAV Year 2 (210*1.1)");
  assertEquals(navs.find(n => n.year === 3)?.nav, 231, "NAV Year 3 (Capped at Year 2 for historical part)");

  // Future investment test: Investment at Year 3, rFuture = 0.1
  const futureInvs: Investment[] = [
    { year: 0, amount: 100 },
    { year: 3, amount: 100 }
  ];
  const navsFuture = computeNAVByYear(futureInvs, 0.1, 2, 0.1, 5, 0, 4);
  // Year 2: 100 * (1.1)^2 = 121
  // Year 3: 121 (hist part capped) + 100 (future part injected) = 221
  // Year 4: 121 (hist part capped) + 100 * (1.1) = 231
  assertEquals(navsFuture.find(n => n.year === 2)?.nav, 121, "NAV Year 2 (Historical part grew)");
  assertEquals(navsFuture.find(n => n.year === 3)?.nav, 221, "NAV Year 3 (Future part injected)");
  assertEquals(navsFuture.find(n => n.year === 4)?.nav, 231, "NAV Year 4 (Future part grew)");

  // 2. Uneven Investments
  // Year 0: 100, Year 2: 200, Final Year: 5
  const unevenInvestments: Investment[] = [
    { year: 0, amount: 100 },
    { year: 2, amount: 200 }
  ];
  const rUneven = computeImpliedReturnRate(unevenInvestments, 5, 500);
  console.log(`Computed uneven r: ${(rUneven * 100).toFixed(2)}%`);

  // 3. Exact Reconstruction Test
  const reconstructedValue = computeNAVByYear(unevenInvestments, rUneven, 5, 0, 5, 5, 5)[0].nav;
  assertEquals(reconstructedValue, 500, "Exact Reconstruction Test", 1e-6);

  // 4. Edge Cases
  // Single investment
  const singleInv: Investment[] = [{ year: 0, amount: 100 }];
  const rSingle = computeImpliedReturnRate(singleInv, 1, 110);
  assertEquals(rSingle, 0.1, "Single investment case", 1e-6);

  // All investments late
  const lateInvs: Investment[] = [{ year: 4, amount: 100 }];
  const rLate = computeImpliedReturnRate(lateInvs, 5, 120);
  assertEquals(rLate, 0.2, "Late investment case", 1e-6);

  // Very high return scenario
  const highReturnInvs: Investment[] = [{ year: 0, amount: 10 }];
  const rHigh = computeImpliedReturnRate(highReturnInvs, 1, 100);
  assertEquals(rHigh, 9.0, "High return case (900%)", 1e-6);

  // Negative or near-zero return
  const lowReturnInvs: Investment[] = [{ year: 0, amount: 100 }];
  const rZero = computeImpliedReturnRate(lowReturnInvs, 1, 100);
  assertEquals(rZero, 0.0, "Zero return case", 1e-6);

  const rNeg = computeImpliedReturnRate(lowReturnInvs, 1, 50);
  assertEquals(rNeg, -0.5, "Negative return case (-50%)", 1e-6);

  console.log("\nAll tests completed.");
}

// For running with tsx
runTests();
