import os
import requests
import json
from redis import Redis
from rq import Worker, Queue, Connection

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
QUICKBASE_URL = os.getenv('QUICKBASE_URL', 'https://api.quickbase.com/v1/records')
QUICKBASE_USER_TOKEN = os.getenv('QUICKBASE_USER_TOKEN')
QUICKBASE_REALM = os.getenv('QUICKBASE_REALM', 'your-realm.quickbase.com')

def query_ollama(po_text, prompt_json):
    """
    Send text + schema to Ollama with HIGH FOCUS settings.
    """
    system_instruction = (
        "You are a strict document extraction engine. "
        "Your ONLY job is to extract the specific terms requested in the JSON schema. "
        "Ignore all conversational filler, pleasantries, and unrelated document text. "
        "If a specific topic (like Insurance or Payment Terms) is not found, return null for that field. "
        "Do not explain your answer. Output ONLY valid JSON."
    )

    full_prompt = f"""
{system_instruction}

--- BEGIN DOCUMENT TEXT ---
{po_text}
--- END DOCUMENT TEXT ---

**INSTRUCTIONS:**
Review the document above.
Extract the exact information requested by the keys below.
Return ONLY the JSON object.

**REQUIRED OUTPUT SCHEMA:**
{json.dumps(prompt_json, indent=2)}
"""

    payload = {
        "model": "llama3",
        "format": "json",
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 1024,
            "top_k": 20,
            "num_ctx": 4096
        }
    }

    try:
        # Increased timeout to 30 minutes for large files
        response = requests.post(OLLAMA_URL, json=payload, timeout=1800)
        response.raise_for_status()
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

    fields_to_update = {}
    fields_to_update["3"] = {"value": record_id}

    for json_key, fid in target_field_ids.items():
        if json_key in ai_data:
            fields_to_update[str(fid)] = {"value": ai_data[json_key]}
        else:
            print(f"WARNING: Expected key '{json_key}' not found in AI response.")

    body = {
        "to": target_table_id,
        "data": [fields_to_update]
    }

    try:
        response = requests.post(QUICKBASE_URL, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error updating Quickbase: {e}")
        print(f"Failed Payload Metadata: {{'to': target_table_id, 'record_id': record_id, 'error': str(e)}}")
        raise

def update_quickbase_error(record_id, target_table_id, error_field_id, error_message):
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
    record_id = data['record_id']
    print(f"Processing Job for Record: {record_id}")

    # --- GUARD RAILS ---
    if not data.get('po_text') or len(data['po_text'].strip()) < 10:
        print("Skipped: Text empty.")
        return "Skipped"

    if len(data['po_text']) > 15000:
        print(f"Truncating text from {len(data['po_text'])} to 15000 chars for speed.")
        data['po_text'] = data['po_text'][:15000]
    # -------------------

    try:
        print(f"Sending to Ollama...")
        ai_result = query_ollama(data['po_text'], data['prompt_json'])
        print(f"Ollama analysis complete. Keys found: {list(ai_result.keys())}")

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
        worker = Worker(map(Queue, ['default']))
        worker.work()
