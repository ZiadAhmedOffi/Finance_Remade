from importlib import import_module

from django.conf import settings


def dispatch_job(job_name, **kwargs):
    """
    Queue boundary for compliance jobs.
    Phase 1 uses inline execution by default until a worker backend is wired in.
    """
    job_mode = getattr(settings, "COMPLIANCE_JOB_MODE", "INLINE")
    if job_mode != "INLINE":
        raise NotImplementedError(f"Compliance job mode '{job_mode}' is not configured yet.")

    module = import_module("compliance.jobs.workflows")
    job = getattr(module, job_name)
    return job(**kwargs)
