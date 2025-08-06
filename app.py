from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Book, Transaction
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    books = Book.query.all()
    return render_template('home.html', books=books)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/books')
@login_required
def list_books():
    books = Book.query.all()
    return render_template('books.html', books=books)

@app.route('/checkout/<int:book_id>', methods=['POST'])
@login_required
def checkout(book_id):
    book = Book.query.get_or_404(book_id)
    
    if not book.available:
        flash('Book is not available', 'danger')
        return redirect(url_for('list_books'))
    
    # Create transaction
    transaction = Transaction(
        user_id=current_user.id,
        book_id=book.id,
        checkout_date=datetime.now(),
        return_date=datetime.now() + timedelta(days=14)
    )
    
    # Update book status
    book.available = False
    
    db.session.add(transaction)
    db.session.commit()
    
    flash(f'You have checked out {book.title}', 'success')
    return redirect(url_for('list_books'))

@app.route('/return/<int:transaction_id>', methods=['POST'])
@login_required
def return_book(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    if transaction.user_id != current_user.id and not current_user.is_librarian:
        flash('You cannot return this book', 'danger')
        return redirect(url_for('my_books'))
    
    # Update book status
    book = Book.query.get(transaction.book_id)
    book.available = True
    
    # Update return date
    transaction.return_date = datetime.now()
    
    db.session.commit()
    
    flash(f'You have returned {book.title}', 'success')
    return redirect(url_for('my_books'))

@app.route('/my-books')
@login_required
def my_books():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        return_date=None
    ).all()
    return render_template('my_books.html', transactions=transactions)

# Admin routes
@app.route('/add-book', methods=['GET', 'POST'])
@login_required
def add_book():
    if not current_user.is_librarian:
        flash('You are not authorized', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        isbn = request.form['isbn']
        
        book = Book(title=title, author=author, isbn=isbn)
        db.session.add(book)
        db.session.commit()
        
        flash('Book added successfully', 'success')
        return redirect(url_for('list_books'))
    
    return render_template('add_book.html')

if __name__ == '__main__':
    app.run(debug=True)