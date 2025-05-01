from datetime import datetime
import uuid
from sheets import log_lead

# Create a sample lead dictionary
sample_lead = {
    "uid": str(uuid.uuid4()),
    "name": "Test User",
    "email": "testuser@example.com",
    "phone": "+123456789",
    "location": "Test City",
    "budget": "$500,000",
    "property_type": "Apartment",
    "property_size": "1200 sqft",
    "timeline": "3 months",
    "interest": "High",
    "status": "New",
    "created_date": datetime.now().strftime("%Y-%m-%d"),
    "last_contact_date": datetime.now().strftime("%Y-%m-%d"),
    "lead_type": "Buyer",
    "use_case": "Investment",
    "company": "TestCorp",
    "position": "Manager",
    "industry": "Tech",
    "company_size": "50-100",
    "decision_maker": "Yes",
    "next_followup": "2025-05-05",
    "followup_required": "Yes",
    "call_outcome": "Interested",
    "notes": "This is a test lead for Google Sheets integration.",
    "lead_source": "Website",
    "competitors": "CompetitorA, CompetitorB"
}

# Call log_lead using unpacked dictionary
success = log_lead(**sample_lead)

if success:
    print("✅ Test Passed: Lead was successfully logged to Google Sheets (or locally if fallback).")
else:
    print("❌ Test Failed: Lead could not be logged.")
