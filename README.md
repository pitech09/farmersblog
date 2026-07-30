# farmersblog 🌾

A full-stack social network for farmers and gardening enthusiasts. Share photos and videos, follow other farmers, join groups, and send direct messages.

Built with **Flask**, **Bootstrap 5**, and **PostgreSQL** — featuring a clean, modern UI blending Apple's minimalism with Facebook's social accent and card-based layout.

Supports both development (PostgreSQL, local storage) and production (PostgreSQL, Cloudinary, Redis) deployments.

## Features

### 📸 Multi-Photo & Video Posts
- Upload multiple images and videos per post
- Gallery carousel on post detail pages
- Video playback with native controls
- Thumbnail grid on profile pages

### 👤 User Profiles
- Public profile page with avatar, bio, location, follower/following counts
- Edit profile (avatar, bio, username, location)
- Grid of user's posts with pagination

### ❤️ Follow System
- Follow/unfollow other farmers (AJAX toggle)
- "Following" feed tab to see posts from people you follow
- Follower/following counts on profiles

### 💬 Direct Messaging
- Private messaging between users
- Inbox with conversation list and unread badges
- Real-time message polling (every 8 seconds)
- AJAX message sending

### 👥 Groups
- Create and join farming groups
- Group-exclusive feeds (only members can post)
- Member lists with avatars
- Join/leave groups (AJAX toggle)

### 🔍 Search & Discovery
- **Post search**: Search all public posts by caption text (`/search/posts?q=...`)
- **User search**: Discover other farmers by username or location (`/search/users?q=...`)
- Location displayed on profiles and searchable in user discovery

### ⚡ Optimistic UI
- **Likes**: Heart icon and count update immediately on click with scale-pulse animation. Automatically reverts on server failure.
- **Comments**: New comment appears instantly with "Sending..." indicator, updated with server timestamp on success.

### 🎨 Core Features
- Public feed with pagination
- Like/unlike posts (AJAX, optimistic)
- Comments (AJAX submission, optimistic)
- Share posts (copy link to clipboard)
- Responsive mobile-first design
- Apple + Facebook design language

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3, Flask |
| ORM | SQLAlchemy |
| Database | PostgreSQL (both development and production) |
| Frontend | Jinja2, Bootstrap 5, vanilla JavaScript |
| Auth | Flask-Login (session-based) |
| Media | Local filesystem (dev) / Cloudinary (prod) |
| Cache | SimpleCache (dev) / Redis (prod) |
| Rate Limiting | In-memory (dev) / Redis (prod) |

## Project Structure

```
farmersblog/
├── app/
│   ├── __init__.py              # App factory
│   ├── models.py                # SQLAlchemy models
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── auth.py              # Login/register/logout
│   │   ├── main.py              # Home feed, post detail
│   │   ├── posts.py             # Create, like, comment
│   │   ├── profile.py           # User profiles, follow, settings
│   │   ├── messages.py          # Direct messaging
│   │   ├── groups.py            # Groups
│   │   ├── search.py            # Post & user search
│   │   └── notifications.py     # Notifications
│   ├── templates/
│   │   ├── base.html            # Layout with navbar
│   │   ├── index.html           # Home feed with tabs
│   │   ├── _post_card.html      # Post card partial
│   │   ├── post_detail.html     # Post detail with carousel
│   │   ├── search/
│   │   │   ├── posts.html       # Post search results
│   │   │   └── users.html       # User discovery
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── posts/
│   │   │   └── create.html      # Multi-media upload form
│   │   ├── profile/
│   │   │   ├── public.html      # Public profile page
│   │   │   └── settings.html    # Edit profile
│   │   ├── messages/
│   │   │   ├── inbox.html       # Conversation list
│   │   │   └── conversation.html # Chat window
│   │   └── groups/
│   │       ├── index.html       # Group listing
│   │       ├── detail.html      # Group feed
│   │       └── create.html      # Create group form
│   └── static/
│       ├── style.css
│       ├── script.js            # Optimistic UI, AJAX logic
│       └── uploads/
│           ├── posts/           # Uploaded images/videos
│           └── avatars/         # Profile pictures
├── run.py                       # Entry point
├── seed.py                      # Database seeder
├── requirements.txt
├── .env.example
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- pip
- virtualenv (recommended)
- PostgreSQL

### 1. Clone the repository

```bash
git clone <repository-url>
cd farmersblog
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` to set:
- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `FLASK_ENV=development` (default, for local development)
- `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/farmersblog_dev` (default, works out of the box with PostgreSQL running locally)

### 5. Create the database

```bash
sudo -u postgres psql -c "CREATE DATABASE farmersblog_dev;"
```

### 6. Run the application

```bash
python run.py
```

The app will be available at **http://localhost:5000**

### 7. (Optional) Seed the database with sample data

```bash
python seed.py
```

This creates 5 sample users, 10 posts with multiple media, 3 groups, and sample messages.

**Sample login credentials:**
- Email: `john@farmersblog.com`
- Password: `password123`

---

## Production Deployment

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Redis server (for caching and rate limiting)
- Cloudinary account (for media storage)
- HTTPS enabled (recommended)

### 1. Environment Setup

Create a production `.env` with:

```env
FLASK_ENV=production
SECRET_KEY=<your-strong-secret-key>
DATABASE_URL=postgresql://user:password@localhost/farmersblog
CLOUDINARY_ENABLED=true
CLOUDINARY_CLOUD_NAME=<your-cloud-name>
CLOUDINARY_API_KEY=<your-api-key>
CLOUDINARY_API_SECRET=<your-api-secret>
REDIS_URL=redis://localhost:6379/0
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Setup

