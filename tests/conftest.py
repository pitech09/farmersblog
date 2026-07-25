import pytest
from app import create_app
from app.extensions import db
from app.models import User

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost'
    # Use SQLite in-memory for tests (isolated, fast, no external DB required)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app

@pytest.fixture
def client(app):
    with app.test_client() as c:
        with app.app_context():
            db.create_all()
            yield c
            db.session.remove()
            db.drop_all()

def make_user(username, email, password):
    u = User(username=username, email=email)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u

def login(client, email, password):
    return client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

@pytest.fixture
def alice(client):
    u = make_user('alice', 'alice@test.local', 'password123')
    login(client, 'alice@test.local', 'password123')
    return u

@pytest.fixture
def bob(client):
    return make_user('bob', 'bob@test.local', 'password123')

@pytest.fixture
def charlie(client):
    return make_user('charlie', 'charlie@test.local', 'password123')