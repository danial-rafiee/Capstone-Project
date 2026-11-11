# B demo/test runner only. This does not package A's Flask app or C's AI service.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Keep dependency installation cached when only B source changes.
COPY requirements-ha3.txt requirements-ha4.txt requirements-capstone-b.txt ./
RUN python -m pip install --no-cache-dir -r requirements-capstone-b.txt \
    && useradd --create-home --uid 10001 appuser

COPY --chown=10001:10001 smart_energy/__init__.py smart_energy/__init__.py
COPY --chown=10001:10001 smart_energy/analytics/ smart_energy/analytics/
COPY --chown=10001:10001 demo_capstone_b.py demo_off_hours_b.py check_docker_database_b.py ./
COPY --chown=10001:10001 tests/test_analytics_ha4.py tests/test_period_analytics.py tests/test_off_hours_analytics.py tests/

USER 10001:10001
CMD ["python", "demo_off_hours_b.py"]
