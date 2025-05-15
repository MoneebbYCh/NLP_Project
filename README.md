# Real-Estate Voice Caller AI

## Overview
This project is an AI-powered real estate assistant built with Streamlit. It provides a conversational interface (both text and voice) to gather lead information from potential clients. The assistant uses Google Gemini (via LangChain) for natural language processing, ElevenLabs for text-to-speech and speech-to-text, and Google Sheets for lead logging and deduplication.

## Features
- **Interactive Chat & Voice Interface**: Engage with users via text and voice using Streamlit.
- **AI-Powered Conversation**: Leverages Google Gemini (via LangChain) to extract information and maintain a natural conversation flow.
- **Voice Capabilities**: Text-to-speech and speech-to-text powered by ElevenLabs.
- **Lead Logging**: Automatically logs lead information to Google Sheets, with deduplication support.
- **Customizable Prompts**: Easily modify conversation prompts in `prompts.py` to suit your business needs.

## Setup and Installation
1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd NLP_Project
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up environment variables**:
   Create a `.env` file in the project root with the following variables:
   ```
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
   GOOGLE_SHEETS_SHEET_NAME=your_sheet_name
   GOOGLE_SHEETS_CREDENTIALS_PATH=path/to/your/service_account_credentials.json
   ```
4. **Run the application**:
   ```bash
   streamlit run app.py
   ```

## Environment Variables
- `ELEVENLABS_API_KEY`: API key for ElevenLabs (text-to-speech and speech-to-text).
- `GOOGLE_SHEETS_SPREADSHEET_ID`: ID of the Google Sheets spreadsheet for lead logging.
- `GOOGLE_SHEETS_SHEET_NAME`: Name of the sheet within the spreadsheet.
- `GOOGLE_SHEETS_CREDENTIALS_PATH`: Path to the service account credentials JSON file for Google Sheets API.

## Usage
- **Text Chat**: Enter your phone number to start the conversation. The assistant will guide you through gathering lead information.
- **Voice Chat**: Enable voice mode in the sidebar. Click the "Speak" button to provide voice input.

## Google Sheets Setup
1. Create a Google Sheets spreadsheet and note its ID.
2. Set up a service account in Google Cloud Console and download the credentials JSON file.
3. Update the `.env` file with the spreadsheet ID, sheet name, and path to the credentials file.

## Customization
- Modify conversation prompts in `prompts.py` to adjust the assistant's behavior.
- Adjust the `RealEstateAgent` logic in `agents.py` to change how information is extracted and processed.

## Testing
Run the test script to verify Google Sheets integration:
```bash
python test.py
```

## Troubleshooting
- **Voice Issues**: Ensure your microphone is properly connected and permissions are granted.
- **Google Sheets Errors**: Verify your service account credentials and spreadsheet permissions.
- **API Key Issues**: Double-check your ElevenLabs API key in the `.env` file.



