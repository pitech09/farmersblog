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
from app.models import User, Post, Media, Comment, Message, Group, Listing

app = create_app()

# Sample data
sample_users = [
    {'username': 'farmer_john', 'email': 'john@farmersblog.com', 'password': 'password123', 'first_name': 'John', 'last_name': 'Doe', 'bio': 'Corn farmer from Iowa. Love the land!'},
    {'username': 'green_thumb', 'email': 'green@farmersblog.com', 'password': 'password123', 'first_name': 'Jane', 'last_name': 'Smith', 'bio': 'Organic gardening enthusiast. Growing food for a better world.'},
    {'username': 'harvest_queen', 'email': 'queen@farmersblog.com', 'password': 'password123', 'first_name': 'Emily', 'last_name': 'Davis', 'bio': 'Woman farmer running a sustainable family farm.'},
    {'username': 'soil_sam', 'email': 'sam@farmersblog.com', 'password': 'password123', 'first_name': 'Sam', 'last_name': 'Wilson', 'bio': 'Soil scientist and regenerative agriculture advocate.'},
    {'username': 'organic_annie', 'email': 'annie@farmersblog.com', 'password': 'password123', 'first_name': 'Annie', 'last_name': 'Miller', 'bio': 'Certified organic farmer. No pesticides, no regrets.'},
]

sample_posts = [
    {'caption': 'Beautiful sunrise over the cornfields this morning! 🌽 #farmlife #sunrise'},
    {'caption': 'Just harvested these gorgeous tomatoes from the garden. Nothing beats homegrown! 🍅 #gardening #organic'},
    {'caption': 'The new tractor arrived today! Ready for the planting season. 🚜 #farming #newmachinery'},
    {'caption': 'Our free-range chickens are loving the new coop we built. Fresh eggs every morning! 🐔 #chickens #farmfresh'},
    {'caption': 'Lavender fields in full bloom. The smell is absolutely incredible. 💜 #lavender #flowers'},
    {'caption': 'Teaching the next generation about sustainable farming. Proud moment! 🌱 #education #sustainable'},
    {'caption': 'Rainy day on the farm. The crops are loving this weather! 🌧️ #rain #grateful'},
    {'caption': 'Farmers market was a success today! Sold out of almost everything. 🥬 #farmersmarket #local'},
    {'caption': 'New beehives installed! Looking forward to our first honey harvest. 🐝 #beekeeping #honey'},
    {'caption': 'The orchard is looking beautiful this spring. Apple blossoms everywhere! 🌸 #orchard #spring'},
]

sample_comments = [
    'Absolutely stunning view!',
    'Great work! Keep it up.',
    'I wish I could grow tomatoes like that!',
    'How long did it take to grow these?',
    'This is so inspiring!',
    'Beautiful! Thanks for sharing.',
    'What zone are you in?',
    'I love this! 😍',
    'Can you share some tips?',
    'Amazing! 👏',
]

sample_groups = [
    {'name': 'Organic Farmers', 'description': 'A group for organic and sustainable farming enthusiasts.'},
    {'name': 'Livestock Lovers', 'description': 'Share tips and photos about raising livestock.'},
    {'name': 'Tech in Agriculture', 'description': 'Discuss the latest farming technology and equipment.'},
]


