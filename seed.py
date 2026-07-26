"""
Seed script to populate the database with sample users, posts, groups, and messages.
Run with: python seed.py
"""
import os
import sys
from datetime import datetime, timedelta
import random

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import User
app = create_app()

# Sample data
sample_users = [
    {'username': 'admin', 'email': 'admin@farmersblog.com', 'password': 'Justice2003', 'first_name': 'Khauhelo', 'last_name': 'Makara', 'bio': 'Platform administrator.', 'is_admin': True},
]


def seed():
    with app.app_context():
        # Clear existing data

        print('Creating sample users...')
        users = []
        for user_data in sample_users:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                bio=user_data.get('bio', ''),
                is_admin=user_data.get('is_admin', False)
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            users.append(user)
        db.session.commit()
        print(f'Created {len(users)} users')

        

        print('   Email: admin@farmersblog.com')
        print('   Password: admin123')
        print('   (dedicated admin account — change credentials after first login!)')


if __name__ == '__main__':
    seed()