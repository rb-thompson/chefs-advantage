from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, NumberRange
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from pathlib import Path
from fpdf import FPDF
from werkzeug.utils import secure_filename  # For filename sanitization
import os
from io import BytesIO
from datetime import datetime
import random
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded


# Load environment variables
load_dotenv()

# Application configuration classes
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32))  # Use random key if not set
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f"sqlite:///{Path.cwd() / 'recipes.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    # RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'redis://localhost:6379')
    # For Redis, you'll need to install redis:
    # pip install redis
    RATELIMIT_DEFAULTS = ["200 per day", "50 per hour"]
    RATELIMIT_STRATEGY = "fixed-window"

    # Security settings
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to cookies
    SESSION_COOKIE_SAMESITE = 'Lax'  # Protect against CSRF
    PERMANENT_SESSION_LIFETIME = 3600  # Sessions expire after 1 hour

    # Database performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,  # Number of connections to keep open
        'max_overflow': 20,  # Extra connections for bursts
        'pool_timeout': 30,  # How long to wait for a connection
        'pool_recycle': 1800,  # Recycle connections after 30 minutes
    }

    DEBUG = False
    ENV = 'production'

class DevelopmentConfig(Config):
    DEBUG = True
    ENV = 'development'

# Choose configuration based on environment
config_mode = os.getenv('FLASK_ENV', 'production')
config = DevelopmentConfig() if config_mode == 'development' else Config()

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config)

# Initialize rate limiter using config class
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=app.config['RATELIMIT_DEFAULTS'],
    storage_uri=app.config['RATELIMIT_STORAGE_URL'],
    strategy=app.config['RATELIMIT_STRATEGY']
)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# SQLAlchemy models
class Recipe(db.Model):
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    author = db.Column(db.String)
    date = db.Column(db.String)
    prep_time = db.Column(db.Integer)
    cook_time = db.Column(db.Integer)
    ingredients = db.Column(db.Text)
    instructions = db.Column(db.Text)
    variations = db.Column(db.Text)
    notes = db.Column(db.Text)
    images = db.relationship('RecipeImage', backref='recipe', lazy=True, cascade='all, delete-orphan')

class RecipeImage(db.Model):
    __tablename__ = 'recipe_images'
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    image_path = db.Column(db.String, nullable=False)

# Input validation and security
class RecipeForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author')
    prep_time = IntegerField('Prep Time (minutes)', 
                           validators=[DataRequired(), NumberRange(min=0)])
    cook_time = IntegerField('Cook Time (minutes)', 
                           validators=[DataRequired(), NumberRange(min=0)])
    ingredients = TextAreaField('Ingredients', validators=[DataRequired()])
    instructions = TextAreaField('Instructions', validators=[DataRequired()])
    variations = TextAreaField('Variations')
    notes = TextAreaField('Notes')

# Update init_db() to use SQLAlchemy
def init_db():
    with app.app_context():
        db.create_all()

# Check if a filename has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Format dates
@app.template_filter('format_date')
def format_date(value, format='%Y-%m-%d %H:%M:%S'):
    if value:
        dt = datetime.strptime(value, '%Y-%m-%d')  # Adjust this format string according to how your date is stored
        return dt.strftime(format)
    return value

# Generate a unique hash for image uploads
def generate_image_hash():
    digits = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    unique_hash = 'IMG_' + ''.join([str(random.choice(digits)) for _ in range(10)])
    return unique_hash

# CSRF protection
csrf = CSRFProtect(app)

# Set up logging
def setup_logging(app):
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    # Set up file handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'recipe_app.log'),
        maxBytes=10240,  # 10KB per file
        backupCount=10   # Keep 10 backup files
    )
    
    # Set log format
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    file_handler.setFormatter(formatter)

    # Set log level based on environment
    if app.config['DEBUG']:
        file_handler.setLevel(logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.INFO)
        app.logger.setLevel(logging.INFO)

    # Add handler to app logger
    app.logger.addHandler(file_handler)

    # Log startup message
    app.logger.info('Recipe app startup')

# Call setup_logging after app initialization
setup_logging(app)

