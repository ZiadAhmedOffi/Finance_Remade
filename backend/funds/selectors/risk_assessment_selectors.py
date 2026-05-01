from funds.models import RiskAssessment

def get_risk_assessments_for_fund(fund):
    return fund.risk_assessments.all()