def seed():
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        print('Creating sample users...')
        users = []
        for user_data in sample_users:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                bio=user_data.get('bio', '')
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            users.append(user)
        db.session.commit()
        print(f'Created {len(users)} users')

        print('Creating sample groups...')
        groups = []
        for group_data in sample_groups:
            group = Group(
                name=group_data['name'],
                description=group_data['description'],
                creator_id=random.choice(users).id
            )
            db.session.add(group)
            db.session.flush()
            group.members.append(group.creator)
            for user in random.sample([u for u in users if u.id != group.creator_id], random.randint(1, 3)):
                group.members.append(user)
            groups.append(group)
        db.session.commit()
        print(f'Created {len(groups)} groups')

        print('Creating sample posts with media...')
        posts = []
        for i, post_data in enumerate(sample_posts):
            author = random.choice(users)
            created_at = datetime.utcnow() - timedelta(hours=i * 3)

            post = Post(
                author_id=author.id,
                caption=post_data['caption'],
                created_at=created_at
            )
            db.session.add(post)
            db.session.flush()

            num_media = random.randint(0, 3)
            for j in range(num_media):
                media = Media(
                    post_id=post.id,
                    filename='placeholder.jpg',
                    media_type='image',
                    position=j
                )
                db.session.add(media)

            posts.append(post)
        db.session.commit()
        print(f'Created {len(posts)} posts with media')

        print('Adding likes...')
        for post in posts:
            likers = random.sample(users, random.randint(1, 3))
            for liker in likers:
                if liker.id != post.author_id:
                    post.likes.append(liker)
        db.session.commit()
        print('Likes added!')

        print('Adding comments...')
        for post in posts:
            num_comments = random.randint(1, 4)
            for _ in range(num_comments):
                commenter = random.choice(users)
                comment = Comment(
                    post_id=post.id,
                    author_id=commenter.id,
                    text=random.choice(sample_comments)
                )
                db.session.add(comment)
        db.session.commit()
        print('Comments added!')

        print('Adding sample messages...')
        for _ in range(5):
            sender = random.choice(users)
            recipient = random.choice([u for u in users if u.id != sender.id])
            message = Message(
                sender_id=sender.id,
                recipient_id=recipient.id,
                body=random.choice([
                    'Hey! Love your photos!',
                    'How do you grow such amazing tomatoes?',
                    'Would love to collaborate on a project!',
                    'Great tips on the group!',
                    'Thanks for following me!'
                ]),
                timestamp=datetime.utcnow() - timedelta(hours=random.randint(1, 48))
            )
            db.session.add(message)
        db.session.commit()
        print('Messages added!')

        print('Creating sample marketplace listings...')
        sample_listings = [
            {'title': 'John Deere Tractor 2020', 'description': 'Well maintained tractor, low hours. Perfect for medium-sized farms.', 'price': 25000.00, 'category': 'Equipment', 'location': 'Iowa'},
            {'title': 'Organic Tomato Seeds - 500 pack', 'description': 'Heirloom organic tomato seeds. Non-GMO, open-pollinated.', 'price': 12.99, 'category': 'Seeds', 'location': ''},
            {'title': 'Angus Calves - 2 available', 'description': 'Healthy Angus calves, 6 months old. Vaccinated and dewormed.', 'price': 850.00, 'category': 'Livestock', 'location': 'Texas'},
            {'title': 'Fresh Organic Honey - 1lb jars', 'description': 'Pure wildflower honey from our farm. No additives.', 'price': 15.00, 'category': 'Produce', 'location': 'Oregon'},
            {'title': 'Used Irrigation System', 'description': 'Complete drip irrigation system, barely used. Covers 2 acres.', 'price': 0, 'category': 'Equipment', 'location': 'California'},
        ]
        for listing_data in sample_listings:
            seller = random.choice(users)
            listing = Listing(
                seller_id=seller.id,
                title=listing_data['title'],
                description=listing_data['description'],
                price=listing_data['price'],
                category=listing_data['category'],
                location=listing_data['location'],
                image_filename='placeholder.jpg',
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72))
            )
            db.session.add(listing)
        db.session.commit()
        print(f'Created {len(sample_listings)} listings')

        print('\n✅ Database seeded successfully!')
        print(f'   Users: {len(users)}')
        print(f'   Posts: {len(posts)}')
        print(f'   Comments: {Comment.query.count()}')
        print(f'   Groups: {len(groups)}')
        print(f'   Messages: {Message.query.count()}')
        print(f'   Listings: {len(sample_listings)}')
        print('\nSample login credentials:')
        print('   Email: john@farmersblog.com')
        print('   Password: password123')


if __name__ == '__main__':
    seed()