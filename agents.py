# agents.py

from sheets import log_lead, check_existing_lead
from prompts import (
    SYSTEM_PROMPT,
    GREETING_PROMPT,
    FOLLOW_UP_PROMPT,
    COMPLETION_PROMPT,
    ERROR_PROMPT
)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, messages_from_dict, messages_to_dict
import uuid
from datetime import datetime, timedelta
import json
import re
import random

class RealEstateAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
        self.memory = []  # Simple list to store messages
        self.company_name = "Elite Properties"  # You can change this to your company name
        self.required_fields = {
            "UID": None,  # Will be auto-generated
            "Name": None,
            "Email": None,
            "Phone": None,
            "Company": None,
            "Position": None,
            "Industry": None,
            "Location": None,
            "Company Size": None,
            "Budget Range": None,
            "Decision Maker": None,
            "Interest Level": None,
            "Use Case": None,
            "Competitors": None,
            "Property Type": None,  # Type of property (house, apartment, office, etc.)
            "Property Size": None,  # Size requirements (sq ft, bedrooms, etc.)
            "Timeline": None,       # How soon they want to buy/sell
            "Last Contact Date": None,  # Will be auto-generated
            "Next Follow-up": None,  # Will be auto-generated
            "Contact Method": None,
            "Availability": None,
            "Status": "New Lead",
            "Notes": None,
            "Call Duration": None,  # Will be auto-generated
            "Call Outcome": None,
            "Follow-up Required": None,
            "Lead Source": "AI Chat",
            "Created Date": None,  # Will be auto-generated
            "Last Updated": None  # Will be auto-generated
        }
        self.lead_type = None  # Will be set to "residential" or "commercial"
        self.conversation_started = False
        self.call_in_progress = False
        self.last_question_field = None  # Track what field we last asked about
        self.consecutive_misses = 0  # Track how many times we've asked without getting an answer
        self.skipped_fields = {"Interest Level", "Use Case", "Competitors", "Call Outcome", "Notes"}  # Fields automatically determined by LLM
        self.existing_lead_checked = False  # Track if we've checked for an existing lead

    def generate_uid(self):
        return str(uuid.uuid4())

    def update_timestamps(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.required_fields["Last Updated"] = now
        if not self.required_fields["Created Date"]:
            self.required_fields["Created Date"] = now
        if not self.required_fields["Last Contact Date"]:
            self.required_fields["Last Contact Date"] = now

    def determine_lead_type(self, message):
        """Determine if this is a residential or commercial inquiry"""
        residential_keywords = ["house", "home", "apartment", "condo", "residential", "live", "family"]
        commercial_keywords = ["office", "business", "company", "commercial", "retail", "warehouse", "industrial"]
        
        message_lower = message.lower()
        residential_matches = sum(1 for word in residential_keywords if word in message_lower)
        commercial_matches = sum(1 for word in commercial_keywords if word in message_lower)
        
        if residential_matches > commercial_matches:
            return "residential"
        elif commercial_matches > residential_matches:
            return "commercial"
        return None

    def get_remaining_fields(self):
        """Get fields that still need to be filled"""
        return [field for field, value in self.required_fields.items() 
                if value is None and not field.endswith("(auto-generated)")]

    def extract_info(self, message):
        """Extract information from the user's message"""
        extracted_something = False
        try:
            # Print for debugging
            print(f"Extracting from message: {message}")
            
            # Update timestamps
            self.update_timestamps()
            
            # Property type detection
            if not self.lead_type and self.call_in_progress:
                lead_type = self.determine_lead_type(message)
                if lead_type:
                    self.lead_type = lead_type
                    print(f"Set lead type to: {lead_type}")
                    if lead_type == "residential":
                        # Set appropriate fields for residential
                        business_fields = ["Company", "Position", "Industry", "Company Size"]
                        for field in business_fields:
                            self.required_fields[field] = "-"
                    else:
                        # Set appropriate fields for commercial
                        residential_fields = ["Use Case"]
                        for field in residential_fields:
                            self.required_fields[field] = "-"
                    
                    extracted_something = True
                    
                    return True
            
            # Check for direct patterns for unambiguous fields
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message)
            if email_match and self.required_fields["Email"] is None:
                self.required_fields["Email"] = email_match.group(1)
                print(f"Extracted email: {email_match.group(1)}")
                extracted_something = True
                
            # Check for phone patterns
            phone_pattern = r'(\+?\d{7,}|\d{3,}[-\s]?\d{3,}[-\s]?\d{3,}|\d{10,})'
            phone_match = re.search(phone_pattern, message)
            if phone_match and self.required_fields["Phone"] is None:
                self.required_fields["Phone"] = phone_match.group(1)
                print(f"Extracted phone: {phone_match.group(1)}")
                extracted_something = True
                
            # Use LLM for contextual extraction - let the LLM decide what fields match
            extraction_prompt = f"""Extract relevant information from this message: "{message}"
            
            Current information so far: {self.required_fields}
            Lead type: {self.lead_type or "Not determined yet"}
            Last question field: {self.last_question_field or "None"}
            
            IMPORTANT:
            1. For "Name", only extract if it's clearly a person's name, not a property type or other preference.
            2. For "Location", extract any mentioned locations for property interest.
            3. For "Budget Range", extract any budget information.
            4. For "Use Case", identify how they plan to use the property (e.g., primary residence, investment, office space, etc.)
            5. For "Competitors", identify any competing properties or agencies they mention.
            6. For "Property Type", extract what type of property they're looking for (e.g., house, apartment, condo, office space, retail, etc.)
            7. For "Property Size", extract any size requirements (e.g., square footage, number of bedrooms/bathrooms, etc.)
            8. For "Timeline", extract how soon they want to buy/sell/move (e.g., immediately, within 3 months, next year, etc.)
            9. If they mention any dates for availability or viewings, capture this as "Availability".
            10. If the last question was about a specific field, focus on finding information for that field.
            
            Return a JSON object with only the fields that have new information. For example:
            {{
                "Name": "John Smith",
                "Location": "Downtown",
                "Budget Range": "500k-700k",
                "Use Case": "Primary residence for family of four",
                "Property Type": "Single-family home",
                "Property Size": "3 bedrooms, at least 2000 sq ft",
                "Timeline": "Looking to move within 2 months"
            }}
            
            Only include fields that are explicitly mentioned or can be reasonably inferred from the message.
            If no new information is found, return an empty object {{}}."""
            
            print("\n=== DEBUG: Starting LLM extraction ===")
            print(f"Message to extract from: {message}")
            
            # Use invoke instead of predict
            response = self.llm.invoke(extraction_prompt)
            
            # Get the content from the response
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            print(f"Raw LLM response: {content}")
            
            try:
                # Strip markdown formatting if present
                if content.startswith('```'):
                    # Remove the first line (```json or similar) and last line (```)
                    content = '\n'.join(content.split('\n')[1:-1])
                
                # Try to parse as JSON
                info_dict = json.loads(content)
                print(f"Parsed JSON: {info_dict}")
                
                # Update fields with new information from LLM
                if info_dict and isinstance(info_dict, dict):
                    print(f"LLM extraction found: {info_dict}")
                    for field, value in info_dict.items():
                        if field in self.required_fields and value:
                            self.required_fields[field] = value
                            print(f"Updated {field} = {value}")
                            extracted_something = True
                        else:
                            print(f"Skipped field {field} because: {'field not in required_fields' if field not in self.required_fields else 'value is empty'}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {content}")
                print(f"JSON Error: {str(e)}")
                
                # Only use direct answer extraction if LLM fails and we don't have a lead type yet
                if not self.lead_type:
                    direct_answers = self._check_direct_answers(message)
                    if direct_answers:
                        print(f"Direct answers found: {direct_answers}")
                        for field, value in direct_answers.items():
                            if value and field in self.required_fields:
                                self.required_fields[field] = value
                                print(f"Updated {field} = {value}")
                                extracted_something = True
            
            # Determine interest level if we have enough context
            if len(self.memory) >= 3 and self.required_fields["Interest Level"] is None:
                self._determine_interest_level()
                
            print(f"Current required fields: {self.required_fields}")
            return extracted_something
        except Exception as e:
            print(f"Error extracting information: {e}")
            return False

    def _check_direct_answers(self, message):
        """
        Check for direct answers to questions like name, email, etc.
        This helps when the user responds with just their name or a short answer.
        """
        info = {}
        message = message.strip()
        
        # Property type keywords that shouldn't be mistaken for names
        property_keywords = ["residential", "commercial", "house", "apartment", "condo", 
                            "office", "retail", "industrial", "warehouse", "building"]
        
        # Skip direct name extraction if message contains property keywords
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in property_keywords):
            # This might be a property type response, not a name
            return {}
        
        # Check for a simple name (1-3 words without special characters)
        if self.required_fields["Name"] is None and len(message.split()) <= 3:
            # Check if this looks like a name (only letters and spaces)
            if re.match(r'^[A-Za-z\s]+$', message) and not message.lower() in ["yes", "no", "sure", "ok", "okay", "residential", "commercial"]:
                info["Name"] = message
                return info
        
        # Check for email format
        if self.required_fields["Email"] is None and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', message):
            info["Email"] = message
            return info
            
        # Check for phone format - just digits or common formats
        if self.required_fields["Phone"] is None:
            # Remove any spaces, dashes, or parentheses
            clean_message = re.sub(r'[\s\-\(\)]', '', message)
            # Check if the result is all digits and a reasonable length
            if re.match(r'^\d{7,15}$', clean_message):
                info["Phone"] = message
                return info
            
        # Check for combo of email and phone
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message)
        phone_match = re.search(r'(\d{10,}|\d{3,}[-\s]?\d{3,}[-\s]?\d{3,})', message)
        
        if email_match and phone_match:
            if self.required_fields["Email"] is None:
                info["Email"] = email_match.group(1)
            if self.required_fields["Phone"] is None:
                info["Phone"] = phone_match.group(1)
            if info:
                return info
            
        return info

    def process_message(self, message):
        if not self.conversation_started:
            self.required_fields["UID"] = self.generate_uid()
            self.conversation_started = True
            return GREETING_PROMPT.format(company_name=self.company_name)

        # Update conversation history
        self.memory.append(HumanMessage(content=message))
        
        # Check if they're available to talk
        if not self.call_in_progress:
            if any(word in message.lower() for word in ["yes", "sure", "okay", "fine", "go ahead"]):
                self.call_in_progress = True
                response = "Great! I'd love to understand what kind of property you're looking for. Are you interested in residential or commercial property?"
                self.memory.append(AIMessage(content=response))
                return response
            elif any(word in message.lower() for word in ["no", "busy", "later", "not now"]):
                response = "I completely understand. We all have busy schedules. Would there be a better time for us to chat? I'm here whenever works best for you."
                self.memory.append(AIMessage(content=response))
                return response
            else:
                response = "I hope I didn't catch you at a bad time. Would you like to chat about your property needs now, or would you prefer I reach out later?"
                self.memory.append(AIMessage(content=response))
                return response

        # Extract information from the user's message
        extracted = self.extract_info(message)

        # Check for existing lead once we have an email
        if not self.existing_lead_checked and self.required_fields["Email"]:
            self._check_for_existing_lead()
            self.existing_lead_checked = True

        # Update timestamps
        self.update_timestamps()
        
        # Get remaining fields to gather
        remaining_fields = [f for f in self.get_remaining_fields() if f not in self.skipped_fields]
        
        # Check if we have all essential fields
        essential_fields = ["Name", "Email", "Phone", "Location", "Budget Range", "Property Type", "Property Size", "Timeline"]
        essential_remaining = [f for f in remaining_fields if f in essential_fields]
        
        # If we have all essential fields, try to infer more information and handle scheduling
        if not essential_remaining:
            print("\nAll essential information collected. Inferring additional details and handling scheduling...")
            
            # First, infer any missing information from the conversation
            inference_prompt = f"""Based on this conversation, infer any missing information and preferences.

            Conversation history:
            {[f"{'User' if isinstance(msg, HumanMessage) else 'Agent'}: {msg.content}" for msg in self.memory]}
            
            Current information:
            {self.required_fields}
            
            Lead type: {self.lead_type}
            
            Please infer:
            1. Use Case (how they plan to use the property)
            2. Decision Maker (who makes the final decision)
            3. Interest Level (Hot/Warm/Cold based on urgency and engagement)
            4. Any specific preferences or requirements mentioned
            5. Their preferred contact method
            
            Return as JSON:
            {{
                "Use Case": "inferred use case",
                "Decision Maker": "inferred decision maker",
                "Interest Level": "inferred level",
                "Notes": "any specific preferences or requirements",
                "Contact Method": "preferred contact method"
            }}"""
            
            try:
                inference_response = self.llm.invoke(inference_prompt)
                if hasattr(inference_response, 'content'):
                    inferred_info = json.loads(inference_response.content)
                    for field, value in inferred_info.items():
                        if field in self.required_fields and (self.required_fields[field] is None or self.required_fields[field] == "Not provided"):
                            self.required_fields[field] = value
                            print(f"Inferred {field}: {value}")
            except Exception as e:
                print(f"Error inferring information: {e}")
            
            # If we don't have scheduling information yet, ask about it
            if not self.required_fields.get("Availability") and not self.required_fields.get("Next Follow-up"):
                scheduling_prompt = f"""Based on this conversation, generate a natural question about scheduling a viewing or meeting.
                
                Information gathered:
                {self.required_fields}
                
                Lead type: {self.lead_type}
                
                The question should:
                1. Be brief and direct
                2. Reference their property type and location
                3. Ask about their preferred time for viewing/meeting
                4. Be friendly but professional
                
                Keep it to one sentence."""
                
                try:
                    scheduling_response = self.llm.invoke(scheduling_prompt)
                    response = scheduling_response.content if hasattr(scheduling_response, 'content') else str(scheduling_response)
                    self.memory.append(AIMessage(content=response))
                    return response
                except Exception as e:
                    print(f"Error generating scheduling question: {e}")
                    response = "When would be a good time for you to view some properties?"
                    self.memory.append(AIMessage(content=response))
                    return response
            
            # If we have scheduling information, proceed with logging
            print("\nLogging to sheets...")
            self._generate_follow_up_plan()
            
            # Set final status
            self.required_fields["Call Outcome"] = "Information Gathered"
            self.required_fields["Follow-up Required"] = "Yes" if self.required_fields["Interest Level"] in ["Hot", "Warm"] else "No"
            
            # Log to Google Sheets
            try:
                success = self.log_to_sheet()
                if success:
                    # Generate a brief completion message
                    completion_prompt = f"""Generate a brief, friendly completion message for this real estate conversation.
                    
                    Information gathered:
                    {self.required_fields}
                    
                    Lead type: {self.lead_type}
                    
                    The message should:
                    1. Be very brief and to the point
                    2. Thank them for their time
                    3. Confirm the next steps (viewing/meeting time if scheduled)
                    4. Not repeat any information they provided
                    
                    Keep it under 2 sentences."""
                    
                    try:
                        completion_response = self.llm.invoke(completion_prompt)
                        response = completion_response.content if hasattr(completion_response, 'content') else str(completion_response)
                    except Exception as e:
                        print(f"Error generating completion message: {e}")
                        response = "Thank you for your time. I'll be in touch with property options that match your requirements."
                else:
                    response = "I've gathered your information. However, I'm having trouble saving it at the moment. Please try again later."
            except Exception as e:
                print(f"Error in completion process: {e}")
                response = "I've gathered your information. However, I'm having trouble saving it at the moment. Please try again later."
            
            self.memory.append(AIMessage(content=response))
            return response
        
        # If we don't have all essential fields, continue the conversation
        # Generate a natural, contextual response using LLM
        conversation_prompt = f"""Generate a natural, conversational response for this real estate conversation.
        
        Conversation history:
        {[f"{'User' if isinstance(msg, HumanMessage) else 'Agent'}: {msg.content}" for msg in self.memory]}
        
        Information gathered so far:
        {self.required_fields}
        
        Lead type: {self.lead_type}
        Last question field: {self.last_question_field}
        
        Remaining fields to gather: {remaining_fields}
        
        The response should:
        1. Be concise and to the point
        2. Only acknowledge what they just said if it's particularly relevant
        3. Ask about one of the remaining fields in a natural way
        4. Avoid repeating information they've already provided
        5. Be warm and professional but brief
        6. Not feel like a template or form
        
        Focus on gathering information about: {remaining_fields[0] if remaining_fields else 'any remaining details'}
        
        Keep responses short and engaging. Avoid starting with phrases like "I understand" or "Thanks for sharing" unless the information is particularly significant."""
        
        try:
            conversation_response = self.llm.invoke(conversation_prompt)
            response = conversation_response.content if hasattr(conversation_response, 'content') else str(conversation_response)
            
            # Update the last question field based on the response
            for field in remaining_fields:
                if field.lower() in response.lower():
                    self.last_question_field = field
                    break
                    
        except Exception as e:
            print(f"Error generating conversation response: {e}")
            # Fallback to template-based response if LLM fails
            if remaining_fields:
                next_field = remaining_fields[0]
                response = self._get_question_for_field(next_field)
                self.last_question_field = next_field
            else:
                response = "Is there anything else you'd like to tell me about your property needs?"
        
        self.memory.append(AIMessage(content=response))
        return response

    def _get_question_for_field(self, field):
        """Get a natural-sounding question for a specific field"""
        # Map fields to their questions with more conversational variations
        field_questions = {
            "Name": [
                "Could you tell me your name?", 
                "What's your name?", 
                "Who am I speaking with today?",
                "I'd love to know who I'm chatting with. Your name?"
            ],
            "Company": [
                "What's your company name?", 
                "Which company are you with?", 
                "What's the name of your business?",
                "Do you work with a particular company?"
            ],
            "Position": [
                "What's your role at the company?", 
                "What's your position there?", 
                "What do you do at your company?",
                "May I ask what your role is?"
            ],
            "Industry": [
                "What industry is your company in?", 
                "What sector does your business operate in?", 
                "What type of business are you in?",
                "What field does your company specialize in?"
            ],
            "Location": [
                "Where are you looking for property?", 
                "What area are you interested in?", 
                "Do you have a specific location in mind?",
                "Which neighborhoods are you considering?",
                "Is there a particular part of town you prefer?"
            ],
            "Budget Range": [
                "What's your budget range?", 
                "How much are you looking to spend?", 
                "What price range works for you?",
                "Do you have a budget in mind for this property?",
                "What's your comfort level in terms of price?"
            ],
            "Company Size": [
                "How large is your company?", 
                "How many employees does your company have?", 
                "What's the size of your organization?",
                "Roughly how many people work at your company?"
            ],
            "Decision Maker": [
                "Who will be making the final decision?", 
                "Are you the decision maker for this?", 
                "Who else is involved in the decision process?",
                "Will you be deciding on this yourself or with others?"
            ],
            "Property Type": [
                "What type of property are you looking for?", 
                "Are you interested in a specific property type like house, apartment, or condo?", 
                "What kind of property would best suit your needs?",
                "Do you have a preference between houses, apartments, or other property types?",
                "What style of property do you have in mind?"
            ],
            "Property Size": [
                "What size property do you need?", 
                "How many bedrooms or square feet are you looking for?", 
                "Could you tell me about your space requirements?",
                "How much space would be ideal for you?",
                "Are you looking for something cozy or more spacious?"
            ],
            "Timeline": [
                "When are you looking to buy or move?", 
                "What's your timeline for this purchase?", 
                "How soon do you want to complete this transaction?",
                "Do you have a particular moving date in mind?",
                "Is this something you're looking to do soon or are you just exploring options?"
            ],
            "Use Case": [
                "How will you be using the property?", 
                "What will the space be used for?", 
                "What's your intended use for the property?",
                "Will this be for living, investment, or something else?"
            ],
            "Competitors": [
                "Are you considering other properties or agents?", 
                "Have you seen any other properties that caught your interest?", 
                "Are you working with other agents?",
                "Have you visited any properties yet that you liked or consulted another agent?"
            ],
            "Availability": [
                "When would be a good time for viewings?", 
                "What days work best for you to see properties?", 
                "When are you available to tour some options?",
                "If we find some good matches, when might you be free to take a look?"
            ]
        }
        
        if field in field_questions:
            return random.choice(field_questions[field])
        return f"Could you tell me about your {field.lower().replace('_', ' ')}?"

    def is_ready_to_log(self):
        """
        Check if we have enough information to log the lead.
        For residential leads, we need at least name, contact info, and property preferences.
        For commercial leads, we need company info, contact info, and property requirements.
        """
        if not self.lead_type:
            return False

        # Basic required fields for all leads
        required_fields = [
            "Name",
            "Email",
            "Phone",
            "Location",
            "Budget Range",
            "Product Interest"
        ]

        # Additional fields based on lead type
        if self.lead_type == "residential":
            # For residential leads, we need personal preferences
            required_fields.extend([
                "Use Case",
                "Interest Level"
            ])
        else:
            # For commercial leads, we need business details
            required_fields.extend([
                "Company",
                "Position",
                "Industry",
                "Company Size",
                "Decision Maker",
                "Decision Timeline"
            ])

        # Check if all required fields are filled
        for field in required_fields:
            if not self.required_fields.get(field):
                return False

        return True

    def log_to_sheet(self):
        """
        Log the lead information to Google Sheets
        """
        try:
            print("\n=== Logging to Google Sheets ===")
            print(f"Lead Type: {self.lead_type}")
            print(f"Interest Level: {self.required_fields['Interest Level']}")
            print(f"Status: {self.required_fields['Status']}")
            
            # Log all fields being sent
            print("\nFields being logged:")
            for field, value in self.required_fields.items():
                if value is not None:
                    print(f"{field}: {value}")
            
            success = log_lead(
                uid=self.required_fields["UID"],
                name=self.required_fields["Name"],
                email=self.required_fields["Email"],
                phone=self.required_fields["Phone"],
                location=self.required_fields["Location"],
                budget=self.required_fields["Budget Range"],
                property_type=self.required_fields["Property Type"],
                property_size=self.required_fields["Property Size"],
                timeline=self.required_fields["Timeline"],
                interest=self.required_fields["Interest Level"],
                status=self.required_fields["Status"],
                created_date=self.required_fields["Created Date"],
                last_contact_date=self.required_fields["Last Contact Date"],
                lead_type=self.lead_type,
                use_case=self.required_fields["Use Case"],
                company=self.required_fields["Company"],
                position=self.required_fields["Position"],
                industry=self.required_fields["Industry"],
                company_size=self.required_fields["Company Size"],
                decision_maker=self.required_fields["Decision Maker"],
                next_followup=self.required_fields["Next Follow-up"],
                followup_required=self.required_fields["Follow-up Required"],
                call_outcome=self.required_fields["Call Outcome"],
                notes=self.required_fields["Notes"],
                lead_source=self.required_fields["Lead Source"],
                competitors=self.required_fields["Competitors"]
            )
            
            if success:
                print("\nSuccessfully logged lead to Google Sheets!")
            else:
                print("\nFailed to log lead to Google Sheets")
            
            return success
        except Exception as e:
            print(f"\nError logging to Google Sheets: {str(e)}")
            print("Error details:", e.__class__.__name__)
            import traceback
            print("Full traceback:")
            print(traceback.format_exc())
            return False

    def _determine_interest_level(self):
        """Have the LLM determine the interest level based on the conversation so far"""
        # Get the last few messages for context
        recent_messages = self.memory[-min(len(self.memory), 5):]
        conversation_text = "\n".join([
            f"{'User' if isinstance(msg, HumanMessage) else 'Agent'}: {msg.content}" 
            for msg in recent_messages
        ])
        
        # Check if they said "no" at the start (Cold)
        if len(self.memory) >= 2:
            first_response = self.memory[1].content.lower() if len(self.memory) > 1 and isinstance(self.memory[1], HumanMessage) else ""
            if any(word in first_response for word in ["no", "not interested", "busy", "later", "not now"]):
                self.required_fields["Interest Level"] = "Cold"
                print("Set interest level to Cold due to initial negative response")
                return
        
        interest_prompt = f"""Based on this conversation, determine the client's interest level in finding a property.
        
        Conversation:
        {conversation_text}
        
        Information gathered so far:
        {self.required_fields}
        
        Follow these specific criteria for categorizing interest level:
        - Hot: If they mention any timeline within the year OR show any eagerness/urgency, OR ask multiple questions about properties
        - Warm: If they show even a slight interest in properties or engage in the conversation beyond basic responses
        - Cold: Should already be categorized as Cold if they said no at the start of the conversation
        
        Only respond with one of these three options: Hot, Warm, or Cold."""
        
        try:
            # Use invoke instead of predict
            response = self.llm.invoke(interest_prompt)
            
            # Get the content from the response
            if hasattr(response, 'content'):
                interest_level = response.content.strip()
            else:
                interest_level = str(response).strip()
            
            # Normalize the response
            if "hot" in interest_level.lower():
                self.required_fields["Interest Level"] = "Hot"
            elif "warm" in interest_level.lower():
                self.required_fields["Interest Level"] = "Warm"
            elif "cold" in interest_level.lower():
                self.required_fields["Interest Level"] = "Cold"
            else:
                # Default to Warm if unclear - based on the new criteria
                self.required_fields["Interest Level"] = "Warm"
                
            print(f"Determined interest level: {self.required_fields['Interest Level']}")
            
        except Exception as e:
            print(f"Error determining interest level: {e}")
            self.required_fields["Interest Level"] = "Warm"  # Default if there's an error

    def _infer_missing_fields_from_context(self):
        """Infer missing fields from conversation context using LLM"""
        # Get the full conversation
        conversation_text = "\n".join([
            f"{'User' if isinstance(msg, HumanMessage) else 'Agent'}: {msg.content}" 
            for msg in self.memory
        ])
        
        # Fields that we want to infer
        fields_to_infer = ["Use Case", "Competitors", "Call Outcome", "Contact Method", "Notes"]
        
        # Add any essential fields that are still missing
        essential_fields = ["Name", "Email", "Phone", "Location", "Budget Range"]
        for field in essential_fields:
            if not self.required_fields.get(field) or self.required_fields[field] == "Not provided":
                fields_to_infer.append(field)
        
        inference_prompt = f"""Based on this conversation, infer values for missing fields in our lead information.

        Conversation:
        {conversation_text}

        Current information:
        {self.required_fields}

        Lead type: {self.lead_type or "Unknown"}

        Please infer values for these fields:
        - Use Case: How the client plans to use the property (e.g., primary residence, investment, office space)
        - Competitors: Any competing properties, agencies, or alternatives the client mentioned
        - Call Outcome: Brief summary of the outcome (e.g., "Interested in viewing properties", "Needs more information")
        - Contact Method: How they prefer to be contacted (infer from conversation, default to "Email")
        - Notes: Any important details or unique requirements mentioned

        Also, if any of our essential information is missing or marked as "Not provided", try to infer it from context.

        Return a JSON object with your best inferences for these fields. If you can't reasonably infer a value, don't include that field.
        Example:
        {{
            "Use Case": "Primary residence for a growing family",
            "Competitors": "Mentioned visiting Century 21 properties last week",
            "Call Outcome": "Interested in scheduling a viewing next week",
            "Contact Method": "Email or phone",
            "Notes": "Prefers properties with south-facing windows and nearby schools"
        }}"""
        
        try:
            # Use invoke instead of predict
            response = self.llm.invoke(inference_prompt)
            
            # Get the content from the response
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # Try to parse as JSON
            try:
                inferred_info = json.loads(content)
                print(f"Inferred fields: {inferred_info}")
                
                # Update fields with inferred information
                if inferred_info and isinstance(inferred_info, dict):
                    for field, value in inferred_info.items():
                        if field in self.required_fields and (self.required_fields[field] is None or self.required_fields[field] == "Not provided"):
                            self.required_fields[field] = value
                            print(f"Updated {field} = {value} (inferred)")
            except json.JSONDecodeError:
                print(f"Failed to parse inferred fields JSON: {content}")
        except Exception as e:
            print(f"Error inferring fields: {e}")
            
    def _generate_follow_up_plan(self):
        """Generate a follow-up plan based on interest level and conversation context"""
        if not self.required_fields["Interest Level"]:
            return
            
        interest_level = self.required_fields["Interest Level"]
        
        # Get the full conversation
        conversation_text = "\n".join([
            f"{'User' if isinstance(msg, HumanMessage) else 'Agent'}: {msg.content}" 
            for msg in self.memory
        ])
        
        follow_up_prompt = f"""Based on this conversation with a {interest_level.lower()} lead, recommend a follow-up plan.

        Conversation:
        {conversation_text}

        Lead information:
        {self.required_fields}

        Lead type: {self.lead_type or "Unknown"}
        Interest level: {interest_level}

        Please determine:
        1. Whether a follow-up is recommended (Yes/No)
        2. When the follow-up should occur (date)
        3. Which agent should handle this lead (Rachel or a senior agent)
        4. Any special preparation needed for the follow-up

        Format your response as a JSON object:
        {{
            "Follow-up Required": "Yes",
            "Next Follow-up": "2023-05-15",
            "Agent": "Rachel",
            "Preparation": "Prepare property listings in Downtown area within 500k-700k range"
        }}"""
        
        try:
            # Use invoke instead of predict
            response = self.llm.invoke(follow_up_prompt)
            
            # Get the content from the response
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # Try to parse as JSON
            try:
                follow_up_plan = json.loads(content)
                print(f"Follow-up plan: {follow_up_plan}")
                
                # Update fields with follow-up information
                if follow_up_plan and isinstance(follow_up_plan, dict):
                    if "Follow-up Required" in follow_up_plan:
                        self.required_fields["Follow-up Required"] = follow_up_plan["Follow-up Required"]
                    
                    if "Next Follow-up" in follow_up_plan:
                        self.required_fields["Next Follow-up"] = follow_up_plan["Next Follow-up"]
                        
                    # Store additional info in Notes if it's not already populated
                    notes = []
                    if self.required_fields["Notes"]:
                        notes.append(self.required_fields["Notes"])
                        
                    if "Agent" in follow_up_plan:
                        notes.append(f"Assigned to: {follow_up_plan['Agent']}")
                        
                    if "Preparation" in follow_up_plan:
                        notes.append(f"Preparation: {follow_up_plan['Preparation']}")
                        
                    if notes:
                        self.required_fields["Notes"] = " | ".join(notes)
            except json.JSONDecodeError:
                print(f"Failed to parse follow-up plan JSON: {content}")
        except Exception as e:
            print(f"Error generating follow-up plan: {e}")
            
    def _check_for_existing_lead(self):
        """Check if this lead already exists in the database based on email"""
        if not self.required_fields["Email"]:
            return
            
        try:
            email = self.required_fields["Email"]
            existing_lead = check_existing_lead(email)
            
            if existing_lead:
                print(f"Found existing lead: {existing_lead}")
                
                # Update UID to match existing lead
                if "UID" in existing_lead:
                    self.required_fields["UID"] = existing_lead["UID"]
                
                # Update Last Contact Date
                self.required_fields["Last Contact Date"] = existing_lead.get("Last Contact Date", "")
                
                # Set status to returning lead
                self.required_fields["Status"] = "Returning Lead"
                
                # Add a note about previous contact
                if self.required_fields["Notes"]:
                    self.required_fields["Notes"] += f" | Previous contact on {existing_lead.get('Last Contact Date', 'unknown date')}"
                else:
                    self.required_fields["Notes"] = f"Previous contact on {existing_lead.get('Last Contact Date', 'unknown date')}"
                
                return True
        except Exception as e:
            print(f"Error checking for existing lead: {e}")
            
        return False