Install PostgreSQL and create a database:

```bash
sudo -u postgres psql
CREATE DATABASE farmersblog;
CREATE USER farmersblog_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE farmersblog TO farmersblog_user;
```

Update `.env` with your PostgreSQL connection string.

### 4. Run Migrations (Optional)

If using Flask-Migrate:

```bash
flask db init
flask db migrate
flask db upgrade
```

Otherwise, tables are created automatically on first run via `db.create_all()`.

### 5. Start the Application

For production, use Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

Or with a WSGI server like uWSGI.

### 6. Production Considerations

- Set up a reverse proxy (Nginx) with HTTPS
- Configure Redis for rate limiting and caching
- Enable Cloudinary for media uploads (no local uploads)
- Set strict security headers (auto-configured)
- Use environment variables for all secrets

## SEO Notes

- The app includes dynamic SEO meta tags, Open Graph, Twitter Cards, and JSON-LD structured data.
- Sitemap: `/sitemap.xml` (auto-generated)
- Robots: `/robots.txt`
- Private pages (`/login`, `/register`, `/admin`, `/settings`, etc.) are set to `noindex, nofollow`.
- For production, set your canonical domain in the Render environment (e.g., `https://farmersblog.com`) and ensure non-www redirects to www or vice versa via Render's static redirects or Flask middleware.

## API Endpoints

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| GET | `/` | Home feed (paginated, ?feed=following) | No |
| GET | `/post/<id>` | Post detail with comments | No |
| GET | `/login` | Login page | No |
| POST | `/login` | Login form submission | No |
| GET | `/register` | Register page | No |
| POST | `/register` | Register form submission | No |
| GET | `/logout` | Logout | Yes |
| GET | `/posts/create` | Create post page | Yes |
| POST | `/posts/create` | Create post submission (multi-media) | Yes |
| POST | `/posts/<id>/like` | Toggle like (AJAX, optimistic) | Yes |
| POST | `/posts/<id>/comment` | Add comment (AJAX, optimistic) | Yes |
| GET | `/user/<username>` | Public profile (shows location) | No |
| POST | `/user/<username>/follow` | Toggle follow (AJAX) | Yes |
| GET | `/search/posts` | Search posts by caption text | No |
| GET | `/search/users` | Search users by username/location | Optional |
| GET | `/user/settings/profile` | Edit profile (avatar, bio, location) | Yes |
| POST | `/user/settings/profile` | Update profile | Yes |
| GET | `/messages` | Inbox | Yes |
| GET | `/messages/<username>` | Conversation | Yes |
| POST | `/messages/send` | Send message (AJAX) | Yes |
| GET | `/messages/<username>/poll` | Poll new messages (AJAX) | Yes |
| GET | `/groups` | Group listing | Yes |
| GET | `/groups/create` | Create group page | Yes |
| POST | `/groups/create` | Create group | Yes |
| GET | `/groups/<name>` | Group detail | No |
| POST | `/groups/<name>/join` | Join/leave group (AJAX) | Yes |

