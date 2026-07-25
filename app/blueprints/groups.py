from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.models import Group, Post, User

groups_bp = Blueprint('groups', __name__)


@groups_bp.route('/')
@login_required
def index():
    # Groups the user is a member of
    my_groups = Group.query.filter(Group.members.any(id=current_user.id)).all()
    # Other groups
    other_groups = Group.query.filter(~Group.members.any(id=current_user.id)).all()
    return render_template('groups/index.html', my_groups=my_groups, other_groups=other_groups)


@groups_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Group name is required.', 'danger')
            return render_template('groups/create.html')

        if Group.query.filter_by(name=name).first():
            flash('A group with that name already exists.', 'danger')
            return render_template('groups/create.html')

        group = Group(
            name=name,
            description=description,
            creator_id=current_user.id
        )
        db.session.add(group)
        db.session.flush()

        # Creator automatically joins
        group.members.append(current_user)
        db.session.commit()

        flash(f'Group "{name}" created successfully!', 'success')
        return redirect(url_for('groups.detail', group_name=name))

    return render_template('groups/create.html')


@groups_bp.route('/<group_name>')
def detail(group_name):
    group = Group.query.filter_by(name=group_name).first_or_404()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    pagination = Post.query.filter_by(group_id=group.id).order_by(
        Post.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    posts = pagination.items

    for post in posts:
        post.user_has_liked = post.is_liked_by(current_user)

    is_member = False
    if current_user.is_authenticated:
        is_member = group.is_member(current_user)

    members = group.members.order_by(User.username).all()

    return render_template('groups/detail.html',
                         group=group,
                         posts=posts,
                         pagination=pagination,
                         is_member=is_member,
                         members=members)


@groups_bp.route('/<group_name>/join', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def join(group_name):
    group = Group.query.filter_by(name=group_name).first_or_404()

    if group.is_member(current_user):
        group.remove_member(current_user)
        joined = False
        flash(f'You have left "{group.name}".', 'info')
    else:
        group.add_member(current_user)
        joined = True
        flash(f'You have joined "{group.name}"!', 'success')

    return jsonify({
        'joined': joined,
        'member_count': group.member_count
    })