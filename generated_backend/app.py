from flask import Flask, request, jsonify
from redis import Redis
from rq import Queue
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 1. SECURITY: Enforce API Key from Environment
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY environment variable must be set")

# Redis connection
redis_conn = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', None)
)

# Define our Queues
q_high = Queue('high', connection=redis_conn)
q_default = Queue('default', connection=redis_conn)
q_low = Queue('low', connection=redis_conn)
q_long = Queue('long_docs', connection=redis_conn)

# Configuration
LONG_DOC_THRESHOLD = 20000  # Characters

@app.route('/api/status', methods=['GET'])
def get_status():
    client_key = request.headers.get('X-API-Key')
    if client_key != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Fetch logs from Redis
        raw_logs = redis_conn.lrange("monitor_logs", 0, 49)
        logs = [log.decode('utf-8') for log in raw_logs]
        
        total_depth = len(q_high) + len(q_default) + len(q_low) + len(q_long)

        return jsonify({
            "status": "online",
            "queue_depth": total_depth,
            "queues": {
                "high": len(q_high),
                "default": len(q_default),
                "low": len(q_low),
                "long_docs": len(q_long)
            },
            "logs": logs
        })
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/debug/config', methods=['GET'])
def get_routing_config():
    """Helper endpoint to verify routing logic and thresholds."""
    client_key = request.headers.get('X-API-Key')
    if client_key != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
        
    return jsonify({
        "long_doc_threshold": LONG_DOC_THRESHOLD,
        "routing_table": {
            "brbf729zp": "high (Priority Contracts)",
            "bpcdfksyx": "low (Standard Invoices)",
            "others": "default"
        }
    })

@app.route('/api/process_po', methods=['POST'])
def process_po():
    client_key = request.headers.get('X-API-Key')
    if client_key != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        
        # Validation
        required_fields = ['record_id', 'po_text', 'target_table_id', 'target_field_ids', 'prompt_json']
        missing = [field for field in required_fields if field not in data]
        
        if missing:
            return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

        if not isinstance(data.get('target_field_ids'), dict):
             return jsonify({'error': 'target_field_ids must be a JSON object mapping keys to FIDs'}), 400

        # --- ROUTING LOGIC ---
        table_id = data.get('target_table_id', '')
        text_len = len(data.get('po_text', '') or "")
        
        selected_queue = q_default
        queue_name = "default"

        # 1. HEAVY TRAFFIC: Check Length First
        if text_len > LONG_DOC_THRESHOLD:
            selected_queue = q_long
            queue_name = "long_docs"
        
        # 2. FAST TRAFFIC: Check Table Priority
        else:
            # Table: brbf729zp -> High Priority (e.g. Urgent Contracts)
            if table_id == 'brbf729zp':
                selected_queue = q_high
                queue_name = "high"
            # Table: bpcdfksyx -> Low Priority (e.g. Batch Invoices)
            elif table_id == 'bpcdfksyx':
                selected_queue = q_low
                queue_name = "low"
            # All other tables -> Default Priority
            else:
                selected_queue = q_default
                queue_name = "default"

        # Enqueue
        from worker import process_po_job
        job = selected_queue.enqueue(
            process_po_job,
            args=(data,),
            job_timeout='30m'
        )
        
        logger.info(f"Enqueued record {data['record_id']} to {queue_name}")
        
        return jsonify({
            'status': 'queued',
            'queue': queue_name,
            'job_id': job.get_id(),
            'message': f'Record {data["record_id"]} added to {queue_name} queue'
        }), 202
        
    except Exception as e:
        logger.error(f"API Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
