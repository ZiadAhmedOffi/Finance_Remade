from django.db import transaction
from funds.models import RiskAssessment
from funds.api.serializers import RiskAssessmentSerializer

class RiskAssessmentService:
    @staticmethod
    @transaction.atomic
    def batch_upsert_risk_assessments(*, fund, data):
        """
        Handles batch upserting of risk assessments for a specific fund.
        """
        if not isinstance(data, list):
            data = [data]

        results = []
        for item in data:
            company_name = item.get("company_name")
            if not company_name:
                continue

            assessment, created = RiskAssessment.objects.update_or_create(
                fund=fund,
                company_name=company_name,
                defaults={
                    "execution_capacity_score": item.get("execution_capacity_score", 5.0),
                    "market_validation_score": item.get("market_validation_score", 5.0),
                    "status": item.get("status", "ON_TRACK")
                }
            )
            results.append(assessment)

        return results
