from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///estoque.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'chave-secreta-flask'

db = SQLAlchemy(app)

# ---------------- DECORADOR LOGIN ---------------- #

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Faça login primeiro.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------- MODELOS ---------------- #

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    produto = db.Column(db.String(100), nullable=False)
    quantidade_estoque = db.Column(db.Integer, nullable=False)
    estoque_minimo = db.Column(db.Integer, default=5)
    validade = db.Column(db.String(20))
    preco = db.Column(db.Float)
    comentario = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)


class HistoricoSaida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    responsavel = db.Column(db.String(100), nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship('Item', backref='historico_saidas')


# ---------------- LOGIN ---------------- #

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('lista'))

        flash('E-mail ou senha incorretos.', 'danger')

    return render_template('login.html')


# ---------------- CADASTRO ---------------- #

@app.route('/signup', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        email = request.form.get('email')

        if Usuario.query.filter_by(email=email).first():
            flash('E-mail já cadastrado!', 'warning')
            return redirect(url_for('registrar'))

        novo_usuario = Usuario(
            nome=request.form.get('nome'),
            email=email,
            senha=generate_password_hash(request.form.get('senha'))
        )

        db.session.add(novo_usuario)
        db.session.commit()

        flash('Usuário registrado com sucesso!', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


# ---------------- LISTA ---------------- #

@app.route('/index')
@login_required
def lista():
    itens = Item.query.filter_by(ativo=True).all()
    return render_template('index.html', itens=itens)


# ---------------- ADICIONAR ---------------- #

@app.route('/addproduct', methods=['GET', 'POST'])
@login_required
def addproduct():
    if request.method == 'POST':
        try:
            codigo = request.form.get('codigo')

            if Item.query.filter_by(codigo=codigo).first():
                flash('Já existe esse código!', 'warning')
                return redirect(url_for('addproduct'))

            novo_item = Item(
                codigo=codigo,
                produto=request.form.get('produto'),
                quantidade_estoque=int(request.form.get('quantidade', 0)),
                estoque_minimo=int(request.form.get('estoque_minimo', 5)),
                validade=request.form.get('validade'),
                preco=float(request.form.get('preco') or 0),
                comentario=request.form.get('comentario', '')
            )

            db.session.add(novo_item)
            db.session.commit()

            flash('Item cadastrado!', 'success')
            return redirect(url_for('lista'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar: {e}', 'danger')

    return render_template('addproduct.html')


# ---------------- SAÍDA ---------------- #

@app.route('/removeproduct/<int:id>', methods=['GET', 'POST'])
@login_required
def saida_produto(id):
    item = Item.query.get_or_404(id)

    if request.method == 'POST':
        try:
            quantidade = int(request.form.get('quantidade', 0))
            responsavel = request.form.get('responsavel')

            if quantidade <= 0:
                flash('Quantidade inválida!', 'danger')
                return redirect(url_for('lista'))

            if quantidade > item.quantidade_estoque:
                flash('Estoque insuficiente!', 'danger')
            else:
                item.quantidade_estoque -= quantidade

                registro = HistoricoSaida(
                    item_id=item.id,
                    quantidade=quantidade,
                    responsavel=responsavel
                )

                db.session.add(registro)
                db.session.commit()

                flash('Saída registrada!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')

        return redirect(url_for('lista'))

    return render_template('removeproduct.html', item=item)


# ---------------- HISTÓRICO ---------------- #

@app.route('/history')
@login_required
def history():
    dados = HistoricoSaida.query.order_by(HistoricoSaida.data.desc()).all()
    return render_template('history.html', history=dados)


# ---------------- EDITAR ---------------- #

@app.route('/editproduct/<int:id>', methods=['GET', 'POST'])
@login_required
def editproduct(id):
    item = Item.query.get_or_404(id)

    if request.method == 'POST':
        item.codigo = request.form.get('codigo')
        item.produto = request.form.get('produto')
        item.quantidade_estoque = int(request.form.get('quantidade', 0))
        item.estoque_minimo = int(request.form.get('estoque_minimo', 5))
        item.validade = request.form.get('validade')
        item.preco = float(request.form.get('preco') or 0)
        item.comentario = request.form.get('comentario', '')

        db.session.commit()
        flash('Item atualizado!', 'success')
        return redirect(url_for('lista'))

    return render_template('editproduct.html', item=item)


# ---------------- EXCLUIR ---------------- #

@app.route('/excluir/<int:id>')
@login_required
def excluir_item(id):
    item = Item.query.get_or_404(id)
    item.ativo = False
    db.session.commit()

    flash('Item desativado!', 'info')
    return redirect(url_for('lista'))


# ---------------- ESTOQUE BAIXO ---------------- #

@app.route('/estoque-baixo')
@login_required
def estoque_baixo():
    itens = Item.query.filter(
        Item.quantidade_estoque <= Item.estoque_minimo,
        Item.ativo == True
    ).all()

    return render_template('index.html', itens=itens)


# ---------------- LOGOUT ---------------- #

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado.', 'info')
    return redirect(url_for('login'))

@app.route('/home')
def index():
    return redirect(url_for('lista'))

# ---------------- INIT ---------------- #

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
