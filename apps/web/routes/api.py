from flask import Blueprint, request, g, jsonify, current_app
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/log_action', methods=['POST'])
def log_action():
    try:
        data = request.json
        # user_idを追加
        data['user_id'] = getattr(g, 'user_id', 'unknown')
        current_app.logger.info(f"ACTION_LOG: {json.dumps(data, ensure_ascii=False)}")
        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"Error logging action: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400
