from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import sqlite3
import os
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = 'its_all_in_sauce'  # Required for flash messages

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database file path
DATABASE = 'recipes.db'

# Initialize the database and ensure tables exist
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Check if the recipes table exists
    c.execute('''
        SELECT count(name) FROM sqlite_master
        WHERE type='table' AND name='recipes'
    ''')
    if not c.fetchone()[0]:
        c.execute('''
            CREATE TABLE recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT,
                date TEXT,
                prep_time INTEGER,
                cook_time INTEGER,
                ingredients TEXT,
                instructions TEXT,
                variations TEXT,
                notes TEXT
            )
        ''')
    
    # Check if the recipe_images table exists
    c.execute('''
        SELECT count(name) FROM sqlite_master
        WHERE type='table' AND name='recipe_images'
    ''')
    if not c.fetchone()[0]:
        c.execute('''
            CREATE TABLE recipe_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE
            )
        ''')
    
    conn.commit()
    conn.close()

# Helper function to get a database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Check if a filename has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

# Home page - Display all recipes
@app.route('/')
def index():
    conn = get_db_connection()
    c = conn.cursor()

    # Get total recipes
    c.execute('SELECT COUNT(*) FROM recipes')
    total_recipes = c.fetchone()[0]

    # Get recent recipes, assuming you want the 10 most recent
    c.execute('SELECT id, title, date FROM recipes ORDER BY date DESC LIMIT 8')
    recently_added = c.fetchall()

    # Get all recipes
    c.execute('SELECT * FROM recipes')
    recipes = c.fetchall()
    conn.close()

    results = f"Showing all {len(recipes)} recipes in the database:"

    if not recipes:
        message = "You don't have any recipes yet. Why not add your first one?"
        return render_template('index.html', recipes=recipes, message=message, total_recipes=total_recipes, recently_added=recently_added)
    
    return render_template('index.html', recipes=recipes, total_recipes=total_recipes, recently_added=recently_added, results=results)

# Add a new recipe
@app.route('/add', methods=['GET', 'POST'])
def add_recipe():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        date = datetime.now().strftime('%Y-%m-%d')
        prep_time = int(request.form['prep_time'])
        cook_time = int(request.form['cook_time'])
        ingredients = request.form['ingredients']
        instructions = request.form['instructions']
        variations = request.form['variations']
        notes = request.form['notes']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO recipes (title, author, date, prep_time, cook_time, ingredients, instructions, variations, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, author, date, prep_time, cook_time, ingredients, instructions, variations, notes))
        recipe_id = c.lastrowid

        # Handle image uploads
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and allowed_file(file.filename):
                    # Generate new filename with 10-digit hash
                    hash_value = generate_image_hash()
                    extension = file.filename.rsplit('.', 1)[1].lower()
                    new_filename = f"{hash_value}.{extension}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename).replace('\\', '/')
                    
                    file.save(filepath)
                    c.execute('''
                        INSERT INTO recipe_images (recipe_id, image_path)
                        VALUES (?, ?)
                    ''', (recipe_id, filepath))
        
        conn.commit()
        conn.close()
        flash('Recipe added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_recipe.html')

# View a single recipe
@app.route('/recipe/<int:recipe_id>')
def view_recipe(recipe_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,))
    recipe = c.fetchone()
    c.execute('SELECT * FROM recipe_images WHERE recipe_id = ?', (recipe_id,))
    images = c.fetchall()
    conn.close()

    if not recipe:
        return "Recipe not found", 404

    ingredients_list = recipe['ingredients'].split(',') if recipe['ingredients'] else []
    return render_template('view_recipe.html', recipe=recipe, ingredients_list=ingredients_list, images=images)

# Update a recipe
@app.route('/update/<int:recipe_id>', methods=['GET', 'POST'])
def update_recipe(recipe_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,))
    recipe = c.fetchone()
    c.execute('SELECT * FROM recipe_images WHERE recipe_id = ?', (recipe_id,))
    images = c.fetchall()

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        prep_time = int(request.form['prep_time'])
        cook_time = int(request.form['cook_time'])
        ingredients = request.form['ingredients']
        instructions = request.form['instructions']
        variations = request.form['variations']
        notes = request.form['notes']

        c.execute('''
            UPDATE recipes
            SET title = ?, author = ?, prep_time = ?, cook_time = ?, ingredients = ?, instructions = ?, variations = ?, notes = ?
            WHERE id = ?
        ''', (title, author, prep_time, cook_time, ingredients, instructions, variations, notes, recipe_id))

        # Handle new image uploads
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and allowed_file(file.filename):
                    # Generate new filename with 10-digit hash
                    hash_value = generate_image_hash()
                    extension = file.filename.rsplit('.', 1)[1].lower()
                    new_filename = f"{hash_value}.{extension}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename).replace('\\', '/')
                    
                    file.save(filepath)
                    c.execute('''
                        INSERT INTO recipe_images (recipe_id, image_path)
                        VALUES (?, ?)
                    ''', (recipe_id, filepath))

        conn.commit()
        conn.close()
        flash('Recipe updated successfully!', 'success')
        return redirect(url_for('view_recipe', recipe_id=recipe_id))
    
    conn.close()
    return render_template('update_recipe.html', recipe=recipe, images=images)

