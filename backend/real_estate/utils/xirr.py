from datetime import date
from decimal import Decimal

def xirr(cashflows: list[tuple[date, float]], guess: float = 0.1) -> float:
    """
    Calculates the internal rate of return for a series of cash flows that occur at irregular intervals.
    Formula: sum(P_i / (1 + r)^((d_i - d_1) / 365)) = 0
    
    Args:
        cashflows: List of (date, amount) tuples.
        guess: Initial guess for the IRR.
        
    Returns:
        The calculated XIRR as a float.
    """
    if not cashflows:
        return 0.0

    # Sort cashflows by date
    cashflows.sort(key=lambda x: x[0])
    
    d1 = cashflows[0][0]
    
    def f(r):
        return sum(
            amount / (1 + r) ** ((d - d1).days / 365.25)
            for d, amount in cashflows
        )
        
    def df(r):
        return sum(
            -((d - d1).days / 365.25) * amount / (1 + r) ** ((d - d1).days / 365.25 + 1)
            for d, amount in cashflows
        )

    r = guess
    for _ in range(100):
        try:
            # Ensure r is within a reasonable range to avoid complex numbers
            # (1 + r) must be positive
            if r <= -0.999:
                r = -0.999

            fr = f(r)
            dfr = df(r)
            if abs(dfr) < 1e-10:
                break
            new_r = r - fr / dfr
            
            # Constrain new_r as well
            if new_r <= -0.999:
                new_r = -0.999
                
            if abs(new_r - r) < 1e-7:
                return float(new_r)
            r = new_r
        except (OverflowError, ZeroDivisionError, TypeError):
            break
            
    return float(r)
