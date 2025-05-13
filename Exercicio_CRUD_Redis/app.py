from flask import Flask, render_template, request, redirect, url_for, flash
import redis
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'  # Necessário para mensagens flash

# Configuração do Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)
STATUS_VALIDOS = ['Pendente', 'Em Progresso', 'Concluída']

def gerar_id():
    """Gera um novo ID para a tarefa incrementando um contador no Redis."""
    return redis_client.incr('contador_tarefas')

def get_redis_connection():
    """Estabelece conexão com o Redis com tratamento de erros robusto"""
    try:
        r = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            socket_connect_timeout=5,
            socket_timeout=5,         
            decode_responses=True
        )
        r.ping()
        return r
    except redis.exceptions.ConnectionError as e:
        print(f"Erro de conexão com Redis: {str(e)}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao conectar ao Redis: {str(e)}")
        return None

@app.route('/')
def index():
    """Página inicial que lista todas as tarefas."""
    redis_client = get_redis_connection()
    
    if redis_client is None:
        flash("Não foi possível conectar ao banco de dados Redis. Verifique se o servidor está em execução.", "error")
        return render_template('index.html', tarefas=[], status_validos=STATUS_VALIDOS)
    
    try:
        tarefas = []
        for chave in redis_client.scan_iter('tarefa:*'):
            tarefa = redis_client.hgetall(chave)
            tarefa['id'] = chave.split(':')[1]
            tarefas.append(tarefa)
        return render_template('index.html', tarefas=tarefas, status_validos=STATUS_VALIDOS)
        
    except Exception as e:
        flash(f"Erro ao acessar as tarefas: {str(e)}", "error")
        return render_template('index.html', tarefas=[], status_validos=STATUS_VALIDOS)

@app.route('/criar', methods=['GET', 'POST'])
def criar_tarefa():
    """Rota para criar uma nova tarefa."""
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        
        if not titulo or not descricao:
            flash('Título e descrição são obrigatórios!', 'error')
            return redirect(url_for('criar_tarefa'))
            
        id_tarefa = gerar_id()
        chave = f'tarefa:{id_tarefa}'
        data_criacao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        redis_client.hset(chave, 'titulo', titulo)
        redis_client.hset(chave, 'descricao', descricao)
        redis_client.hset(chave, 'data_criacao', data_criacao)
        redis_client.hset(chave, 'status', 'Pendente')
        
        flash('Tarefa criada com sucesso!', 'success')
        return redirect(url_for('index'))
    
    return render_template('criar.html')

@app.route('/editar/<int:id_tarefa>', methods=['GET', 'POST'])
def editar_tarefa(id_tarefa):
    """Rota para editar uma tarefa existente."""
    chave = f'tarefa:{id_tarefa}'
    redis_client = get_redis_connection()
    
    if not redis_client.exists(chave):
        flash('Tarefa não encontrada!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        campo = request.form.get('campo')
        valor = request.form.get('valor')
        
        if campo not in ['titulo', 'descricao', 'status']:
            flash('Campo inválido para atualização!', 'error')
        elif campo == 'status' and valor not in STATUS_VALIDOS:
            flash(f'Status inválido. Use um dos seguintes: {", ".join(STATUS_VALIDOS)}', 'error')
        else:
            redis_client.hset(chave, campo, valor)
            flash('Tarefa atualizada com sucesso!', 'success')
        
        return redirect(url_for('index'))
    
    # Obtém e formata os dados da tarefa
    tarefa_raw = redis_client.hgetall(chave)
    tarefa = {
        'id': id_tarefa,
        'titulo': tarefa_raw.get(b'titulo', b'').decode(),
        'descricao': tarefa_raw.get(b'descricao', b'').decode(),
        'status': tarefa_raw.get(b'status', b'').decode(),
        'data_criacao': tarefa_raw.get(b'data_criacao', b'').decode()
    }
    
    return render_template('editar.html', tarefa=tarefa, status_validos=STATUS_VALIDOS)

@app.route('/deletar/<int:id_tarefa>')
def deletar_tarefa(id_tarefa):
    """Rota para deletar uma tarefa."""
    chave = f'tarefa:{id_tarefa}'
    if redis_client.exists(chave):
        redis_client.delete(chave)
        flash('Tarefa deletada com sucesso!', 'success')
    else:
        flash('Tarefa não encontrada!', 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)