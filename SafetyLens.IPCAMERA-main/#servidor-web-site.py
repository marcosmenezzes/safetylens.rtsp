from flask import Flask, render_template, request, make_response, jsonify, redirect, url_for
import sqlite3
from datetime import datetime, timedelta
import json
import math
import yaml
import time
import os

class Config:
    def __init__(self, config_path='config.yaml'):
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def save_config(self):
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f)
    
    @property
    def database_path(self):
        return self.config['paths']['database']

config = Config()
DATABASE_PATH = config.database_path

app = Flask(__name__)

def get_db_connection():
    """
    Cria uma conexão com o banco de dados com timeout e configurações de segurança.
    
    Returns:
        sqlite3.Connection: Conexão com o banco de dados
    """
    return sqlite3.connect(DATABASE_PATH, timeout=20, isolation_level=None)

def execute_db_query(query, params=None, fetch_all=True):
    """
    Executa uma query no banco de dados com retry em caso de falha.
    
    Args:
        query (str): Query SQL a ser executada
        params (tuple): Parâmetros para a query
        fetch_all (bool): Se True, retorna fetchall(), se False, fetchone()
    
    Returns:
        list/tuple: Resultado da query
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with get_db_connection() as conn:
                conn.execute("PRAGMA busy_timeout = 5000")  # 5 segundos de timeout
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                    
                if fetch_all:
                    return cursor.fetchall()
                return cursor.fetchone()
                
        except sqlite3.OperationalError as e:
            retry_count += 1
            if retry_count == max_retries:
                raise e
            time.sleep(1)  # Espera 1 segundo antes de tentar novamente

def get_data(limit=100, start_time=None, end_time=None, offset=0):
    """
    Obtém os dados de detecção de EPIs do banco de dados.

    Args:
        limit (int): Número máximo de registros a serem retornados.
        start_time (str): Data e hora de início para filtrar os resultados.
        end_time (str): Data e hora de fim para filtrar os resultados.
        offset (int): Deslocamento para a paginação.

    Returns:
        list: Uma lista de tuplas contendo os dados das detecções.
    """
    query = """
        SELECT detections.id, timestamp, frame_data, epis.nome
        FROM detections
        JOIN epis ON detections.epi_id = epis.id
    """
    params = []
    if start_time:
        query += " WHERE timestamp >= ?"
        params.append(start_time)
    if end_time:
        query += " AND timestamp <= ?" if start_time else " WHERE timestamp <= ?"
        params.append(end_time)
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    return execute_db_query(query, params)

def get_evolution_data(start_time=None, end_time=None):
    """
    Obtém os dados de evolução das detecções por dia.

    Args:
        start_time (str): Data e hora de início para filtrar os resultados.
        end_time (str): Data e hora de fim para filtrar os resultados.

    Returns:
        list: Uma lista de tuplas contendo a data e a contagem de detecções.
    """
    if not start_time:
        start_time = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    if not end_time:
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    query = """
        SELECT strftime('%Y-%m-%d', timestamp) AS date, COUNT(*)
        FROM detections
        WHERE timestamp >= ? AND timestamp <= ?
        GROUP BY date
        ORDER BY date
    """
    
    results = execute_db_query(query, (start_time, end_time))
    
    # Converte o formato da data para o padrão brasileiro
    formatted_results = []
    for row in results:
        dt = datetime.strptime(row[0], '%Y-%m-%d')
        formatted_date = dt.strftime('%d-%m-%Y')
        formatted_results.append((formatted_date, row[1]))
    
    return formatted_results

def get_epi_counts(start_time=None, end_time=None):
    """
    Obtém a contagem de detecções por tipo de EPI.

    Args:
        start_time (str): Data e hora de início para filtrar os resultados.
        end_time (str): Data e hora de fim para filtrar os resultados.

    Returns:
        list: Uma lista de tuplas contendo o nome do EPI e a contagem de detecções.
    """
    # Se não houver data de início especificada, usa os últimos 30 dias
    if not start_time:
        start_time = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    if not end_time:
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    query = """
        SELECT epis.nome, COUNT(*)
        FROM detections
        JOIN epis ON detections.epi_id = epis.id
        WHERE timestamp >= ? AND timestamp <= ?
        GROUP BY epis.nome
        ORDER BY COUNT(*) DESC
    """
    return execute_db_query(query, (start_time, end_time))

def get_total_count(start_time=None, end_time=None):
    """
    Obtém a contagem total de detecções.

    Args:
        start_time (str): Data e hora de início para filtrar os resultados.
        end_time (str): Data e hora de fim para filtrar os resultados.

    Returns:
        int: A contagem total de detecções.
    """
    # Se não houver data de início especificada, usa os últimos 30 dias
    if not start_time:
        start_time = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    if not end_time:
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    query = "SELECT COUNT(*) FROM detections WHERE timestamp >= ? AND timestamp <= ?"
    result = execute_db_query(query, (start_time, end_time), fetch_all=False)
    return result[0] if result else 0

def get_detection_image(detection_id):
    """
    Obtém os dados da imagem de uma detecção específica.

    Args:
        detection_id (int): O ID da detecção.

    Returns:
        bytes: Os dados da imagem, ou None se a imagem não for encontrada.
    """
    query = "SELECT frame_data FROM detections WHERE id = ?"
    result = execute_db_query(query, (detection_id,), fetch_all=False)
    return result[0] if result else None

def get_data_json(limit=100, start_time=None, end_time=None, offset=0):
    """
    Obtém os dados de detecção de EPIs do banco de dados e os formata para JSON.

    Args:
        limit (int): Número máximo de registros a serem retornados.
        start_time (str): Data e hora de início para filtrar os resultados.
        end_time (str): Data e hora de fim para filtrar os resultados.
        offset (int): Deslocamento para a paginação.

    Returns:
        list: Uma lista de tuplas contendo os dados das detecções.
    """
    data = get_data(limit, start_time, end_time, offset)
    processed_data = []
    for row in data:
        if row[2] and not isinstance(row[2], str):
            row = list(row)
            row[2] = row[2].decode('utf-8', errors='ignore')
        processed_data.append(row)
    return processed_data

def get_monthly_comparison(start_time=None, end_time=None):
    """
    Obtém o total de detecções por mês para o período selecionado.
    Se nenhum período for especificado, mostra os últimos 12 meses.

    Args:
        start_time (str): Data e hora de início para filtrar os resultados.
        end_time (str): Data e hora de fim para filtrar os resultados.
    """
    if not start_time and not end_time:
        # Se não houver datas especificadas, usa os últimos 12 meses
        query = """
            SELECT 
                strftime('%m', timestamp) as mes,
                strftime('%Y', timestamp) as ano,
                COUNT(*) as total
            FROM detections
            WHERE timestamp >= date('now', '-11 months')
            GROUP BY ano, mes
            ORDER BY ano, mes
        """
        results = execute_db_query(query)
    else:
        # Se houver datas especificadas, usa o período selecionado
        query = """
            SELECT 
                strftime('%m', timestamp) as mes,
                strftime('%Y', timestamp) as ano,
                COUNT(*) as total
            FROM detections
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY ano, mes
            ORDER BY ano, mes
        """
        results = execute_db_query(query, (start_time, end_time))
    
    meses = {
        '01': 'JAN', '02': 'FEV', '03': 'MAR', 
        '04': 'ABR', '05': 'MAI', '06': 'JUN',
        '07': 'JUL', '08': 'AGO', '09': 'SET', 
        '10': 'OUT', '11': 'NOV', '12': 'DEZ'
    }
    
    # Processa os resultados para criar labels e dados
    labels = []
    values = []
    
    for mes, ano, total in results:
        # Formata o label como "MMM/YY"
        label = f"{meses[mes]}/{ano[2:]}"
        labels.append(label)
        values.append(total)
    
    return labels, values

def get_compliance_rate(start_time=None, end_time=None):
    """
    Calcula a taxa de conformidade (detecções sem violações).
    """
    query = """
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN epi_id IS NULL THEN 1 END) as compliant
        FROM detections
        WHERE 1=1
    """
    params = []
    if start_time:
        query += " AND timestamp >= ?"
        params.append(start_time)
    if end_time:
        query += " AND timestamp <= ?"
        params.append(end_time)
    
    result = execute_db_query(query, params, fetch_all=False)
    if result and result[0] > 0:
        return (result[1] / result[0]) * 100
    return 100

def get_most_common_epi(start_time=None, end_time=None):
    """
    Obtém o EPI mais frequentemente ausente.

    Args:
        start_time (str): Data e hora de início para filtrar os resultados.
        end_time (str): Data e hora de fim para filtrar os resultados.
    """
    # Se não houver data de início especificada, usa os últimos 30 dias
    if not start_time:
        start_time = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    if not end_time:
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    query = """
        SELECT epis.nome, COUNT(*) as count
        FROM detections
        JOIN epis ON detections.epi_id = epis.id
        WHERE timestamp >= ? AND timestamp <= ?
        GROUP BY epis.nome
        ORDER BY count DESC
        LIMIT 1
    """
    result = execute_db_query(query, (start_time, end_time), fetch_all=False)
    return result[0] if result else "Nenhum"

def get_total_violations():
    """
    Obtém o total geral de violações (sem filtro de data).
    
    Returns:
        int: O número total de violações registradas.
    """
    query = """
        SELECT COUNT(*)
        FROM detections
        JOIN epis ON detections.epi_id = epis.id
    """
    result = execute_db_query(query, fetch_all=False)
    return result[0] if result else 0

def get_epi_trend(epi_name, start_time=None, end_time=None):
    """
    Calcula a tendência de violações para um EPI específico comparando com o período anterior.
    
    Args:
        epi_name (str): Nome do EPI para calcular a tendência
        start_time (str): Data e hora de início para filtrar os resultados
        end_time (str): Data e hora de fim para filtrar os resultados
        
    Returns:
        float: Porcentagem de variação entre os períodos (positivo = aumento, negativo = diminuição)
    """
    if not start_time:
        start_time = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    if not end_time:
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Converter strings para objetos datetime
    end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    
    # Calcular a duração do período em dias
    period_days = (end_dt - start_dt).days
    if period_days < 1:
        period_days = 1
    
    # Definir o período anterior
    previous_end = start_dt
    previous_start = previous_end - timedelta(days=period_days)
    
    # Consulta para o período atual
    current_query = """
        SELECT COUNT(*)
        FROM detections
        JOIN epis ON detections.epi_id = epis.id
        WHERE epis.nome = ?
        AND timestamp >= ?
        AND timestamp <= ?
    """
    
    # Consulta para o período anterior
    previous_query = """
        SELECT COUNT(*)
        FROM detections
        JOIN epis ON detections.epi_id = epis.id
        WHERE epis.nome = ?
        AND timestamp >= ?
        AND timestamp < ?
    """
    
    # Obter contagens
    current_count = execute_db_query(current_query, 
        (epi_name, start_time, end_time), fetch_all=False)[0]
    
    previous_count = execute_db_query(previous_query,
        (epi_name, previous_start.strftime('%Y-%m-%d %H:%M:%S'), 
         previous_end.strftime('%Y-%m-%d %H:%M:%S')), fetch_all=False)[0]
    
    # Calcular a tendência
    if previous_count == 0:
        if current_count == 0:
            return 0
        return 100  # Se não havia violações antes e agora há, representa um aumento de 100%
    
    trend = ((current_count - previous_count) / previous_count) * 100
    return round(trend, 1)

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Rota principal que renderiza o dashboard.
    """
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    data = get_data(limit=5, start_time=start_time, end_time=end_time)
    epi_counts = get_epi_counts(start_time=start_time, end_time=end_time)
    total_detections = get_total_count(start_time=start_time, end_time=end_time)

    last_detection = data[0] if data else None

    processed_data = []
    for row in data:
        if row[2] and not isinstance(row[2], str):
            row = list(row)
            row[2] = row[2].decode('utf-8', errors='ignore')
        processed_data.append(row)

    labels = [item[0] for item in epi_counts]
    counts = [item[1] for item in epi_counts]
    chart_data = json.dumps({"labels": labels, "counts": counts})

    evolution_data = get_evolution_data(start_time=start_time, end_time=end_time)
    evolution_labels = [item[0] for item in evolution_data]
    evolution_counts = [item[1] for item in evolution_data]
    evolution_chart_data = json.dumps({"labels": evolution_labels, "counts": evolution_counts})

    return render_template('index.html',
        detections=processed_data,
        now=datetime.now(),
        total_detections=total_detections,
        last_detection=last_detection,
        chart_data=chart_data,
        evolution_chart_data=evolution_chart_data,
        active_page='dashboard')

