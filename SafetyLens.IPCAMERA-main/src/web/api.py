"""Contratos HTTP consumidos pelo painel React."""

import io
import sqlite3
from datetime import datetime, timedelta

from flask import Blueprint, Response, jsonify, request, send_file


def create_api(database_path, config=None, camera_runtime=None):
    """Cria o Blueprint com consultas, validação e rotas da API."""
    api = Blueprint('api', __name__)

    def query(sql, params=(), one=False):
        """Executa uma consulta em conexão curta para não compartilhar SQLite entre threads."""
        connection = sqlite3.connect(database_path, timeout=20)
        try:
            connection.execute('PRAGMA busy_timeout = 5000')
            connection.execute('PRAGMA foreign_keys = ON')
            cursor = connection.execute(sql, params)
            return cursor.fetchone() if one else cursor.fetchall()
        finally:
            connection.close()

    def parse_date(value, field):
        """Converte uma data ISO 8601 e produz mensagem de erro adequada à API."""
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f'{field} deve ser uma data ISO 8601 válida') from error
        if parsed.tzinfo:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed

    def period(default_days=30):
        """Resolve o intervalo solicitado ou usa os trinta dias mais recentes."""
        end = parse_date(request.args.get('end'), 'end') or datetime.now()
        start = parse_date(request.args.get('start'), 'start') or end - timedelta(days=default_days)
        if start > end:
            raise ValueError('start não pode ser posterior a end')
        return start, end

    def sql_period(start, end, prefix='d'):
        """Gera a cláusula e os parâmetros de período usados nas consultas."""
        return f'{prefix}.timestamp >= ? AND {prefix}.timestamp <= ?', (
            start.strftime('%Y-%m-%d %H:%M:%S'),
            end.strftime('%Y-%m-%d %H:%M:%S'),
        )

    def serialize_detection(row):
        """Transforma uma linha SQLite no contrato público sem expor o BLOB."""
        return {
            'id': row[0],
            'timestamp': row[1].replace(' ', 'T') if row[1] else None,
            'epi': row[2] or 'Não identificado',
            'imageUrl': f'/image/{row[0]}' if row[3] else None,
        }

    def require_camera():
        """Interrompe rotas de câmera quando o app foi criado apenas para consultas."""
        if config is None:
            raise RuntimeError('Configuração de câmera indisponível')

    def json_body(allowed):
        """Limita tamanho e campos do JSON para evitar abuso e mass assignment."""
        if not request.is_json or (request.content_length or 0) > 4096:
            raise ValueError('Envie um JSON válido de até 4 KB')
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) - set(allowed):
            raise ValueError('O JSON possui campos não permitidos')
        return body

    def camera_payload():
        """Monta o estado público da câmera sem revelar a URL/credenciais."""
        require_camera()
        camera = config.config['camera']
        runtime_status = camera_runtime.status() if camera_runtime else {
            'state': 'offline', 'message': 'Serviço de câmera indisponível', 'fps': 0,
            'resolution': None, 'missingEpis': [], 'updatedAt': None,
        }
        return {
            'source': {
                'name': camera.get('active_name', 'Câmera nativa'),
                'type': 'network' if camera.get('url') else 'native',
            },
            'settings': {
                **camera['default_settings'],
                'minConfidence': config.min_confidence,
                'delayTime': config.delay_time,
            },
            'status': runtime_status,
            'streamUrl': '/api/camera/stream',
        }

    def detections(start, end, limit, offset=0):
        """Busca ocorrências paginadas com a indicação de imagem disponível."""
        where, params = sql_period(start, end)
        return query(
            f'''SELECT d.id, d.timestamp, e.nome, d.frame_data IS NOT NULL
                FROM detections d
                LEFT JOIN epis e ON e.id = d.epi_id
                WHERE {where}
                ORDER BY d.timestamp DESC, d.id DESC
                LIMIT ? OFFSET ?''',
            (*params, limit, offset),
        )

    def total(start, end):
        """Conta exatamente o mesmo universo filtrado usado na listagem."""
        where, params = sql_period(start, end)
        return query(f'SELECT COUNT(*) FROM detections d WHERE {where}', params, one=True)[0]

    def by_epi(start, end):
        """Agrupa ocorrências por EPI para cards e gráficos."""
        where, params = sql_period(start, end)
        return query(
            f'''SELECT COALESCE(e.nome, 'Não identificado'), COUNT(*)
                FROM detections d
                LEFT JOIN epis e ON e.id = d.epi_id
                WHERE {where}
                GROUP BY e.nome
                ORDER BY COUNT(*) DESC''',
            params,
        )

    def daily(start, end):
        """Agrupa ocorrências por dia para a série temporal."""
        where, params = sql_period(start, end)
        return query(
            f'''SELECT date(d.timestamp), COUNT(*) FROM detections d
                WHERE {where} GROUP BY date(d.timestamp) ORDER BY date(d.timestamp)''',
            params,
        )

    @api.errorhandler(ValueError)
    def invalid_request(error):
        """Padroniza falhas de validação como JSON HTTP 400."""
        return jsonify({'error': str(error)}), 400

    @api.get('/api/health')
    def health():
        """Confirma que servidor e banco respondem."""
        query('SELECT 1', one=True)
        return jsonify({'status': 'ok', 'database': 'connected'})

    @api.get('/api/camera')
    def camera():
        """Retorna fonte, ajustes e telemetria atual da câmera."""
        try:
            return jsonify(camera_payload())
        except RuntimeError as error:
            return jsonify({'error': str(error)}), 503

    @api.patch('/api/camera/settings')
    def camera_settings():
        """Valida e persiste somente ajustes permitidos pelo painel."""
        require_camera()
        body = json_body({
            'brightness', 'contrast', 'sharpness', 'grayscale', 'minConfidence',
            'delayTime',
        })
        ranges = {
            'brightness': (0, 200), 'contrast': (0, 200), 'sharpness': (0, 10),
            'minConfidence': (0, 1), 'delayTime': (0, 300),
        }
        normalized = {}
        for key, value in body.items():
            if key == 'grayscale':
                if not isinstance(value, bool):
                    raise ValueError('grayscale deve ser verdadeiro ou falso')
                normalized[key] = value
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f'{key} deve ser numérico')
            minimum, maximum = ranges[key]
            if not minimum <= value <= maximum:
                raise ValueError(f'{key} deve estar entre {minimum} e {maximum}')
            normalized[key] = value

        setting_names = {
            'minConfidence': 'min_confidence', 'delayTime': 'delay_time',
        }
        config.update_camera_settings(**{
            setting_names.get(key, key): value for key, value in normalized.items()
        })
        if camera_runtime and 'minConfidence' in normalized:
            camera_runtime.update_confidence(normalized['minConfidence'])
        return jsonify(camera_payload())

    @api.get('/api/cameras')
    def cameras():
        """Lista câmeras sem expor seus caminhos internos de conexão."""
        require_camera()
        active_name = config.config['camera'].get('active_name', 'Câmera nativa')
        return jsonify({
            'active': active_name,
            'items': [
                {'name': item.get('name'), 'ip': item.get('ip'), 'port': item.get('port', 554), 'active': item.get('name') == active_name}
                for item in config.registered_cameras
            ],
        })

    @api.post('/api/cameras')
    def register_camera():
        """Cadastra uma câmera IPv4 privada e inicia a tentativa de conexão."""
        require_camera()
        body = json_body({'name', 'ip', 'port'})
        if not {'name', 'ip'} <= set(body):
            raise ValueError('Informe name e ip')
        port = body.get('port', 554)
        name, ip, candidates = config.camera_candidates(body['name'], body['ip'], port)
        if any(item.get('ip') == ip for item in config.registered_cameras):
            return jsonify({'error': 'Já existe uma câmera com esse IP'}), 409
        config.register_camera(name, ip, candidates[0], port)
        if camera_runtime:
            camera_runtime.restart()
        return jsonify({'camera': {'name': name, 'ip': ip, 'port': int(port), 'active': True}}), 201

    @api.post('/api/cameras/native')
    def native_camera():
        """Volta para a webcam local sem apagar câmeras de rede."""
        require_camera()
        body = json_body(set())
        if body:
            raise ValueError('Esta ação não recebe campos')
        config.activate_native_camera()
        if camera_runtime:
            camera_runtime.restart()
        return jsonify({'active': 'Câmera nativa'})

    @api.post('/api/cameras/<ip>/connect')
    def connect_camera(ip):
        """Ativa novamente uma câmera cadastrada e reinicia o runtime."""
        require_camera()
        body = json_body(set())
        if body:
            raise ValueError('Esta ação não recebe campos')
        camera = config.activate_camera(ip)
        if camera_runtime:
            camera_runtime.restart()
            camera_runtime.ensure_started()
        return jsonify({'camera': {'name': camera['name'], 'ip': camera['ip'], 'port': camera.get('port', 554)}}), 202

    @api.delete('/api/cameras/<ip>')
    def delete_camera(ip):
        """Remove uma câmera e volta à nativa quando necessário."""
        require_camera()
        camera, was_active = config.remove_camera(ip)
        if camera_runtime and was_active:
            camera_runtime.restart()
        return jsonify({'deleted': {'name': camera['name'], 'ip': camera['ip']}, 'active': 'Câmera nativa' if was_active else None})

    @api.post('/api/camera/restart')
    def restart_camera():
        """Força uma nova tentativa na fonte atualmente selecionada."""
        require_camera()
        body = json_body(set())
        if body:
            raise ValueError('Esta ação não recebe campos')
        if camera_runtime:
            camera_runtime.restart()
            camera_runtime.ensure_started()
        return jsonify({'status': 'reconnecting'}), 202

    @api.get('/api/camera/stream')
    def camera_stream():
        """Entrega os frames como MJPEG, formato aceito diretamente pelo navegador."""
        if camera_runtime is None:
            return jsonify({'error': 'Serviço de câmera indisponível'}), 503
        return Response(
            camera_runtime.frames(),
            mimetype='multipart/x-mixed-replace; boundary=frame',
            headers={'Cache-Control': 'no-store, private'},
        )

    @api.get('/api/dashboard')
    def dashboard():
        """Agrega o resumo e eventos recentes da visão geral."""
        start, end = period()
        recent = [serialize_detection(row) for row in detections(start, end, 5)]
        counts = [{'name': name, 'count': count} for name, count in by_epi(start, end)]
        timeline = [{'date': date, 'count': count} for date, count in daily(start, end)]
        return jsonify({
            'updatedAt': datetime.now().isoformat(timespec='seconds'),
            'summary': {
                'totalDetections': total(start, end),
                'lastDetection': recent[0] if recent else None,
                'monitoredEpis': len(counts),
            },
            'byEpi': counts,
            'daily': timeline,
            'recent': recent,
        })

    @api.get('/api/detections')
    def detection_list():
        """Entrega o histórico com filtros e paginação validados."""
        start, end = period()
        try:
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 15))
        except ValueError as error:
            raise ValueError('page e limit devem ser números inteiros') from error
        if page < 1 or not 1 <= limit <= 100:
            raise ValueError('page deve ser >= 1 e limit deve estar entre 1 e 100')
        count = total(start, end)
        items = [serialize_detection(row) for row in detections(start, end, limit, (page - 1) * limit)]
        return jsonify({
            'items': items,
            'page': page,
            'limit': limit,
            'total': count,
            'totalPages': max(1, (count + limit - 1) // limit),
        })

    @api.get('/api/analytics')
    def analytics():
        """Calcula totais, tendências e séries no mesmo intervalo solicitado."""
        start, end = period()
        current = by_epi(start, end)
        duration = end - start
        previous_end = start - timedelta(seconds=1)
        previous = dict(by_epi(previous_end - duration, previous_end))
        period_total = total(start, end)
        overall_total = query('SELECT COUNT(*) FROM detections', one=True)[0]
        epi_summary = []
        for name, count in current:
            old_count = previous.get(name, 0)
            trend = 0 if count == old_count else (100 if old_count == 0 else round((count - old_count) / old_count * 100, 1))
            epi_summary.append({
                'name': name,
                'count': count,
                'percentage': round(count / period_total * 100, 1) if period_total else 0,
                'trend': trend,
            })
        monthly_start = start if request.args.get('start') else end - timedelta(days=365)
        monthly_where, monthly_params = sql_period(monthly_start, end)
        monthly = query(
            f'''SELECT strftime('%Y-%m', d.timestamp), COUNT(*) FROM detections d
                WHERE {monthly_where}
                GROUP BY strftime('%Y-%m', d.timestamp)
                ORDER BY strftime('%Y-%m', d.timestamp)''',
            monthly_params,
        )
        return jsonify({
            'updatedAt': datetime.now().isoformat(timespec='seconds'),
            'summary': {
                'periodTotal': period_total,
                'overallTotal': overall_total,
                'periodShare': round(period_total / overall_total * 100, 1) if overall_total else 0,
                'mostMissing': current[0][0] if current else 'Nenhum',
            },
            'trend': [{'date': date, 'count': count} for date, count in daily(start, end)],
            'byEpi': epi_summary,
            'monthly': [{'month': month, 'count': count} for month, count in monthly],
        })

    @api.get('/image/<int:detection_id>')
    def detection_image(detection_id):
        """Entrega uma evidência JPEG privada pelo identificador da ocorrência."""
        result = query('SELECT frame_data FROM detections WHERE id = ?', (detection_id,), one=True)
        if not result or not result[0]:
            return jsonify({'error': 'Imagem não encontrada'}), 404
        response = send_file(io.BytesIO(result[0]), mimetype='image/jpeg', max_age=0)
        response.headers['Cache-Control'] = 'private, no-store'
        return response

    return api
