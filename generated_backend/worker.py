import os
import requests
import json
import time
import logging
from typing import Dict, Any, Union
from redis import Redis
from rq import Worker, Queue, Connection

# Configure Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
QUICKBASE_URL = os.getenv('QUICKBASE_URL', 'https://api.quickbase.com/v1/records')
QUICKBASE_USER_TOKEN = os.getenv('QUICKBASE_USER_TOKEN')
QUICKBASE_REALM = os.getenv('QUICKBASE_REALM', 'your-realm.quickbase.com')

# Redis Connection (Global)
redis_conn = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', None)
)

def log_safe_event(message: str):
    """Logs a message to stdout (for systemd) AND pushes it to Redis (for Dashboard)."""
    logger.info(message)
    timestamp = time.strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    try:
        # Push to 'monitor_logs' list and keep only last 100
        redis_conn.lpush("monitor_logs", log_entry)
        redis_conn.ltrim("monitor_logs", 0, 99) 
    except Exception as e:
        logger.warning(f"Could not push log to Redis: {e}")

def query_ollama(po_text: str, prompt_json: Dict[str, str]) -> Dict[str, Any]:
    """Send text + schema to Ollama."""
    system_instruction = (
        "You are an expert data extraction engine. "
        "Your job is to read the document provided and extract accurate information "
        "matching the specific keys requested in the JSON schema. "
        "Output ONLY valid JSON."
    )

    full_prompt = f"""
{system_instruction}

--- BEGIN DOCUMENT TEXT ---
{po_text}
--- END DOCUMENT TEXT ---

**INSTRUCTIONS:**
1. Read the document text above.
2. For each key in the schema below, analyze the text and provide the requested summary.
3. Return ONLY the JSON object.

**REQUIRED OUTPUT SCHEMA:**
{json.dumps(prompt_json, indent=2)}
"""

    payload = {
        "model": "llama3.1",
        "format": "json",
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 4096,
            "top_k": 20,
            "num_ctx": 32000,
            "repeat_penalty": 1.1
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=1800)
        response.raise_for_status()
        return json.loads(response.json().get('response', '{}'))
    except requests.RequestException as e:
        log_safe_event(f"Error querying Ollama: {e}")
        raise
    except json.JSONDecodeError as e:
        log_safe_event(f"Error parsing AI response: {e}")
        raise

def update_quickbase(record_id: str, target_table_id: str, target_field_ids: Dict[str, int], ai_data: Dict[str, Any]):
    """Update the record in Quickbase using the dynamic field map."""
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
            logger.warning(f"Expected key '{json_key}' not found in AI response.")

    body = {
        "to": target_table_id,
        "data": [fields_to_update]
    }

    try:
        response = requests.post(QUICKBASE_URL, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        log_safe_event(f"Error updating Quickbase: {e}")
        logger.error(f"Failed Payload Metadata: {{'to': target_table_id, 'record_id': record_id, 'error': str(e)}}")
        raise

def update_quickbase_error(record_id: str, target_table_id: str, error_field_id: int, error_message: str):
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
        logger.error(f"Failed to report error to QuickBase: {e}")

def process_po_job(data: Dict[str, Any]):
    start_time = time.time()
    record_id = data['record_id']
    request_name = data.get('request_name', 'Unknown Request')
    
    log_safe_event(f"Processing Job: '{request_name}' for Record: {record_id}")

    # --- GUARD RAILS ---
    if not data.get('po_text') or len(data.get('po_text', '').strip()) < 10:
        log_safe_event("Skipped: Text empty.")
        return "Skipped"

    try:
        logger.info(f"Sending to Ollama...")
        ai_result = query_ollama(data['po_text'], data['prompt_json'])
        logger.info(f"Ollama analysis complete. Keys found: {list(ai_result.keys())}")

        logger.info(f"Updating QuickBase table {data['target_table_id']}...")
        update_quickbase(
            record_id,
            data['target_table_id'],
            data['target_field_ids'],
            ai_result
        )
        
        end_time = time.time()
        duration = end_time - start_time
        log_safe_event(f"Job complete for {record_id}")
        log_safe_event(f"PERFORMANCE: Job finished in {duration:.2f} seconds")
        return "Success"

    except Exception as e:
        log_safe_event(f"Job failed for {record_id}: {e}")
        if 'error_field_id' in data and 'target_table_id' in data:
            logger.info(f"Reporting error to QuickBase field {data['error_field_id']}...")
            update_quickbase_error(
                record_id,
                data['target_table_id'],
                data['error_field_id'],
                str(e)
            )
        raise e

if __name__ == '__main__':
    # Read queues from Env Var, default to 'default'
    queue_names = os.getenv('WORKER_QUEUES', 'default').split(',')
    
    with Connection(redis_conn):
        logger.info(f"Worker listening on queues: {queue_names}")
        worker = Worker(map(Queue, queue_names))
        worker.work()
