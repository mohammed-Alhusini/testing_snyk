"""
Saudi Bank Transaction Analyzer
------------------------------
This script processes and analyzes Saudi bank SMS transactions, specifically focusing on purchase transactions.
It performs the following functions:
1. Extracts transaction details from Arabic SMS format (amount, vendor, date, card number)
2. Validates transaction type (purchase/شراء)
3. Categorizes transactions using OpenAI's API based on vendor names
4. Saves processed data in JSON format
"""

from openai import OpenAI
import os
import pandas as pd
import re
import json

from dotenv import load_dotenv
load_dotenv()

# OpenAI API setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in environment variables")
OpenAI.api_key = OPENAI_API_KEY

def extract_transaction_details(transaction: str):
    """Extract details from SMS text"""

    type_match = re.search(r"^(شراء|بطاقة ائتمانية:تحويل)", transaction)
    if not type_match:
        return print('its not a purchase transaction')
    else:
        amount_match = re.search(r"مبلغ:SAR ([\d.]+)", transaction)
        vendor_match = re.search(r"لدى:([\w\s]+)", transaction)
        date_match = re.search(r"في:(\d{2}-\d{1,2}-\d{1,2})", transaction)  # Extract date only
        time_match = re.search(r"في:[\d-]+ (\d{2}:\d{2})", transaction)     # Extract time only
        type_match = re.search(r"^(شراء|بطاقة ائتمانية:تحويل)", transaction)
        card_number_match = re.search(r'بطاقة:(\d{4})', transaction)
        if all([amount_match, vendor_match, date_match, time_match, type_match, card_number_match]):
            vendor = vendor_match.group(1).strip().replace("\nفي", "")
            date_str = date_match.group(1)
            time_str = time_match.group(1)
            full_datetime = pd.to_datetime(f"{date_str} {time_str}", format="%y-%m-%d %H:%M")
            return {
                "Type": type_match.group(1),
                "Amount (SAR)": float(amount_match.group(1)),
                "Vendor": vendor,
                "Category": "Other",
                "Card Number": card_number_match.group(1),
                "Date": full_datetime.date().isoformat(),
                "Time": time_str
            }

# ---- OpenAI API Call ----
def get_gpt_category(vendor: str, amount: float):
    try:

        client = OpenAI()
        response = client.chat.completions.create(
            # ---- Classify transaction by vendor name & amount  ----

            model="gpt-4o-mini", 
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial transaction categorizer. Respond with exactly one category from: Food, Shopping, Transport, Health, Education, Utilities, Entertainment, Other. No additional text."
                },
                {
                    "role": "user",
                    "content": f"Based on the vendor name '{vendor}' and transaction amount 'SAR {amount}', what category does this transaction belong to?"
                }
            ],
            temperature=0.3,
            max_tokens=20
        )
        category = response.choices[0].message.content.strip()
        # Validate the category is one of the expected ones
        valid_categories = {
            "Food",          # Combines Groceries, Restaurants, Dining
            "Shopping",      # General retail purchases
            "Transport",     # Transportation, fuel, car services
            "Health",        # Medical, pharmacy, wellness
            "Education",     # Schools, courses, books
            "Utilities",     # Bills, services, subscriptions
            "Entertainment", # Leisure, events, entertainment
            "Other"          # Fallback category
        }

        return category if category in valid_categories else "Other"
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Other"

# ---- Process Transactions & Save as JSON ----
def analyze_transaction(transaction):
    processed_data = []
    if transaction:
        transaction["Category"] = get_gpt_category(
            transaction["Vendor"],
            transaction["Amount (SAR)"]
        )  
        processed_data.append(transaction)
    return processed_data

def save_transactions_to_json(data, filename="data/transactions_analysis.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Data saved to {filename}")



def process_sms_text(sms_text: str):
    """Process a single SMS text and return categorized transaction data"""
    try:
        transaction_details = extract_transaction_details(sms_text)
        transaction = analyze_transaction(transaction_details)
        if transaction:
            save_transactions_to_json(transaction)
            return transaction
        return None
    except Exception as e:
        print(f"Error processing SMS: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    sms_text = input("Enter the transaction SMS text: ")
    result = process_sms_text(sms_text)
    if result:
        print("Transaction processed successfully")
    else:
        print("Could not process transaction")                   
        # شراء\nبطاقة:0510;مدى-ابل باي\nمبلغ:SAR 47.80\nلدى:HALA MARK\nفي:25-2-2 06:44