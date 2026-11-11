#!/usr/bin/env python3
"""Initialize storage directories and files."""
import os
import json
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage import DATA_DIR, ESTIMATES_DIR, PRICEBOOK_PATH

def initialize_storage():
    """Create necessary directories and initialize pricebook if needed."""
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)

    # Create estimates directory if it doesn't exist
    os.makedirs(ESTIMATES_DIR, exist_ok=True)

    # Initialize pricebook if it doesn't exist
    if not os.path.exists(PRICEBOOK_PATH):
        default_pricebook = {
            "materials": [
                {
                    "id": "wire-12-2",
                    "description": "12-2 NM-B Wire",
                    "category": "Wire",
                    "unit_price": 0.45,
                    "unit": "ft"
                },
                {
                    "id": "wire-14-2",
                    "description": "14-2 NM-B Wire",
                    "unit_price": 0.35,
                    "unit": "ft",
                    "category": "Wire"
                },
                {
                    "id": "breaker-15",
                    "description": "15A Circuit Breaker",
                    "unit_price": 8.50,
                    "unit": "each",
                    "category": "Breakers"
                },
                {
                    "id": "breaker-20",
                    "description": "20A Circuit Breaker",
                    "unit_price": 10.75,
                    "unit": "each",
                    "category": "Breakers"
                },
                {
                    "id": "box-4sq",
                    "description": "4" Square Electrical Box",
                    "unit_price": 3.25,
                    "unit": "each",
                    "category": "Boxes"
                },
                {
                    "id": "outlet",
                    "description": "15A Duplex Receptacle",
                    "unit_price": 4.95,
                    "unit": "each",
                    "category": "Receptacles"
                },
                {
                    "id": "switch",
                    "description": "Single Pole Switch",
                    "unit_price": 6.50,
                    "unit": "each",
                    "category": "Switches"
                },
                {
                    "id": "panel-200",
                    "description": "200A Main Breaker Panel",
                    "unit_price": 450.00,
                    "unit": "each",
                    "category": "Service Equipment"
                }
            ],
            "state": "Maryland",
            "code_edition": "NEC 2023",
            "labor_rate_per_hour": 85.00,
            "labor_rate_sources": [],
            "ai_cache": {}
        }

        with open(PRICEBOOK_PATH, "w", encoding="utf-8") as f:
            json.dump(default_pricebook, f, indent=2)

        print(f"Initialized pricebook at {PRICEBOOK_PATH}")
    else:
        print(f"Pricebook already exists at {PRICEBOOK_PATH}")

    print("Storage initialization complete!")

if __name__ == "__main__":
    initialize_storage()
