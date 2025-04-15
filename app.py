# Import required libraries
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from datetime import datetime, date
from flask_bootstrap5 import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import smtplib
import os
from dotenv import load_dotenv
from flask_ckeditor import CKEditor
# from flask_gravatar import Gravatar
# from gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, RegisterForm, LogInForm, CommentForm, ForgotPasswordForm, ResetPasswordForm
from supabase import create_client, Client
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask_migrate import Migrate
from urllib.parse import urlparse, urljoin, urlencode
from hashlib import md5
import requests
from middleware import SEOMiddleware
from flask import send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

# Load environment variables
load_dotenv()

# Supabase setup - Replace these with your Supabase project details
supabase_url = os.getenv('SUPABASE_URL')  # Your Supabase URL
supabase_key = os.getenv('SUPABASE_KEY')  # Your Supabase Key
supabase: Client = create_client(supabase_url, supabase_key)

# Email and password configuration for sending emails (Gmail SMTP as an example)
google_email = os.getenv('MY_WEBSITE_EMAIL') # Set your email in .env
google_password = os.getenv('MY_WEBSITE_PASSWORD') # Set your email password in .env

# Gravatar URL generator function for user profile images
def gravatar_url(email, size=100, rating='g', default='retro', force_default=False):
    # Convert email to lowercase and hash with MD5 (Gravatar requirement)
    email_hash = md5(email.strip().lower().encode('utf-8')).hexdigest()

    # Build query parameters
    query_params = {'d': default, 's': str(size), 'r': rating}
    if force_default:
        query_params['f'] = 'y'  # Gravatar expects 'f=y' if force_default is True

    return f"https://www.gravatar.com/avatar/{email_hash}?{urlencode(query_params)}"

# Initialize Flask application
app = Flask(__name__)

# Trust Render’s proxy (1 proxy layer, if applicable)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Add the filter for Jinja templates
app.jinja_env.filters['gravatar'] = gravatar_url

# Email setup for Flask-Mail (ensure your credentials are in .env file)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # e.g., smtp.gmail.com for Gmail
app.config['MAIL_PORT'] = 587  # Use 465 for SSL, 587 for TLS
app.config['MAIL_USE_TLS'] = True  # or False if using SSL
app.config['MAIL_USE_SSL'] = False  # or True if using SSL
app.config['MAIL_USERNAME'] = os.getenv('MY_WEBSITE_EMAIL')
app.config['MAIL_PASSWORD'] = os.getenv('MY_WEBSITE_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MY_WEBSITE_EMAIL')

# SQLite database config (replace with your database URL in .env)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') # Secret key for sessions
app.config['CKEDITOR_PKG_TYPE'] = 'full'

# Initialize Flask extensions
ckeditor = CKEditor(app)
login_manager = LoginManager()
mail = Mail(app)
app.config['MAIL_SECRET_KEY'] = os.getenv('MAIL_SECRET_KEY')
s = URLSafeTimedSerializer(app.config['MAIL_SECRET_KEY'])

# Captcha for site security, can use recaptcha as well
HCAPTCHA_SECRET_KEY = os.getenv('HCAPTCHA_SECRET_KEY')

# Register SEO Middleware
SEOMiddleware(app)

# Initialize the database
class Base(DeclarativeBase):
    pass

# Set Up database
db = SQLAlchemy(model_class=Base)
db.init_app(app)
login_manager.init_app(app)
bootstrap = Bootstrap(app)
migrate = Migrate(app, db)

# Current year for dynamic copyright in templates
year = datetime.today().year

# Database tables: Define your models here with placeholder descriptions

# Post table (Example: A blog post with title, body, etc.)
class Post(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title: Mapped[int] = mapped_column(String, unique=True, nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="published")  # "draft" or "published"
    scheduled_datetime: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    comments = relationship("Comment", back_populates="parent_post")
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)