# Delete a recipe
@app.route('/delete_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def delete_recipe(recipe_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Retrieve image paths before deleting from the database
    c.execute('SELECT image_path FROM recipe_images WHERE recipe_id = ?', (recipe_id,))
    images = c.fetchall()
    
    # Delete associated images from the filesystem
    for image in images:
        image_path = image['image_path']
        if os.path.exists(image_path):
            os.remove(image_path)
    
    # Delete associated image records from the database
    c.execute('DELETE FROM recipe_images WHERE recipe_id = ?', (recipe_id,))
    
    # Delete the recipe
    c.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))
    
    conn.commit()
    conn.close()

    # Open a new connection for VACUUM
    conn = get_db_connection()
    conn.execute('VACUUM')
    conn.close()  # Close this new connection
    
    flash('Recipe and associated images deleted successfully!', 'success')
    return redirect(url_for('index'))

# Delete an image
@app.route('/delete_image/<int:image_id>')
def delete_image(image_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT image_path FROM recipe_images WHERE id = ?', (image_id,))
    image = c.fetchone()
    if image:
        os.remove(image['image_path'])  # Delete the file from the filesystem
        c.execute('DELETE FROM recipe_images WHERE id = ?', (image_id,))
        conn.commit()
        flash('Image deleted successfully!', 'success')
    conn.close()
    return redirect(request.referrer)

# Search for recipes
@app.route('/search', methods=['GET'])
def search():
    conn = get_db_connection()
    c = conn.cursor()

    # Base SQL query
    query = 'SELECT * FROM recipes WHERE 1=1'
    params = []

    # Keyword Search
    keyword = request.args.get('keyword')
    if keyword:
        query += ' AND (title LIKE ? OR ingredients LIKE ?)'
        params.extend([f'%{keyword}%', f'%{keyword}%'])

    # Ingredient Search
    ingredient = request.args.get('ingredient')
    if ingredient and not keyword:
        query += ' AND ingredients LIKE ?'
        params.append(f'%{ingredient}%')

    query += ' ORDER BY date DESC'
    c.execute(query, params)
    recipes = c.fetchall()

    # Get recent recipes
    c.execute('SELECT id, title, date FROM recipes ORDER BY date DESC LIMIT 10')
    recently_added = c.fetchall()

    # Get total recipe count
    c.execute('SELECT COUNT(*) FROM recipes')
    total_recipes = c.fetchone()[0]

    conn.close()

    if not recipes:
        results = "No recipes found matching your criteria."
    else:
        if keyword and ingredient:
            results = f"Found {len(recipes)} recipes matching your filters '{keyword}' and '{ingredient}':"
        elif keyword:
            results = f"Found {len(recipes)} recipes matching your keyword '{keyword}':"
        elif ingredient:
            results = f"Found {len(recipes)} recipes containing '{ingredient}':"
        else:
            results = f"Showing all {len(recipes)} recipes in the database:"

    return render_template('index.html', recipes=recipes, recently_added=recently_added, 
                           keyword=keyword, ingredient=ingredient, total_recipes=total_recipes, 
                           results=results)

# Generate a PDF for a recipe
@app.route('/generate_pdf/<int:recipe_id>')
def generate_pdf(recipe_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,))
    recipe = c.fetchone()
    conn.close()

    if recipe:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=recipe['title'], ln=True, align='C')
        pdf.multi_cell(0, 10, txt=f"Author: {recipe['author']}")
        pdf.multi_cell(0, 10, txt=f"Date: {recipe['date']}")
        pdf.multi_cell(0, 10, txt=f"Prep Time: {recipe['prep_time']} minutes")
        pdf.multi_cell(0, 10, txt=f"Cook Time: {recipe['cook_time']} minutes")
        pdf.multi_cell(0, 10, txt=f"Ingredients:\n{recipe['ingredients']}")
        pdf.multi_cell(0, 10, txt=f"Instructions:\n{recipe['instructions']}")
        pdf.multi_cell(0, 10, txt=f"Variations:\n{recipe['variations']}")
        pdf.multi_cell(0, 10, txt=f"Notes:\n{recipe['notes']}")
        pdf_output = f"recipe_{recipe_id}.pdf"
        pdf.output(pdf_output)
        return send_file(pdf_output, as_attachment=True)
    return "Recipe not found", 404

# Photo gallery
@app.route('/photo_gallery')
def photo_gallery():

    conn = get_db_connection()
    c = conn.cursor()

    # Get total recipe count
    c.execute('SELECT COUNT(*) FROM recipes')
    total_recipes = c.fetchone()[0]

    # Get all recipes
    c.execute('SELECT * FROM recipes')
    recipes = c.fetchall()

        # Get all recipe images
    c.execute('SELECT * FROM recipe_images')
    images = c.fetchall()
    conn.close()

    results = f"Showing all {len(recipes)} recipes in the database."

    if not recipes:
        message = "You don't have any recipes yet. Why not add your first one?"
        return render_template('gallery.html', recipes=recipes, message=message, total_recipes=total_recipes)
    
    return render_template('gallery.html', recipes=recipes, total_recipes=total_recipes, results=results, images=images)

# Interactive Menu


if __name__ == '__main__':
    init_db()
    app.run(debug=True)