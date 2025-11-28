import os
import requests
import json
from redis import Redis
from rq import Worker, Queue, Connection

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
QUICKBASE_URL = os.getenv('QUICKBASE_URL', 'https://api.quickbase.com/v1/records')
QUICKBASE_USER_TOKEN = os.getenv('QUICKBASE_USER_TOKEN')
QUICKBASE_APP_TOKEN = os.getenv('QUICKBASE_APP_TOKEN')
QUICKBASE_TABLE_ID = os.getenv('QUICKBASE_TABLE_ID')

def query_ollama(prompt, text):
    """Send text to Ollama for processing"""
    full_prompt = f"{prompt}\n\nText to analyze:\n{text}"
    
    payload = {
        "model": "llama3",  # Or your preferred model
        "prompt": full_prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        return response.json().get('response', '')
    except requests.RequestException as e:
        print(f"Error querying Ollama: {e}")
        raise

def update_quickbase(record_id, analysis_result):
    """Update the record in Quickbase with the analysis"""
    headers = {
        'QB-Realm-Hostname': os.getenv('QUICKBASE_REALM', 'your-realm.quickbase.com'),
        'User-Agent': 'Python-Worker',
        'Authorization': f'QB-USER-TOKEN {QUICKBASE_USER_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Map the analysis result to your Quickbase field ID (e.g., field 6 for comments/analysis)
    body = {
        "to": QUICKBASE_TABLE_ID,
        "data": [
            {
                "3": {"value": record_id},  # Assuming field 3 is the Key/Record ID
                "6": {"value": analysis_result}  # Assuming field 6 is where we store the result
            }
        ]
    }
    
    try:
        response = requests.post(QUICKBASE_URL, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error updating Quickbase: {e}")
        raise

def process_po_job(record_id, po_text, prompt):
    """The worker task function"""
    print(f"Processing PO Record: {record_id}")
    
    try:
        # 1. Analyze with Ollama
        analysis = query_ollama(prompt, po_text)
        print(f"Ollama analysis complete for {record_id}")
        
        # 2. Update Quickbase
        update_quickbase(record_id, analysis)
        print(f"Quickbase updated for {record_id}")
        
        return "Success"
        
    except Exception as e:
        print(f"Job failed for {record_id}: {e}")
        raise e

if __name__ == '__main__':
    redis_conn = Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD', None)
    )
    
    with Connection(redis_conn):
        worker = Worker(map(Queue, ['default']))
        worker.work()
