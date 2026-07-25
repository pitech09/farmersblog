from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager
import bleach
import re


def sanitize_text(text, max_length=5000):
    """Sanitize user input to prevent XSS."""
    if not text:
        return text
    # Strip all HTML tags
    cleaned = bleach.clean(text, tags=[], strip=True)
    # Limit length
    return cleaned[:max_length]


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Association tables
post_likes = db.Table('post_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True)
)

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

group_members = db.Table('group_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=datetime.utcnow)
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar_filename = db.Column(db.String(255), default=None)
    bio = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    liked_posts = db.relationship('Post', secondary=post_likes, back_populates='likes', lazy='dynamic')
    listings = db.relationship('Listing', backref='seller', lazy='dynamic', cascade='all, delete-orphan')

    # Follow relationships
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

    # Messages sent/received
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic', cascade='all, delete-orphan')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic', cascade='all, delete-orphan')

    # Groups
    groups_created = db.relationship('Group', backref='creator', lazy='dynamic', cascade='all, delete-orphan')
    groups_joined = db.relationship('Group', secondary=group_members, back_populates='members', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def follower_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return self.followed.count()

    @property
    def post_count(self):
        return self.posts.count()

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
            db.session.commit()
            return True
        return False

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
            db.session.commit()
            return True
        return False

    @property
    def unread_message_count(self):
        return Message.query.filter_by(recipient_id=self.id, read=False).count()

    def __repr__(self):
        return f'<User {self.username}>'


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    caption = db.Column(db.Text, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    media = db.relationship('Media', backref='post', lazy='dynamic', cascade='all, delete-orphan', order_by='Media.position')
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('User', secondary=post_likes, back_populates='liked_posts', lazy='dynamic')

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()

    @property
    def media_count(self):
        return self.media.count()

    @property
    def first_media(self):
        return self.media.order_by(Media.position).first()

    @property
    def media_list(self):
        return self.media.order_by(Media.position).all()

    def is_liked_by(self, user):
        if user.is_authenticated:
            return self.likes.filter(post_likes.c.user_id == user.id).count() > 0
        return False

    @property
    def caption_preview(self):
        if len(self.caption) > 150:
            return self.caption[:150] + '...'
        return self.caption

    @property
    def has_long_caption(self):
        return len(self.caption) > 150

    def __repr__(self):
        return f'<Post {self.id} by {self.author_id}>'


class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    media_type = db.Column(db.String(10), nullable=False)  # 'image' or 'video'
    position = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Media {self.id} {self.media_type} for Post {self.post_id}>'


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Comment {self.id} on Post {self.post_id}>'


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.recipient_id}>'


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text, default='')
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('User', secondary=group_members, back_populates='groups_joined', lazy='dynamic')
    posts = db.relationship('Post', backref='group', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def member_count(self):
        return self.members.count()

    @property
    def post_count(self):
        return self.posts.count()

    def is_member(self, user):
        if user.is_authenticated:
            return self.members.filter(group_members.c.user_id == user.id).count() > 0
        return False

    def add_member(self, user):
        if not self.is_member(user):
            self.members.append(user)
            db.session.commit()
            return True
        return False

    def remove_member(self, user):
        if self.is_member(user):
            self.members.remove(user)
            db.session.commit()
            return True
        return False

    def __repr__(self):
        return f'<Group {self.name}>'


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500), nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='notifications')
    actor = db.relationship('User', foreign_keys=[actor_id], backref='actions')

    def __repr__(self):
        return f'<Notification {self.id} type={self.type} for User {self.recipient_id}>'


class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200), default='')
    image_filename = db.Column(db.String(255), nullable=False)
    is_sold = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    LISTING_CATEGORIES = ['Seeds', 'Equipment', 'Livestock', 'Produce', 'Other']

    @property
    def price_display(self):
        if self.price == 0:
            return 'Free'
        return f'M{self.price:.2f}'

    def __repr__(self):
        return f'<Listing {self.id}: {self.title}>'