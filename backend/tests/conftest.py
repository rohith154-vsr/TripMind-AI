import pytest
import os
import sys

# Ensure backend root is on sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

@pytest.fixture
def sample_preferences():
    return {
        "origin": "Paris",
        "destination": "Rome",
        "departure_date": "2026-09-10",
        "return_date": "2026-09-15",
        "num_travelers": 2,
        "budget": 2000.0,
        "currency": "EUR",
        "travel_style": "Cultural",
        "interests": ["Historical Places", "Food", "Architecture"],
    }
