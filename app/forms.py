from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SelectField, FileField, PasswordField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional, NumberRange
from app.models import User, Group


def coerce_optional_int(value):
    """Coerce a value to int, returning None for empty strings."""
    if value == '' or value is None:
        return None
    return int(value)


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=50),
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')


class PostForm(FlaskForm):
    caption = TextAreaField('Caption', validators=[
        DataRequired()
    ])
    media = FileField('Media', validators=[Optional()])
    group_id = SelectField('Post to Group', coerce=coerce_optional_int, validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.group_id.choices = [('', '— Public Feed —')]


class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=50),
    ])
    bio = TextAreaField('Bio', validators=[
        Optional(),
        Length(max=300, message='Bio must be under 300 characters.')
    ])
    location = StringField('Location', validators=[
        Optional(),
        Length(max=120, message='Location must be under 120 characters.')
    ])
    avatar = FileField('Profile Picture', validators=[Optional()])

    def __init__(self, current_user_id=None, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.current_user_id = current_user_id

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user and user.id != self.current_user_id:
            raise ValidationError('Username already taken.')


class GroupForm(FlaskForm):
    name = StringField('Group Name', validators=[
        DataRequired(),
        Length(min=3, max=100),
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description must be under 500 characters.')
    ])

    def validate_name(self, name):
        group = Group.query.filter_by(name=name.data).first()
        if group:
            raise ValidationError('Group name already exists.')


class ListingForm(FlaskForm):
    title = StringField('Title', validators=[
        DataRequired(),
        Length(min=3, max=200),
    ])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = FloatField('Price (M)', validators=[DataRequired(), NumberRange(min=0)])
    category = SelectField('Category', validators=[DataRequired()])
    location = StringField('Location', validators=[Optional(), Length(max=100)])
    image = FileField('Image', validators=[DataRequired()])

    def __init__(self, categories=None, *args, **kwargs):
        super(ListingForm, self).__init__(*args, **kwargs)
        if categories:
            self.category.choices = [(c, c) for c in categories]
        else:
            self.category.choices = []