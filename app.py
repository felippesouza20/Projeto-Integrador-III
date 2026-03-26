# app.py
# -------------------------------------------
# Sistema de Controle de Estoque com Flask
# Autor: Seu Nome
# -------------------------------------------

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------------------------
# Configuração da aplicação Flask
# -------------------------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///estoque.db'  # Banco de dados SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'chave-secreta-flask'  # Necessária para sessão e mensagens flash

db = SQLAlchemy(app)

# -------------------------------------------
# Modelo de Usuário
# -------------------------------------------
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)

# -------------------------------------------
# Modelo de Item de Estoque
# -------------------------------------------
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    produto = db.Column(db.String(100), nullable=False)
    quantidade_estoque = db.Column(db.Integer, nullable=False)
    validade = db.Column(db.String(20))
    preco = db.Column(db.Float)

    comentario = db.Column(db.String(255))  # <-- Adicionado

# -------------------------------------------
# Modelo: Saída de Material
# -------------------------------------------

from datetime import datetime

class HistoricoSaida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship('Item', backref=db.backref('historico_saidas', lazy=True))




class Saida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    data_saida = db.Column(db.String(20))
    responsavel = db.Column(db.String(100))

    item = db.relationship('Item', backref=db.backref('saidas', lazy=True))



# -------------------------------------------
# Rota: Página de Login
# -------------------------------------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('lista'))
        else:
            flash('E-mail ou senha incorretos.', 'danger')

    return render_template('login.html')

# -------------------------------------------
# Rota: Cadastro de Usuário
# -------------------------------------------
@app.route('/signup', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = generate_password_hash(request.form['senha'])

        if Usuario.query.filter_by(email=email).first():
            flash('E-mail já cadastrado!', 'warning')
            return redirect(url_for('signup'))

        novo_usuario = Usuario(nome=nome, email=email, senha=senha)
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Usuário registrado com sucesso!', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

# -------------------------------------------
# Rota: Lista de Itens
# -------------------------------------------
@app.route('/index')
def list():
    if 'usuario_id' not in session:
        flash('Faça login primeiro.', 'warning')
        return redirect(url_for('login'))

    itens = Item.query.all()
    return render_template('index.html', itens=itens)

# -------------------------------------------
# Rota: Adicionar Item
# -------------------------------------------
@app.route('/addproduct', methods=['GET', 'POST'])
def addproduct():
    if request.method == 'POST':
        try:
            codigo = request.form['codigo']
            produto = request.form['produto']
            quantidade = int(request.form['quantidade'])
            validade = request.form['validade']
            preco = float(request.form['preco']) if request.form['preco'] else 0.0
            comentario = request.form.get('comentario', '')

            # Verifica se o código já existe
            if Item.query.filter_by(codigo=codigo).first():
                flash('⚠️ Já existe um item com esse código!', 'warning')
                return redirect(url_for('addproduct'))

            novo_item = Item(
                codigo=codigo,
                produto=produto,
                quantidade_estoque=quantidade,
                validade=validade,
                preco=preco,
                comentario=comentario
            )

            db.session.add(novo_item)
            db.session.commit()
            flash('✅ Material cadastrado com sucesso!', 'success')
            return redirect(url_for('lista'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erro ao cadastrar material: {e}', 'danger')

    return render_template('addproduct.html')





# -------------------------------------------
# Rota: Saída de Material
# -------------------------------------------


@app.route('/removeproduct/<int:id>', methods=['GET', 'POST'])
def removeproduct(id):
    item = Item.query.get_or_404(id)
    if request.method == 'POST':
        quantidade_saida = int(request.form['quantidade'])
        responsavel = request.form['responsavel']

        if quantidade_saida > item.quantidade_estoque:
            flash('Quantidade insuficiente no estoque!', 'danger')
        else:
            item.quantidade_estoque -= quantidade_saida

            registro = HistoricoSaida(
                item_id=item.id,
                quantidade=quantidade_saida,
                responsavel=responsavel
            )

            db.session.add(registro)
            db.session.commit()
            flash('Saída registrada com sucesso!', 'success')
        return redirect(url_for('lista'))
    return render_template('removeproduct.html', item=item)


@app.route('/history')
def history():
    history = HistoricoSaida.query.order_by(HistoricoSaida.data.desc()).all()
    return render_template('history.html', history=history)

# -------------------------------------------
# Rota: Editar Item
# -------------------------------------------
@app.route('/editproduct/<int:id>', methods=['GET', 'POST'])
def editproduct(id):
    item = Item.query.get_or_404(id)

    if request.method == 'POST':
        try:
            item.codigo = request.form['codigo']
            item.produto = request.form['produto']
            item.quantidade_estoque = int(request.form['quantidade'])
            item.validade = request.form['validade']
            item.preco = float(request.form['preco']) if request.form['preco'] else 0.0
            item.comentario = request.form.get('comentario', '')

            db.session.commit()
            flash('✅ Item atualizado com sucesso!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erro ao atualizar item: {e}', 'danger')

    return render_template('editproduct.html', item=item)



# -------------------------------------------
# Rota: Excluir Item
# -------------------------------------------
@app.route('/excluir/<int:id>')
def removeproduct(id):
    item = Item.query.get(id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash('Item removido com sucesso!', 'info')
    return redirect(url_for('index'))

@app.route('/deletar/<int:id>')
def deletar(id):
    return removeproduct(id)



# -------------------------------------------
# Rota: Logout
# -------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado.', 'info')
    return redirect(url_for('login'))

# -------------------------------------------
# Criação do Banco de Dados
# -------------------------------------------
with app.app_context():
    db.create_all()

# -------------------------------------------
# Inicialização do servidor
# -------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

@app.cli.command('reset-db')
def reset_db():
    """Apaga e recria o banco de dados."""
    db.drop_all()
    db.create_all()
    print("Banco de dados reiniciado com sucesso!")
