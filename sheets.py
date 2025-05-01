# sheets.py

import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from datetime import datetime
import gspread

# Load environment variables
load_dotenv()

# Constants
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
SHEET_NAME = os.getenv("GOOGLE_SHEETS_SHEET_NAME", "AI Voice Leads")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")

# Flag to track if sheets integration is available
sheets_available = True if SERVICE_ACCOUNT_FILE and SPREADSHEET_ID else False

def get_credentials():
    """Get Google Sheets API credentials from service account file"""
    global sheets_available
    
    if not SERVICE_ACCOUNT_FILE:
        print("Warning: Google Sheets credentials path not set in environment variables")
        sheets_available = False
        return None
        
    try:
        credentials = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return credentials
    except Exception as e:
        print(f"Error getting credentials: {e}")
        sheets_available = False
        return None

def get_sheets_client():
    """Get gspread client for easier spreadsheet handling"""
    global sheets_available
    
    if not sheets_available:
        print("Google Sheets integration is not available - skipping")
        return None
        
    try:
        credentials = get_credentials()
        if not credentials:
            return None
            
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        print(f"Error getting gspread client: {e}")
        sheets_available = False
        return None

def log_lead(uid, name, email, phone, location, budget, property_type, property_size, timeline, 
             interest, status, created_date, last_contact_date, lead_type, use_case, company, 
             position, industry, company_size, decision_maker, next_followup, followup_required, 
             call_outcome, notes, lead_source, competitors):
    """Attempt to log to Google Sheets only. No fallback to local save."""

    # Prepare lead data for Sheets only
    lead_data = {
        "UID": uid,
        "Name": name,
        "Email": email,
        "Phone": phone,
        "Location": location,
        "Budget": budget,
        "Property Type": property_type,
        "Property Size": property_size,
        "Timeline": timeline,
        "Interest": interest,
        "Status": status,
        "Created Date": created_date,
        "Last Contact Date": last_contact_date,
        "Lead Type": lead_type,
        "Use Case": use_case,
        "Company": company,
        "Position": position,
        "Industry": industry,
        "Company Size": company_size,
        "Decision Maker": decision_maker,
        "Next Follow-up": next_followup,
        "Follow-up Required": followup_required,
        "Call Outcome": call_outcome,
        "Notes": notes,
        "Lead Source": lead_source,
        "Competitors": competitors
    }

    # Data to log in same order as column headers
    data = list(lead_data.values())

    try:
        client = get_sheets_client()
        if not client:
            raise RuntimeError("Sheets client not available")

        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet(SHEET_NAME)

        # Look for existing record
        existing_lead = None
        if email and len(email) > 0 and email != "Not provided":
            records = sheet.get_all_records()
            for i, record in enumerate(records):
                if record.get("UID") == uid or record.get("Email") == email:
                    existing_lead = record
                    existing_lead["row"] = i + 2
                    break

        if existing_lead:
            row = existing_lead["row"]
            cell_range = f"A{row}:Z{row}"
            sheet.update(cell_range, [data])
            print(f"Updated existing lead: {name} at row {row}")
        else:
            sheet.append_row(data)
            print(f"Appended new lead: {name}")

        return True

    except Exception as e:
        print(f"[Google Sheets] Failed to log lead: {e}")
        return False



def get_all_leads():
    """Retrieve all leads from the sheet"""
    try:
        client = get_sheets_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet(SHEET_NAME)
        
        return sheet.get_all_records()
    except Exception as err:
        print(f"Error retrieving leads from Google Sheets: {err}")
        return None

def check_existing_lead(email):
    """Check if a lead already exists with the given email and return their data if found"""
    try:
        # Open the sheet
        client = get_sheets_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet(SHEET_NAME)
        
        # Get all records
        records = sheet.get_all_records()
        
        # Look for a matching email
        for i, record in enumerate(records):
            if record.get('Email') == email:
                print(f"Found existing lead with email {email} at row {i+2}")
                # Add row number for later updates
                record['row'] = i + 2
                return record
                
        print(f"No existing lead found with email {email}")
        return None
        
    except Exception as e:
        print(f"Error checking for existing lead: {e}")
        return None
