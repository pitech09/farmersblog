from flask import Blueprint, render_template, jsonify, request, url_for
from flask_login import login_required, current_user
from app.extensions import db, cache
from app.models import Notification

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notifications_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 20

    pagination = Notification.query.filter_by(recipient_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    notifications = pagination.items

    return render_template('notifications.html',
                         notifications=notifications,
                         pagination=pagination)


@notifications_bp.route('/unread-count')
@login_required
def unread_count():
    count = Notification.query.filter_by(
        recipient_id=current_user.id, read=False
    ).count()
    return jsonify({'count': count})


@notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)

    if notification.recipient_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    notification.read = True
    db.session.commit()
    return jsonify({'success': True})


@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(
        recipient_id=current_user.id, read=False
    ).update({'read': True})
    db.session.commit()
    return jsonify({'success': True})