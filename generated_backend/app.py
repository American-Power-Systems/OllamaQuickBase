from flask import Flask, request, jsonify
from redis import Redis
from rq import Queue
import os

app = Flask(__name__)

# Redis connection
redis_conn = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', None)
)

# RQ Queue
q = Queue(connection=redis_conn)

@app.route('/process_po', methods=['POST'])
def process_po():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['record_id', 'po_text']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields: record_id, po_text'}), 400
            
        record_id = data['record_id']
        po_text = data['po_text']
        prompt = data.get('prompt', 'Extract key details from this PO')
        
        # Enqueue the job
        from worker import process_po_job
        job = q.enqueue(
            process_po_job,
            args=(record_id, po_text, prompt),
            job_timeout='5m'
        )
        
        return jsonify({
            'status': 'queued',
            'job_id': job.get_id(),
            'message': f'PO {record_id} added to queue'
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
