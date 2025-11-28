import os
import requests
import json
from redis import Redis
from rq import Worker, Queue, Connection

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
QUICKBASE_URL = os.getenv('QUICKBASE_URL', 'https://api.quickbase.com/v1/records')
# We keep Auth tokens in Env Vars for security, but Table IDs come from the payload
QUICKBASE_USER_TOKEN = os.getenv('QUICKBASE_USER_TOKEN')
QUICKBASE_REALM = os.getenv('QUICKBASE_REALM', 'your-realm.quickbase.com')

def query_ollama(po_text, prompt_json):
    """
    Send text + schema to Ollama.
    """
    # Construct a prompt that forces JSON output based on the schema provided by QuickBase
    system_instruction = "You are an expert data extraction assistant. Extract information from the text to match the provided JSON schema exactly."
    
    full_prompt = f"""
{system_instruction}

**TEXT TO ANALYZE:**
{po_text}

**REQUIRED JSON OUTPUT SCHEMA:**
{json.dumps(prompt_json, indent=2)}

Respond ONLY with valid JSON that matches this schema.
"""
    
    payload = {
        "model": "llama3",
        "format": "json", # Force valid JSON
        "prompt": full_prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=600) # 10 minute timeout
        response.raise_for_status()
        # Ollama returns the response object, we need the 'response' string inside it
        return json.loads(response.json().get('response', '{}'))
    except requests.RequestException as e:
        print(f"Error querying Ollama: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error parsing AI response: {e}")
        raise

def update_quickbase(record_id, target_table_id, target_field_ids, ai_data):
    """
    Update the record in Quickbase using the dynamic field map.
    """
    headers = {
        'QB-Realm-Hostname': QUICKBASE_REALM,
        'User-Agent': 'Python-Worker',
        'Authorization': f'QB-USER-TOKEN {QUICKBASE_USER_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Build the update payload dynamically
    # target_field_ids maps JSON keys to QuickBase FIDs
    # Example: {"payment_terms": 6, "total": 7}
    
    fields_to_update = {}
    
    # Always include the Record ID (FID 3) to identify which record to update
    fields_to_update["3"] = {"value": record_id}
    
    for json_key, fid in target_field_ids.items():
        if json_key in ai_data:
            fields_to_update[str(fid)] = {"value": ai_data[json_key]}
            
    body = {
        "to": target_table_id,
        "data": [fields_to_update]
    }
    
    try:
        # Use the 'upsert' endpoint or 'records' endpoint
        response = requests.post(QUICKBASE_URL, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error updating Quickbase: {e}")
        print(f"Attempted Body: {json.dumps(body)}") # Log payload for debugging
        raise

def update_quickbase_error(record_id, target_table_id, error_field_id, error_message):
    """
    Write an error message back to QuickBase if processing fails.
    """
    headers = {
        'QB-Realm-Hostname': QUICKBASE_REALM,
        'User-Agent': 'Python-Worker',
        'Authorization': f'QB-USER-TOKEN {QUICKBASE_USER_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    body = {
        "to": target_table_id,
        "data": [
            {
                "3": {"value": record_id},
                str(error_field_id): {"value": str(error_message)}
            }
        ]
    }
    
    try:
        requests.post(QUICKBASE_URL, headers=headers, json=body)
    except Exception as e:
        print(f"Failed to report error to QuickBase: {e}")

def process_po_job(data):
    """
    The worker task function.
    Expects 'data' dict with: record_id, po_text, target_table_id, target_field_ids, prompt_json
    Optional: error_field_id
    """
    record_id = data['record_id']
    print(f"Processing Job for Record: {record_id}")
    
    try:
        # 1. Analyze with Ollama
        print(f" sending to Ollama...")
        ai_result = query_ollama(data['po_text'], data['prompt_json'])
        print(f"Ollama analysis complete.")
        
        # 2. Update Quickbase
        print(f"Updating QuickBase table {data['target_table_id']}...")
        update_quickbase(
            record_id, 
            data['target_table_id'], 
            data['target_field_ids'], 
            ai_result
        )
        print(f"Job complete for {record_id}")
        return "Success"
        
    except Exception as e:
        print(f"Job failed for {record_id}: {e}")
        
        # Write error back to QuickBase if an 'error_field_id' was provided
        if 'error_field_id' in data and 'target_table_id' in data:
            print(f"Reporting error to QuickBase field {data['error_field_id']}...")
            update_quickbase_error(
                record_id,
                data['target_table_id'],
                data['error_field_id'],
                str(e)
            )
            
        raise e

if __name__ == '__main__':
    redis_conn = Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD', None)
    )
    
    with Connection(redis_conn):
        # Listen on 'default' queue
        worker = Worker(map(Queue, ['default']))
        worker.work()