# User table (Handles user registration, login, and profile)
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    posts = relationship("Post", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

# Comment table (Handles comments on blog posts)
class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("Post", back_populates="comments")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("comments.id"), nullable=True)
    parent_comment = relationship("Comment", remote_side=[id], backref="replies")

# Password reset token table
# noinspection PyDeprecation
class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    is_used: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)

# Initialize database schema
with app.app_context():
    db.create_all()


# Static Routes
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/img', 'favicon.png', mimetype='image/vnd.microsoft.icon')


# Have this route if you want to use Google search console with your site
@app.route('/sitemap.xml')
def generate_sitemap():
    pages = ['/', '/about', '/contact', '/blog', '/new-page']  # Add more pages dynamically
    base_url = "https://alhadarwebsite.onrender.com/"

    xml_sitemap = """<?xml version="1.0" encoding="UTF-8"?>\n"""
    xml_sitemap += """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n"""

    for page in pages:
        xml_sitemap += f"""<url>
            <loc>{base_url}{page}</loc>
            <lastmod>{datetime.today().strftime('%Y-%m-%d')}</lastmod>
            <changefreq>weekly</changefreq>
            <priority>0.7</priority>
        </url>\n"""

    xml_sitemap += """</urlset>"""

    response = Response(xml_sitemap, mimetype="application/xml")

    # Print out the response headers for debugging
    print(response.headers)

    return response


# this is for Google Adsense if you want to connect adsense with your site
@app.route('/ads.txt')
def ads_txt():
    return send_from_directory('static', 'ads.txt', mimetype='text/plain')


# URL Normalization (ensure lowercase paths)
@app.before_request
def normalize_url():
    # Only normalize category-based URLs (if necessary)
    if "category" in request.view_args:
        category = request.view_args["category"]
        # Normalize only the category part to lowercase
        request.view_args["category"] = category.lower()

    # Redirect if the entire URL path is not in lowercase (except for static files)
    if request.path != request.path.lower() and not request.path.startswith('/static/'):
        return redirect(request.path.lower(), code=301)


# Admin-only wrapper for routes
def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        elif current_user.id != 1:
            return redirect(url_for('home'))
        return func(*args, **kwargs)  # Make sure to pass args and kwargs to the wrapped function
    return wrapper


# Route for user registration
# noinspection PyArgumentList
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        name = form.name.data

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        new_user = User(email=email, password=hashed_password, name=name)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template("register.html", form=form, copyright_year=year)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


