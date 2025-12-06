from flask import Flask, request, jsonify
from redis import Redis
from rq import Queue, Worker
import os
import logging
import psutil
import subprocess
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# SECURITY
API_KEY = os.getenv('API_KEY')

# Redis Connection
redis_conn = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', None)
)

# Queues
q_high = Queue('high', connection=redis_conn)
q_default = Queue('default', connection=redis_conn)
q_low = Queue('low', connection=redis_conn)
q_long = Queue('long_docs', connection=redis_conn)

def get_gpu_stats():
    """Parses nvidia-smi for GPU usage."""
    if not shutil.which('nvidia-smi'):
        return {"load": 0, "memory": 0, "mem_used_mb": 0}
    try:
        # Get GPU Load and Memory Used
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            encoding='utf-8'
        )
        util, mem_used, mem_total = map(int, output.strip().split(', '))
        mem_percent = round((mem_used / mem_total) * 100, 1)
        return {"load": util, "memory": mem_percent, "mem_used_mb": mem_used}
    except Exception:
        return {"load": 0, "memory": 0, "mem_used_mb": 0}

@app.route('/api/status', methods=['GET'])
def get_status():
    client_key = request.headers.get('X-API-Key')
    if client_key != API_KEY:
        # Strict security: Require key even for dashboard
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # 1. Redis Logs
        raw_logs = redis_conn.lrange("monitor_logs", 0, 19)
        logs = [log.decode('utf-8') for log in raw_logs]

        # 2. Queue Depths
        queues = {
            "high": len(q_high),
            "default": len(q_default),
            "low": len(q_low),
            "long_docs": len(q_long)
        }
        total_depth = sum(queues.values())

        # 3. Worker Status
        workers = Worker.all(connection=redis_conn)
        active_count = sum(1 for w in workers if w.state == 'busy')
        
        # 4. System Resources
        sys_stats = {
            "cpu": psutil.cpu_percent(interval=None),
            "ram": psutil.virtual_memory().percent,
            "gpu": get_gpu_stats()
        }

        return jsonify({
            "status": "online" if active_count > 0 else "idle",
            "queue_depth": total_depth,
            "active_workers": len(workers),
            "working_count": active_count,
            "queues": queues,
            "system": sys_stats,
            "logs": logs
        })
    except Exception as e:
        logger.error(f"Status Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/process_po', methods=['POST'])
def process_po():
    client_key = request.headers.get('X-API-Key')
    if client_key != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        
        required_fields = ['record_id', 'po_text', 'target_table_id', 'target_field_ids', 'prompt_json']
        if any(f not in data for f in required_fields):
            return jsonify({'error': 'Missing fields'}), 400

        # Routing Logic
        priority = data.get('priority', 'normal').lower()
        text_len = len(data.get('po_text', '') or "")
        LONG_DOC_THRESHOLD = 20000
        
        selected_queue = q_default
        queue_name = "default"

        if text_len > LONG_DOC_THRESHOLD:
            selected_queue = q_long
            queue_name = "long_docs"
        elif priority == 'high':
            selected_queue = q_high
            queue_name = "high"
        elif priority == 'low':
            selected_queue = q_low
            queue_name = "low"
        else:
            selected_queue = q_default
            queue_name = "default"

        from worker import process_po_job
        job = selected_queue.enqueue(
            process_po_job,
            args=(data,),
            job_timeout='60m'
        )
        
        logger.info(f"Enqueued record {data['record_id']} to {queue_name}")
        
        return jsonify({
            'status': 'queued',
            'queue': queue_name,
            'job_id': job.get_id(),
            'message': f'Record {data["record_id"]} added to {queue_name} queue'
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
