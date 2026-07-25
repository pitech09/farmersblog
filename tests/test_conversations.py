"""
Automated tests for the direct messaging (conversation) feature.

Covers:
- Starting a conversation (GET /messages/<username>)
- Sending a message (POST /messages/send)
- Inbox listing (GET /messages)
- CSRF enforcement
- Empty message validation
- Self-message prevention
- Rapid duplicate prevention
"""
import json
import pytest
from app.extensions import db
from app.models import User, Message


def get_csrf_token(client):
    """Fetch CSRF token from meta tag on any page."""
    resp = client.get('/')
    token = None
    if b'csrf-token' in resp.data:
        import re
        m = re.search(rb'content="([^"]+)"', resp.data[resp.data.find(b'csrf-token'):])
        if m:
            token = m.group(1).decode()
    return token


def login_for_csrf(client, email, password):
    """Login with CSRF enabled to get a real session."""
    resp = client.get('/login')
    import re
    m = re.search(rb'name="csrf_token" value="([^"]+)"', resp.data)
    token = m.group(1).decode() if m else ''
    client.post('/login', data={
        'email': email,
        'password': password,
        'csrf_token': token
    }, follow_redirects=True)
    return client


# --- Test: Start conversation ---
def test_start_conversation(alice, bob):
    """Login as alice, open /messages/bob, should see bob's name and a form."""
    resp = alice.get('/messages/bob')
    assert resp.status_code == 200
    assert b'bob' in resp.data
    assert b'messageForm' in resp.data or b'form' in resp.data


# --- Test: Send message ---
def test_send_message(alice, bob):
    """Alice sends a message to bob; message saved in DB."""
    resp = alice.post('/messages/send', json={
        'recipient_username': 'bob',
        'body': 'Hello Bob!'
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['body'] == 'Hello Bob!'

    msg = Message.query.filter_by(sender_id=alice.id, recipient_id=bob.id).first()
    assert msg is not None
    assert msg.body == 'Hello Bob!'


# --- Test: Inbox shows conversation ---
def test_inbox(alice, bob):
    """After alice sends a message, bob's inbox shows the conversation."""
    alice.post('/messages/send', json={
        'recipient_username': 'bob',
        'body': 'Hi there'
    })
    # Logout alice, login as bob
    alice.get('/logout')
    from tests.conftest import login
    login(alice, 'bob@test.local', 'password123')
    resp = alice.get('/messages')
    assert resp.status_code == 200
    assert b'alice' in resp.data
    assert b'Hi there' in resp.data


# --- Test: CSRF enforcement ---
def test_csrf_enforced(app, client):
    """POST without CSRF token should fail with 400."""
    app.config['WTF_CSRF_ENABLED'] = True
    from tests.conftest import make_user, login
    make_user('alice', 'alice@test.local', 'password123')
    make_user('bob', 'bob@test.local', 'password123')
    login(client, 'alice@test.local', 'password123')
    resp = client.post('/messages/send', json={
        'recipient_username': 'bob',
        'body': 'Hello'
    })
    assert resp.status_code == 400
    app.config['WTF_CSRF_ENABLED'] = False


# --- Test: Empty message rejected ---
def test_empty_message(alice, bob):
    """Sending an empty body should be rejected."""
    resp = alice.post('/messages/send', json={
        'recipient_username': 'bob',
        'body': ''
    })
    assert resp.status_code == 400
    data = resp.get_json()
    assert 'error' in data


# --- Test: Message to self ---
def test_message_to_self(alice):
    """Sending a message to yourself should be prevented."""
    resp = alice.post('/messages/send', json={
        'recipient_username': 'alice',
        'body': 'Hello me'
    })
    assert resp.status_code == 400
    data = resp.get_json()
    assert 'error' in data


# --- Test: Rapid duplicate prevention ---
def test_no_duplicate_on_rapid_send(alice, bob):
    """Sending the same message twice should create two messages (not dedupe),
    but rapid identical requests should not cause errors."""
    resp1 = alice.post('/messages/send', json={
        'recipient_username': 'bob',
        'body': 'Hello'
    })
    resp2 = alice.post('/messages/send', json={
        'recipient_username': 'bob',
        'body': 'Hello'
    })
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    count = Message.query.filter_by(sender_id=alice.id, recipient_id=bob.id).count()
    assert count == 2


# --- Test: Non-existent user ---
def test_message_nonexistent_user(alice):
    """Sending to a non-existent user should return 404."""
    resp = alice.post('/messages/send', json={
        'recipient_username': 'ghost',
        'body': 'Hello?'
    })
    assert resp.status_code == 404


# --- Test: Conversation marks messages as read ---
def test_conversation_marks_read(alice, bob):
    """When bob opens the conversation, alice's messages are marked read."""
    alice.post('/messages/send', json={
        'recipient_username': 'bob',
        'body': 'Read me'
    })
    alice.get('/logout')
    from tests.conftest import login
    login(alice, 'bob@test.local', 'password123')
    alice.get('/messages/alice')
    msg = Message.query.filter_by(sender_id=alice.id, recipient_id=bob.id).first()
    assert msg.read is True