def is_safe_url(target):
    """Validate that the redirect URL is safe and within the same site."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def retry_post(post_data):
    """Re-run the saved POST request after login."""
    post_url = post_data.get("url")
    post_payload = post_data.get("data")

    if post_url:
        # Simulate the original POST request
        with app.test_request_context(post_url, method="POST", data=post_payload):
            # Call the appropriate route function
            response = app.dispatch_request()
            return response
    return redirect(url_for('home'))


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LogInForm()

    # Use session.get() to avoid KeyError
    previous_url = session.get('url')
    print(f"Previous session URL: {previous_url}")

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password.")
            return redirect(url_for("login"))

        login_user(user)

        # Redirect user back to the page they tried to access before login
        if previous_url:
            session.pop('url')  # Remove 'url' after using it
            return redirect(previous_url)

        return redirect(url_for("home"))

    return render_template("login.html", form=form)


@app.route("/<string:category>/post/<int:post_id>/like", methods=["POST"])
def like_post(category, post_id):
    print(f"Like post requested: Category = {category}, Post ID = {post_id}")

    if not current_user.is_authenticated:
        # If not authenticated, redirect to login page and preserve the current URL
        return redirect(url_for('login'))

    # Fetch the post
    category = category.replace("-", " ")  # Convert hyphenated category back to spaces
    post = Post.query.filter_by(id=post_id, category=category).first()

    if not post:
        print("Post not found. Redirecting to home page.")
        # If post is not found, redirect to the home page
        flash('Post not found.', 'danger')
        return redirect(url_for('home'))

    # Increment likes
    post.likes += 1
    db.session.commit()

    print(f"Post found. Likes incremented. Current likes: {post.likes}")

    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        print("AJAX request detected. Returning like count in response.")
        return jsonify({'likes': post.likes})

    # Non-AJAX requests should redirect back to the post
    print(f"Redirecting back to post page: Category = {category}, Post ID = {post_id}")
    return redirect(url_for('show_post', category=category.replace(" ", "-"), post_id=post_id))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


def send_post_notification(post):
    """Send email notification about new blog post to all registered users."""
    try:
        # Get all registered users' emails
        users = User.query.all()
        for user in users:
            if not user.email:
                continue

            # Create the email
            subject = f"New Blog Post: {post.title}"

            def truncate_text(text, word_limit=300):
                words = text.split()
                return " ".join(words[:word_limit]) + "..." if len(words) > word_limit else text

            preview_text = truncate_text(post.body)

            # Create HTML email content
            html_content = f'''
            <html>
                <body>
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2>{post.title}</h2>
                        <p>{preview_text}</p>
                        <div style="margin: 20px 0;">
                            <p>Category: {post.category}</p>
                        </div>
                        <a href="{url_for('show_post', category=post.category, post_id=post.id, _external=True)}" 
                           style="background-color: #007bff; color: white; padding: 10px 20px; 
                                  text-decoration: none; border-radius: 5px;">
                            Read More
                        </a>
                        <hr style="margin-top: 30px;">
                        <p style="font-size: 12px; color: #666;">
                            You received this email because you're registered on our blog. 
                            If you'd like to unsubscribe, please update your preferences in your account settings.
                        </p>
                    </div>
                </body>
            </html>
            '''

            msg = Message(
                subject=subject,
                recipients=[user.email],
                html=html_content
            )

            mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False


# noinspection PyTypeChecker
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()

    if form.validate_on_submit():
        new_post = Post(
            title=form.title.data,
            category=form.category.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y"),
        )

        if form.publish.data:
            new_post.status = "published"
            new_post.scheduled_datetime = None
        elif form.draft.data:
            new_post.status = "draft"
            new_post.scheduled_datetime = None
        elif form.schedule.data:
            new_post.status = "scheduled"
            # Combine the date and time fields
            if form.publish_date.data and form.publish_time.data:
                scheduled_datetime = datetime.combine(
                    form.publish_date.data,
                    form.publish_time.data
                )
                new_post.scheduled_datetime = scheduled_datetime

        db.session.add(new_post)
        db.session.commit()

        if new_post.status == "published":
            if send_post_notification(new_post):
                flash("New post created and notification sent to subscribers!", "success")
            else:
                flash("Post created, but there was an issue sending notifications.", "warning")
        else:
            flash("Post saved successfully!", "success")

        return redirect(url_for("home"))

    return render_template("make-post.html", form=form, copyright_year=year, post=None)


# noinspection PyTypeChecker,PyUnresolvedReferences
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only # Ensure only admin can access
def edit_post(post_id):
    """
    Edit an existing post: Allows changing post title, category, body, and setting status (published, draft, scheduled)
    """
    post = db.get_or_404(Post, post_id) # Retrieve post or 404 error if not found
    edit_form = CreatePostForm(obj=post) # Initialize form with existing post data

    # If it's a GET request and the post is scheduled, populate the date/time fields
    if request.method == "GET" and post.scheduled_datetime:
        edit_form.publish_date.data = post.scheduled_datetime.date()
        edit_form.publish_time.data = post.scheduled_datetime.time()

    if edit_form.validate_on_submit(): # Handle POST request
        # Backup original status before changes
        original_status = post.status

        # Update post attributes
        post.title = edit_form.title.data
        post.category = edit_form.category.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data

        print("\nButton states:")
        print(f"Publish: {edit_form.publish.data}")
        print(f"Draft: {edit_form.draft.data}")
        print(f"Schedule: {edit_form.schedule.data}")
        print(f"Current post status: {post.status}")

        # Handle post status (publish, draft, schedule)
        if edit_form.publish.data:
            print("Setting status to published")
            post.status = "published"
            post.scheduled_datetime = None
        elif edit_form.draft.data:
            print("Setting status to draft")
            post.status = "draft"
            post.scheduled_datetime = None
        elif edit_form.schedule.data:
            print("Setting status to scheduled")
            post.status = "scheduled"

            # Combine the date and time fields
            if edit_form.publish_date.data and edit_form.publish_time.data:
                scheduled_datetime = datetime.combine(
                    edit_form.publish_date.data,
                    edit_form.publish_time.data
                )
                post.scheduled_datetime = scheduled_datetime
            else:
                flash('Publish date and time are required when scheduling a post.', 'danger')
                return render_template(
                    "make-post.html",
                    form=edit_form,
                    is_edit=True,
                    post=post,
                    copyright_year=year
                )

        print(f"Post status before commit: {post.status}")

        try:
            db.session.commit() # Commit changes to database
            # Check if the post's status was changed to 'published' and the previous status was draft or scheduled
            if original_status != "published" and post.status == "published":
                # Send email notification to users about the new post
                if send_post_notification(post):
                    flash("New post published and notification sent to subscribers!", "success")
                else:
                    flash("Post published, but there was an issue sending notifications.", "warning")
            else:
                flash("Post updated successfully!", "success")
            print(f"Post status after commit: {post.status}")
            flash("Post updated successfully!", "success")
            # Check if there’s a saved action to replay
            return redirect(url_for("show_post", post_id=post.id, category=post.category.replace(" ", "-")))
        except Exception as e:
            db.session.rollback() # Rollback in case of error
            flash(f"Error updating post: {str(e)}", "danger")
            return render_template(
                "make-post.html",
                form=edit_form,
                is_edit=True,
                post=post,
                copyright_year=year
            )

    return render_template(
        "make-post.html",
        form=edit_form,
        is_edit=True,
        post=post,
        copyright_year=year
    )


@app.route("/delete/<int:post_id>")
@admin_only # Ensure only admin can delete posts
def delete_post(post_id):
    """
    Delete an existing post by its ID
    """
    post_to_delete = db.get_or_404(Post, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


# Helper Functions
def send_reset_email(email, reset_url):
    """
    Send password reset email with a link
    """
    msg = Message("Password Reset Request",
                  sender=os.getenv('MY_WEBSITE_EMAIL'),
                  recipients=[email])

    # Email body content
    msg.body = f"""To reset your password, click the following link: {reset_url}
    If you did not request this, ignore this email."""

    # Set the Reply-To header to a non-monitored address
    msg.reply_to = "no-reply@example.com"  # Use a non-monitored address

    # Send the email
    mail.send(msg)


# Password Reset Routes
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """
    Handle password reset request: Sends a reset email with a token
    """
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user:
            token = s.dumps(email, salt='email-reset') # Generate a token for the reset link

            # save or update the password reset token in the database
            reset_token = PasswordResetToken.query.filter_by(email=email).first()
            if reset_token:
                reset_token.token = token # Update token if exists
            else:
                reset_token = PasswordResetToken(email=email, token=token)
                db.session.add(reset_token)
            db.session.commit()

            reset_url = url_for('reset_password', token=token, _external=True)
            send_reset_email(email, reset_url)
            flash("A password reset link has been sent to your email.", "info")
            return redirect(url_for('login'))
        else:
            flash("Email not found. Please register.", "warning")
            return redirect(url_for('register'))
    return render_template("forgot_password.html", form=form, copyright_year=year)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """
    Reset the password using the token received via email
    """
    try:
        email = s.loads(token, salt="email-reset", max_age=3600)  # Token expires in 1 hour
    except SignatureExpired:
        flash("The reset link is expired! Request for another one.", "warning")
        return redirect(url_for("forgot_password"))

    # Verify token exists and is valid
    reset_token = PasswordResetToken.query.filter_by(email=email, token=token).first()
    if not reset_token:
        flash("Invalid or already used reset link.", "warning")
        return redirect(url_for("forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        new_password = form.new_password.data
        confirm_password = form.confirm_password.data
        if new_password == confirm_password:
            user = User.query.filter_by(email=email).first()
            user.password = generate_password_hash(new_password)  # Hash the new password
            db.session.commit()

            # check if token is used
            reset_token.is_used = True  # Mark token as used
            db.session.commit()

            flash("Password reset successful. Please log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("Passwords do not match.", "danger")

    return render_template("reset_password.html", form=form, token=token, copyright_year=year)


@app.route("/")
def home():
    return render_template("index.html", copyright_year=year)


@app.route("/about")
def about():
    return render_template("about.html", copyright_year=year)


@app.route("/blog", defaults={'category': None})
@app.route("/blog/<category>")
def blogs(category):
    if category:
        # Filter posts by category and ensure they are published
        posts = Post.query.filter_by(category=category.replace('-', ' '), status='published').all()
    else:
        # Get all published posts
        posts = Post.query.filter_by(status='published').all()
    return render_template("blog.html", posts=posts, copyright_year=year)


@app.route("/<category>")
def show_category(category):
    category = category.replace('-', ' ')
    posts = Post.query.filter_by(category=category, status='published').all()
    return render_template("category.html", posts=posts, category=category, copyright_year=year)


@app.route("/projects")
def projects(): # If you have a route for this
    posts = Post.query.filter_by(category='Projects', status='published').all()
    return render_template("projects.html", posts=posts, copyright_year=year)


@app.route("/cvresume") # If you have a route for this
def cvresume():
    return render_template("cvresume.html", copyright_year=year)


@app.route("/ug-escapades")
def ugescapades():
    posts = Post.query.filter_by(category='UG Escapades', status='published').all()
    return render_template("ugescapades.html", posts=posts, copyright_year=year)


@app.route("/random-musings")
def random_musings():
    posts = Post.query.filter_by(category='Random Musings', status='published').all()
    return render_template("randommusings.html", posts=posts, copyright_year=year)

@app.route("/türkiye-geçilmez")
def turkiyegecilmez():
    posts = Post.query.filter_by(category='Türkiye Geçilmez', status='published').all()
    return render_template("turkiyegecilmez.html", posts=posts, copyright_year=year)


# Contact Form Route
@app.route("/contact", methods=["GET", "POST"])
def contact():
    """
    Contact form for users to send messages to website owner
    """
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        #Honeypot field check: If the honeypot is filled out, treat it as spam
        honeypot = request.form.get('honeypot')
        if honeypot:  # If honeypot is filled out, it's a bot
            return "Spam detected, ignoring form submission."

        #Get HCAPTCHA response from form
        captcha_response = request.form.get('h-captcha-response')

        #Verify HCAPTCHA response
        payload = {

            'secret': HCAPTCHA_SECRET_KEY,

            'response': captcha_response

        }

        verify_url = "https://hcaptcha.com/siteverify" # Put in Google reCaptcha link if you are using reCaptcha
        response = requests.post(verify_url, data=payload)
        result = response.json()

        # If HCAPTCHA verification is successful
        if result.get('success'):
            # Send email

            my_email = google_email
            password = google_password

            with smtplib.SMTP("smtp.gmail.com", 587) as connection:
                connection.starttls()
                connection.login(user=my_email, password=password)
                connection.sendmail(from_addr=my_email, to_addrs=my_email,
                                    msg=f"Subject: New Message From Your Website!\n\nName: {name}\nEmail: {email}\nMessage: {message}")

            flash('Message sent successfully!', 'success')
        #if recaptcha is not successful
        else:
            flash('HCAPTCHA verification failed. Please try again.', 'danger')
            return redirect(url_for('contact'))

    return render_template("index.html", message_sent=False, copyright_year=year)


@app.route("/audacious-men-series")
def audacity():
    posts = Post.query.filter_by(category='Audacious Men Series', status='published').all()
    return render_template("audacity.html", posts=posts, copyright_year=year)


@app.route("/my-portfolio")
def portfolio():
    posts = Post.query.filter_by(category='My Portfolio', status='published').all()
    return render_template("portfolio.html", posts=posts, copyright_year=year)


@app.route("/<string:category>/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id, category=None):
    # Fetch the post, optionally validating the category
    if category:
        category = category.replace("-", " ")  # Replace hyphen with space
        print(f"[DEBUG] Searching for post with ID {post_id} in category '{category}'.")

        # Use filter() with ilike() for case-insensitive comparison
        requested_post = Post.query.filter(
            Post.id == post_id,
            Post.category.ilike(category)  # ilike() performs case-insensitive search
        ).first()

        if not requested_post:
            print(f"[DEBUG] Post not found in category '{category}' with ID {post_id}. Redirecting to home.")
            flash(f"Post with ID {post_id} not found in category {category}.", "warning")
            return redirect(url_for("home"))
    else:
        requested_post = db.get_or_404(Post, post_id)


    # Debug print to confirm image URL
    print(f"[DEBUG] Image URL before transformation: {requested_post.img_url}")

    requested_post.views += 1
    db.session.commit()

    # Only update session URL if it's not already the current post URL
    if session.get('url') != request.url:
        session['url'] = request.url

    comment_form = CommentForm()

    if comment_form.validate_on_submit():
        if current_user.is_authenticated:

            parent_id = request.form.get("parent_id")

            new_comment = Comment(
                text=comment_form.comment.data,
                author_id=current_user.id,
                post_id=requested_post.id,
                parent_id=parent_id
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=post_id, category=category))
        else:
            error = "Login Required! Please log in/Register to leave a comment"
            flash(f"{error}. Log in to leave a comment!")
            return redirect(url_for("login", session=f"{session['url']}"))
    # Fetch all posts in the same category, excluding the current post
    top_level_comments = Comment.query.filter_by(post_id=post_id, parent_id=None).all()
    all_posts = Post.query.filter(Post.category == requested_post.category, Post.id != requested_post.id).all()
    categories = [cat[0] for cat in db.session.query(Post.category).distinct().all()]

    return render_template(
        "post.html",
        post=requested_post,
        comments=top_level_comments,  # Pass only top-level comments
        current_user=current_user,
        form=comment_form,
        all_posts=all_posts,
        categories=categories,
        copyright_year=year,
        category=category
    )


@app.route('/search')
def search():
    query = request.args.get('q')
    if query:
        results = Post.query.filter(
            (Post.title.ilike(f'%{query}%')) | (Post.body.ilike(f'%{query}%'))
        ).all()
    else:
        results = []

    # Query all unique categories
    categories = [cat[0] for cat in db.session.query(Post.category).distinct().all()]

    return render_template('search.html', query=query, results=results, copyright_year=year, categories=categories)


@app.route("/drafts", methods=["GET", "POST"])
@admin_only  # Ensure only admin can access
def drafts():
    draft_posts = Post.query.filter_by(status="draft").all()

    return render_template("drafts.html", drafts=draft_posts, copyright_year=year)


@app.route("/scheduled-posts", methods=["GET"])
@admin_only
def scheduled_posts():
    post_scheduled = Post.query.filter_by(status="scheduled").all()  # Get all scheduled posts
    return render_template("scheduled.html", post_scheduled=post_scheduled, copyright_year=year)


@app.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html", copyright_year=year)


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html", copyright_year=year)


@app.route("/terms-and-conditions")
def terms_and_conditions():
    return render_template("terms_conditions.html", copyright_year=year)


if __name__ == "__main__":
    app.run(debug=True, port=5005)
