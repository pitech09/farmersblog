from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.models import User, Message, Notification, Listing

messages_bp = Blueprint('messages', __name__)


@messages_bp.route('/')
@login_required
@limiter.limit("30 per minute")
def inbox():
    # Get all messages involving current user
    messages = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
    ).order_by(Message.timestamp.desc()).all()

    conversations_dict = {}
    for msg in messages:
        other_id = msg.recipient_id if msg.sender_id == current_user.id else msg.sender_id
        if other_id not in conversations_dict:
            conversations_dict[other_id] = {
                'user': User.query.get(other_id),
                'last_message': msg,
                'unread_count': 0
            }
        # Keep the newest message as last_message
        if msg.id > conversations_dict[other_id]['last_message'].id:
            conversations_dict[other_id]['last_message'] = msg

    # Calculate unread counts and filter out invalid users
    conversations = []
    for uid, conv in conversations_dict.items():
        if not conv['user']:
            continue
        unread = Message.query.filter_by(
            sender_id=uid,
            recipient_id=current_user.id,
            read=False
        ).count()
        conv['unread_count'] = unread
        conversations.append(conv)

    conversations.sort(key=lambda c: c['last_message'].timestamp, reverse=True)

    return render_template('messages/inbox.html', conversations=conversations)


@messages_bp.route('/<username>')
@login_required
def conversation(username):
    other_user = User.query.filter_by(username=username).first_or_404()

    if other_user == current_user:
        flash('You cannot message yourself.', 'warning')
        return redirect(url_for('messages.inbox'))

    # No mutual-follow requirement; any authenticated user can message any other user
    can_message = True

    # Mark messages as read
    unread = Message.query.filter_by(
        sender_id=other_user.id,
        recipient_id=current_user.id,
        read=False
    ).all()
    for msg in unread:
        msg.read = True
    db.session.commit()

    # Get chat history
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == other_user.id)) |
        ((Message.sender_id == other_user.id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()

    return render_template('messages/conversation.html', other_user=other_user, messages=messages, can_message=can_message)


@messages_bp.route('/send', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def send():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request.'}), 400

    recipient_username = data.get('recipient_username', '').strip()
    body = data.get('body', '').strip()

    if not recipient_username or not body:
        return jsonify({'error': 'Recipient and message body are required.'}), 400

    # Sanitize message body
    from bleach import clean
    body = clean(body, tags=[], strip=True)[:5000]

    recipient = User.query.filter_by(username=recipient_username).first()
    if not recipient:
        return jsonify({'error': 'User not found.'}), 404

    if recipient == current_user:
        return jsonify({'error': 'You cannot message yourself.'}), 400

    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient.id,
        body=body
    )
    db.session.add(message)
    db.session.flush()

    # Check if this is a buyer interest message from a marketplace listing
    listing_id = data.get('listing_id')
    if listing_id:
        listing = Listing.query.get(listing_id)
        if listing and listing.seller_id == recipient.id:
            notification = Notification(
                recipient_id=recipient.id,
                actor_id=current_user.id,
                type='buyer_interest',
                message=f'{current_user.username} is interested in your listing: {listing.title}',
                link=url_for('messages.conversation', username=current_user.username)
            )
            db.session.add(notification)

    db.session.commit()

    return jsonify({
        'success': True,
        'id': message.id,
        'body': message.body,
        'sender_username': current_user.username,
        'timestamp': message.timestamp.strftime('%b %d, %Y at %I:%M %p')
    })


@messages_bp.route('/<username>/poll')
@login_required
def poll_messages(username):
    """Poll for new messages since a given timestamp."""
    other_user = User.query.filter_by(username=username).first_or_404()
    since = request.args.get('since', type=int, default=0)

    new_messages = Message.query.filter(
        (Message.sender_id == other_user.id) &
        (Message.recipient_id == current_user.id) &
        (Message.id > since)
    ).order_by(Message.timestamp.asc()).all()

    messages_data = []
    for msg in new_messages:
        messages_data.append({
            'id': msg.id,
            'body': msg.body,
            'sender_username': other_user.username,
            'timestamp': msg.timestamp.strftime('%b %d, %Y at %I:%M %p')
        })

    return jsonify({'messages': messages_data})