## Database Models

- **User** — id, username, email, password_hash, avatar_filename, bio, location, created_at
- **Post** — id, author_id, caption, group_id, created_at
- **Media** — id, post_id, filename, media_type (image/video), position
- **Comment** — id, post_id, author_id, text, created_at
- **Message** — id, sender_id, recipient_id, body, timestamp, read
- **Group** — id, name, description, creator_id, created_at
- **Notification** — id, recipient_id, actor_id, type, message, link, read, created_at
- **Listing** — id, seller_id, title, description, price, category, location, image_filename, is_sold, created_at
- **post_likes** — user_id, post_id (association table)
- **followers** — follower_id, followed_id (association table)
- **group_members** — user_id, group_id, joined_at (association table)

## Testing Multi-Media Uploads

1. Log in with sample credentials
2. Click "Create Post" in the navbar
3. Select multiple files (images and/or videos) using the file picker
4. Add a caption and optionally select a group
5. Submit the post
6. View the post on the feed — the first media is shown as thumbnail
7. Click the post to see the carousel/gallery view

## Database Migrations

If you encounter foreign‑key errors like `"Key (user_id) is not present in table 'user'"`, the database schema has stale constraints referencing the old singular `user` table name. The model correctly uses `users` (plural).

### Quick fix in-place (PostgreSQL)

Connect to your database and run:

```sql
ALTER TABLE "group"      DROP CONSTRAINT group_creator_id_fkey;
ALTER TABLE "group"      ADD CONSTRAINT group_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES users(id);
ALTER TABLE comment      DROP CONSTRAINT comment_author_id_fkey;
ALTER TABLE comment      ADD CONSTRAINT comment_author_id_fkey FOREIGN KEY (author_id) REFERENCES users(id);
ALTER TABLE followers    DROP CONSTRAINT followers_follower_id_fkey;
ALTER TABLE followers    ADD CONSTRAINT followers_follower_id_fkey FOREIGN KEY (follower_id) REFERENCES users(id);
ALTER TABLE followers    DROP CONSTRAINT followers_followed_id_fkey;
ALTER TABLE followers    ADD CONSTRAINT followers_followed_id_fkey FOREIGN KEY (followed_id) REFERENCES users(id);
ALTER TABLE group_members DROP CONSTRAINT group_members_user_id_fkey;
ALTER TABLE group_members ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
ALTER TABLE listing      DROP CONSTRAINT listing_seller_id_fkey;
ALTER TABLE listing      ADD CONSTRAINT listing_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES users(id);
ALTER TABLE message      DROP CONSTRAINT message_recipient_id_fkey;
ALTER TABLE message      ADD CONSTRAINT message_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES users(id);
ALTER TABLE message      DROP CONSTRAINT message_sender_id_fkey;
ALTER TABLE message      ADD CONSTRAINT message_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES users(id);
ALTER TABLE notification DROP CONSTRAINT notification_actor_id_fkey;
ALTER TABLE notification ADD CONSTRAINT notification_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES users(id);
ALTER TABLE notification DROP CONSTRAINT notification_recipient_id_fkey;
ALTER TABLE notification ADD CONSTRAINT notification_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES users(id);
ALTER TABLE post         DROP CONSTRAINT post_author_id_fkey;
ALTER TABLE post         ADD CONSTRAINT post_author_id_fkey FOREIGN KEY (author_id) REFERENCES users(id);
ALTER TABLE post_likes   DROP CONSTRAINT post_likes_user_id_fkey;
ALTER TABLE post_likes   ADD CONSTRAINT post_likes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
```

### Drop and recreate from scratch (PostgreSQL)

```bash
sudo -u postgres psql -c "DROP DATABASE farmersblog_dev;"
sudo -u postgres psql -c "CREATE DATABASE farmersblog_dev;"
```

### SQLite

```bash
rm app/instance/farmersblog.db  # if using SQLite
```

After resetting the database, restart the app — tables will be created automatically via `db.create_all()`.

## License

MIT