@app.route('/detections', methods=['GET', 'POST'])
def detections():
    """
    Rota para a página de histórico de detecções.
    """
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    page = request.args.get('page', 1, type=int)
    per_page = 15
    offset = (page - 1) * per_page

    data = get_data(limit=per_page, start_time=start_time,
                    end_time=end_time, offset=offset)
    total_detections = get_total_count(start_time=start_time, end_time=end_time)

    processed_data = []
    for row in data:
        if row[2] and not isinstance(row[2], str):  # Fixed extra parenthesis
            row = list(row)
            row[2] = row[2].decode('utf-8', errors='ignore')
        processed_data.append(row)

    total_pages = math.ceil(total_detections / per_page)
    start_page = max(1, page - 2)
    end_page = min(page + 2, total_pages)

    return render_template('detections.html',
        detections=processed_data,
        now=datetime.now(),
        total_detections=total_detections,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        start_page=start_page,
        end_page=end_page,
        active_page='detections')

@app.route('/analytics', methods=['GET', 'POST'])
def analytics():
    """
    Rota para a página de análises.
    """
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    # Converter as datas para o formato correto se fornecidas
    if start_time:
        start_time = start_time.replace('T', ' ') + ':00'
    if end_time:
        end_time = end_time.replace('T', ' ') + ':00'

    # Obter dados para os cards e gráficos
    total_detections = get_total_count(start_time=start_time, end_time=end_time)
    violations_count = get_total_violations()  # Agora usa o total geral sem filtro
    compliance_rate = get_compliance_rate(start_time=start_time, end_time=end_time)
    most_common_epi = get_most_common_epi(start_time=start_time, end_time=end_time)

    # Dados para o gráfico de tendência
    trend_data = get_evolution_data(start_time=start_time, end_time=end_time)
    trend_labels = [item[0] for item in trend_data]
    trend_counts = [item[1] for item in trend_data]
    
    # Preparar dados do gráfico de tendência
    trend_chart_data = {
        'labels': trend_labels,
        'datasets': [{
            'label': 'Detecções',
            'data': trend_counts,
            'borderColor': '#3b82f6',
            'backgroundColor': 'rgba(59, 130, 246, 0.1)',
            'tension': 0.4,
            'fill': True
        }]
    }
    
    # Dados para o gráfico de pizza
    pie_data = get_epi_counts(start_time=start_time, end_time=end_time)
    pie_labels = [item[0] for item in pie_data]
    pie_counts = [item[1] for item in pie_data]
    
    # Dados para o gráfico mensal
    monthly_labels, monthly_values = get_monthly_comparison(start_time=start_time, end_time=end_time)

    # Resumo por EPI
    epi_summary = []
    total_violations = sum(count for _, count in pie_data)
    for epi, count in pie_data:
        percentage = (count / total_violations * 100) if total_violations > 0 else 0
        trend = get_epi_trend(epi, start_time, end_time)  # Calcula a tendência real
        epi_summary.append({
            'name': epi,
            'count': count,
            'percentage': round(percentage, 1),
            'trend': trend
        })

    return render_template('analytics.html',
        now=datetime.now(),
        total_detections=total_detections,
        violations_count=violations_count,
        compliance_rate=round(compliance_rate, 1),
        most_common_epi=most_common_epi,
        trend_data=json.dumps(trend_chart_data),
        pie_data=json.dumps({
            'labels': pie_labels,
            'data': pie_counts
        }),
        monthly_data=json.dumps({
            'labels': monthly_labels,
            'datasets': [{
                'label': 'Total de Detecções',
                'data': monthly_values,
                'backgroundColor': '#3b82f6'
            }]
        }),
        epi_summary=epi_summary,
        active_page='analytics')

