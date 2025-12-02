from flask import Flask, request, jsonify
from redis import Redis
from rq import Queue
import os

app = Flask(__name__)

# SECURITY: Your API Key
API_KEY = os.getenv('API_KEY', 'q#*3VyUK6&ih63xZ')

# Redis connection
redis_conn = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', None)
)

# RQ Queue
q = Queue(connection=redis_conn)

@app.route('/api/process_po', methods=['POST'])
def process_po():
    # 1. SECURITY CHECK: Verify API Key
    client_key = request.headers.get('X-API-Key')
    if client_key != API_KEY:
        # Reject if key is missing or wrong
        return jsonify({'error': 'Unauthorized: Invalid or missing API Key'}), 401

    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['record_id', 'po_text', 'target_table_id', 'target_field_ids', 'prompt_json']
        missing = [field for field in required_fields if field not in data]
        
        if missing:
            return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
            
        # Enqueue the job
        from worker import process_po_job
        job = q.enqueue(
            process_po_job,
            args=(data,),
            job_timeout='10m'
        )
        
        return jsonify({
            'status': 'queued',
            'job_id': job.get_id(),
            'message': f'Record {data["record_id"]} added to queue'
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