# Home page - Display all recipes
@app.route('/')
def index():
    # Get total recipes
    total_recipes = Recipe.query.count()
    
    # Get recent recipes
    recently_added = Recipe.query.order_by(Recipe.date.desc()).limit(8).all()
    
    # Get all recipes
    recipes = Recipe.query.all()
    
    results = f"Showing all {len(recipes)} recipes in the database:"
    
    if not recipes:
        message = "You don't have any recipes yet. Why not add your first one?"
        return render_template('index.html', 
                            recipes=recipes, 
                            message=message, 
                            total_recipes=total_recipes, 
                            recently_added=recently_added)
    
    return render_template('index.html', 
                         recipes=recipes, 
                         total_recipes=total_recipes, 
                         recently_added=recently_added, 
                         results=results)

# Add a new recipe
@app.route('/add', methods=['GET', 'POST'])
@limiter.limit("10 per minute")  # Limit recipe creation
def add_recipe():
    form = RecipeForm()
    if request.method == 'POST' and form.validate_on_submit():
        app.logger.info(f"Adding new recipe: {form.title.data}")
        try:
            new_recipe = Recipe(
                title=form.title.data,
                author=form.author.data,
                date=datetime.now().strftime('%Y-%m-%d'),
                prep_time=form.prep_time.data,
                cook_time=form.cook_time.data,
                ingredients=form.ingredients.data,
                instructions=form.instructions.data,
                variations=form.variations.data,
                notes=form.notes.data
            )
            db.session.add(new_recipe)
            db.session.flush()

            # Handle image uploads
            image_count = 0
            if 'images' in request.files:
                files = request.files.getlist('images')
                for file in files:
                    if file and allowed_file(file.filename):
                        hash_value = generate_image_hash()
                        extension = file.filename.rsplit('.', 1)[1].lower()
                        new_filename = f"{hash_value}.{extension}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename).replace('\\', '/')
                        
                        file.save(filepath)
                        new_image = RecipeImage(
                            recipe_id=new_recipe.id,
                            image_path=filepath
                        )
                        db.session.add(new_image)
                        image_count += 1
            
            db.session.commit()
            app.logger.info(f"Successfully added recipe {new_recipe.id} with {image_count} images")
            flash('Recipe added successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding recipe: {str(e)}")
            flash('Error adding recipe. Please try again.', 'error')
            return render_template('add_recipe.html', form=form)
    return render_template('add_recipe.html', form=form)

# View a single recipe
@app.route('/recipe/<int:recipe_id>')
def view_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    images = RecipeImage.query.filter_by(recipe_id=recipe_id).all()
    
    ingredients_list = recipe.ingredients.split(',') if recipe.ingredients else []
    return render_template('view_recipe.html', 
                         recipe=recipe, 
                         ingredients_list=ingredients_list, 
                         images=images)

# Update a recipe
@app.route('/update/<int:recipe_id>', methods=['GET', 'POST'])
@limiter.limit("20 per minute")  # Limit recipe updates
def update_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    form = RecipeForm()
    images = RecipeImage.query.filter_by(recipe_id=recipe_id).all()

    if request.method == 'POST' and form.validate_on_submit():
        app.logger.info(f"Updating recipe {recipe_id}")
        try:
            recipe.title = form.title.data
            recipe.author = form.author.data
            recipe.prep_time = form.prep_time.data
            recipe.cook_time = form.cook_time.data
            recipe.ingredients = form.ingredients.data
            recipe.instructions = form.instructions.data
            recipe.variations = form.variations.data
            recipe.notes = form.notes.data

            image_count = 0
            if 'images' in request.files:
                files = request.files.getlist('images')
                for file in files:
                    if file and allowed_file(file.filename):
                        hash_value = generate_image_hash()
                        extension = file.filename.rsplit('.', 1)[1].lower()
                        new_filename = f"{hash_value}.{extension}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename).replace('\\', '/')
                        
                        file.save(filepath)
                        new_image = RecipeImage(
                            recipe_id=recipe_id,
                            image_path=filepath
                        )
                        db.session.add(new_image)
                        image_count += 1

            db.session.commit()
            app.logger.info(f"Successfully updated recipe {recipe_id} with {image_count} new images")
            flash('Recipe updated successfully!', 'success')
            return redirect(url_for('view_recipe', recipe_id=recipe_id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating recipe {recipe_id}: {str(e)}")
            flash('Error updating recipe. Please try again.', 'error')
    
    # Populate form with existing data for GET request
    form.title.data = recipe.title
    form.author.data = recipe.author
    form.prep_time.data = recipe.prep_time
    form.cook_time.data = recipe.cook_time
    form.ingredients.data = recipe.ingredients
    form.instructions.data = recipe.instructions
    form.variations.data = recipe.variations
    form.notes.data = recipe.notes
    
    return render_template('update_recipe.html', form=form, recipe=recipe, images=images)

# Delete a recipe
@app.route('/delete_recipe/<int:recipe_id>', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Stricter limit for deletions
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    app.logger.info(f"Attempting to delete recipe {recipe_id}")
    try:
        for image in recipe.images:
            if os.path.exists(image.image_path):
                os.remove(image.image_path)
        db.session.delete(recipe)
        db.session.commit()
        app.logger.info(f"Successfully deleted recipe {recipe_id}")
        flash('Recipe and associated images deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting recipe {recipe_id}: {str(e)}")
        flash('Error deleting recipe. Please try again.', 'error')
    return redirect(url_for('index'))

# Delete an image
@app.route('/delete_image/<int:image_id>')
@limiter.limit("5 per minute")  # Stricter limit for image deletions
def delete_image(image_id):
    image = RecipeImage.query.get_or_404(image_id)
    
    if os.path.exists(image.image_path):
        os.remove(image.image_path)
    
    db.session.delete(image)
    db.session.commit()
    flash('Bleep blop! Image deleted successfully.', 'success')
    return redirect(request.referrer)

# Search for recipes
@app.route('/search', methods=['GET'])
@limiter.limit("25 per minute")  # Pace search requests
def search():
    # Get total recipe count
    total_recipes = Recipe.query.count()
    
    # Base query
    query = Recipe.query
    
    # Keyword Search
    keyword = request.args.get('keyword')
    ingredient = request.args.get('ingredient')
    
    if keyword:
        query = query.filter(
            db.or_(
                Recipe.title.ilike(f'%{keyword}%'),
                Recipe.ingredients.ilike(f'%{keyword}%')
            )
        )
    elif ingredient:
        query = query.filter(Recipe.ingredients.ilike(f'%{ingredient}%'))
    
    recipes = query.order_by(Recipe.date.desc()).all()
    
    # Get recent recipes
    recently_added = Recipe.query.order_by(Recipe.date.desc()).limit(10).all()

    if not recipes:
        flash('Recipe not there? Add one!', 'info')
        results = "No recipes found matching your criteria."
    else:
        if keyword and ingredient:
            flash(f'{len(recipes)} recipes found!', 'success')
            results = f"Found {len(recipes)} recipes matching your filters '{keyword}' and '{ingredient}':"
        elif keyword:
            flash(f'{len(recipes)} recipes found!', 'success')
            results = f"Found {len(recipes)} recipes matching your keyword '{keyword}':"
        elif ingredient:
            flash(f'{len(recipes)} recipes found!', 'success')
            results = f"Found {len(recipes)} recipes containing '{ingredient}':"
        else:
            flash(f'{len(recipes)} recipes found! Get cooking!', 'info')
            results = f"Showing all {len(recipes)} recipes in the database:"

    return render_template('index.html', 
                         recipes=recipes, 
                         recently_added=recently_added,
                         keyword=keyword, 
                         ingredient=ingredient, 
                         total_recipes=total_recipes,
                         results=results)

# Generate PDF
@app.route('/generate_pdf/<int:recipe_id>')
@limiter.limit("5 per minute")  # Limit PDF generation (resource-intensive)
def generate_pdf(recipe_id):
    try:
        recipe = Recipe.query.get_or_404(recipe_id)

        # Create PDF instance
        pdf = FPDF()
        pdf.add_page()
        pdf.set_margins(left=20, top=20, right=20)
        
        # Title styling
        pdf.set_font("Helvetica", 'B', 14)
        pdf.set_text_color(255, 71, 32)
        pdf.cell(0, 10, txt=recipe.title, ln=True, align='C')
        pdf.ln(5)

        # Metadata styling
        pdf.set_font("Helvetica", 'I', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 10, txt=f"Author: {recipe.author}")
        pdf.multi_cell(0, 10, txt=f"Date: {recipe.date}")
        pdf.multi_cell(0, 10, txt=f"Prep Time: {recipe.prep_time} minutes")
        pdf.multi_cell(0, 10, txt=f"Cook Time: {recipe.cook_time} minutes")
        pdf.ln(5)

        # Ingredients styling
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.multi_cell(0, 10, txt="Ingredients:", fill=True)
        pdf.set_font("Helvetica", '', 10)
        pdf.multi_cell(0, 6, txt=recipe.ingredients)
        pdf.ln(5)

        # Instructions styling
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 10, txt="Instructions:", fill=True)
        pdf.set_font("Helvetica", '', 10)
        pdf.multi_cell(0, 6, txt=recipe.instructions)
        pdf.ln(5)

        # Variations styling
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 10, txt="Variations:", fill=True)
        pdf.set_font("Helvetica", '', 10)
        pdf.multi_cell(0, 6, txt=recipe.variations)
        pdf.ln(5)

        # Notes styling
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 10, txt="Notes:", fill=True)
        pdf.set_font("Helvetica", '', 10)
        pdf.multi_cell(0, 6, txt=recipe.notes)

        # Generate PDF in memory
        try:
            pdf_output = pdf.output(dest='S')
        except UnicodeEncodeError:
            pdf_output = pdf.output(dest='S').encode('latin1', errors='replace').decode('latin1')
        pdf_buffer = BytesIO(pdf_output.encode('latin1'))

        # Sanitize filename to prevent invalid characters
        safe_title = secure_filename(recipe.title)
        download_name = f"{safe_title}_{recipe.date}.pdf"

        # Send PDF to browser for download or preview
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/pdf'
        )
    
    except Exception as e:
        app.logger.error(f"Error generating PDF for recipe {recipe_id}: {str(e)}")
        flash('Application cooked. Something went wrong.', 'error')
        return f"Error generating PDF: {str(e)}", 500
    
# Photo gallery
@app.route('/photo_gallery')
def photo_gallery():
    keyword = request.args.get('keyword')
    images = []

    if keyword:
        # Search recipes by keyword in title or ingredients
        recipes = Recipe.query.filter(
            db.or_(
                Recipe.title.ilike(f'%{keyword}%'),
                Recipe.ingredients.ilike(f'%{keyword}%')
            )
        ).all()

        if recipes:
            # Get all images for matching recipes
            recipe_ids = [recipe.id for recipe in recipes]
            images = RecipeImage.query.filter(
                RecipeImage.recipe_id.in_(recipe_ids)
            ).join(Recipe).add_columns(
                RecipeImage.image_path,
                Recipe.id.label('recipe_id'),
                Recipe.title,
                Recipe.ingredients
            ).all()
        
        results = f"Showing {len(images)} images matching '{keyword}'."
        if not images:
            flash('Make your memories count. Upload photos!', 'info')
            results = "No photos found for this keyword. Why not add your first one?"
    else:
        # Get all images with recipe information
        images = RecipeImage.query.join(Recipe).add_columns(
            RecipeImage.image_path,
            Recipe.id.label('recipe_id'),
            Recipe.title,
            Recipe.ingredients
        ).all()
        results = f"Showing all {len(images)} images."

    return render_template(
        'gallery.html',
        images=images,
        results=results
    )

@app.errorhandler(RateLimitExceeded)
def handle_rate_limit_exceeded(e):
    app.logger.warning(f"Rate limit exceeded for {request.remote_addr}: {str(e)}")
    flash('Too many requests. Please try again later.', 'error')
    return render_template('error/429.html'), 429

if __name__ == '__main__':
    init_db()
    app.run(debug=True)