@app.route('/get_data', methods=['GET'])
def get_data_for_update():
    """
    Rota para obter os dados atualizados para os gráficos e tabela.
    """
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    data = get_data_json(start_time=start_time, end_time=end_time)
    epi_counts = get_epi_counts(start_time=start_time, end_time=end_time)
    evolution_data = get_evolution_data(start_time=start_time, end_time=end_time)  # Adicionado

    labels = [item[0] for item in epi_counts]
    counts = [item[1] for item in epi_counts]
    chart_data = {"labels": labels, "counts": counts}

    evolution_labels = [item[0] for item in evolution_data]  # Adicionado
    evolution_counts = [item[1] for item in evolution_data]  # Adicionado
    evolution_chart_data = {"labels": evolution_labels, "counts": evolution_counts}  # Adicionado

    total_detections = get_total_count(start_time=start_time, end_time=end_time)  # Adicionado

    return jsonify({
        "data": data,
        "chart_data": chart_data,
        "evolution_chart_data": evolution_chart_data,  # Adicionado
        "total_detections": total_detections  # Adicionado
    })

@app.route('/about')
def about():
    """
    Rota para a página Quem Somos.
    """
    return render_template('about.html', 
                         now=datetime.now(),
                         active_page='about')

@app.route('/image/<int:detection_id>')
def display_image(detection_id):
    """
    Rota para exibir a imagem de uma detecção específica.
    """
    image_data = get_detection_image(detection_id)
    if image_data:
        response = make_response(image_data)
        response.headers.set('Content-Type', 'image/jpeg')
        return response
    return "Imagem não encontrada", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)