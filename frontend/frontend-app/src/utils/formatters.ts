
/**
 * Utility functions for formatting currency and percentages with parentheses for negative numbers.
 */

export const formatCurrency = (val: number | string | null | undefined, options: Intl.NumberFormatOptions = {}) => {
  if (val === null || val === undefined) return "-";
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return "-";
  
  const isNegative = num < 0;
  const absVal = Math.abs(num);
  
  const formatted = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    ...options
  }).format(absVal);
  
  return isNegative ? `(${formatted})` : formatted;
};

export const formatPercent = (val: number | string | null | undefined, decimals: number = 2) => {
  if (val === null || val === undefined) return "-";
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return "-";
  
  const isNegative = num < 0;
  const absVal = Math.abs(num);
  const formatted = absVal.toFixed(decimals) + "%";
  
  return isNegative ? `(${formatted})` : formatted;
};

export const formatNumber = (val: number | string | null | undefined, options: Intl.NumberFormatOptions = {}) => {
  if (val === null || val === undefined) return "-";
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return "-";
  
  const isNegative = num < 0;
  const absVal = Math.abs(num);
  
  const formatted = new Intl.NumberFormat('en-US', options).format(absVal);
  
  return isNegative ? `(${formatted})` : formatted;
};

export const formatPropertyType = (type: string | null | undefined) => {
  if (!type) return "-";
  if (type === "MIXED_USE") return "Admin";
  return type.charAt(0) + type.slice(1).toLowerCase().replace('_', ' ');
};
