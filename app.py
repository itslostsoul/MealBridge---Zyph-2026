from flask import Flask, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL

app = Flask(__name__)

app.secret_key = 'mindflayers_secret_key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1975@'
app.config['MYSQL_DB'] = 'mealbridge_db'

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM users WHERE email= %s AND password= %s', (email, password))
        account = cur.fetchone()
        if account:
            session['loggedin'] = True
            session['user_id'] = account[0]
            session['role'] = account[4]
            return redirect(url_for('dashboard'))
        else:
            msg = 'Incorrect email or password'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        if password != confirm_password:
            msg = "Passwords do not match!"
            return render_template('register.html', msg=msg)
        
        cur = mysql.connection.cursor()
        cur.execute('INSERT INTO users (full_name, email, password, role) VALUES(%s, %s, %s, %s)', (full_name, email, password, role))
        mysql.connection.commit()
        return redirect(url_for('login'))
    return render_template('register.html', msg=msg)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    requested_mode = request.args.get('mode')
    user_role = session['role']
    alert_msg = None

    if requested_mode and requested_mode != user_role:
        if user_role == 'donor':
            alert_msg = "⚠️ Access Denied: You are a Donor account! You cannot request food. Redirecting to your Donor Dashboard."
        else:
            alert_msg = "⚠️ Access Denied: You are a Recipient account! You cannot post food. Redirecting to your Recipient Dashboard."

    cur = mysql.connection.cursor()

    if session['role'] == 'donor':
        cur.execute("SELECT * FROM food_items WHERE donor_id = %s", [session['user_id']])
        my_food = cur.fetchall()
        
        cur.execute("SELECT green_points FROM users WHERE id = %s", [session['user_id']])
        user_data = cur.fetchone()
        current_points = user_data[0] if user_data else 0
        
        return render_template('donor_dashboard.html', food=my_food, points=current_points, alert_msg=alert_msg)
    
    else:
        cur.execute("SELECT * FROM food_items WHERE status = 'available'")
        available_food = cur.fetchall()
        return render_template('recipient_dashboard.html', food=available_food, alert_msg=alert_msg)

@app.route('/post_food', methods=['POST'])
def post_food():
    if session['role'] == 'donor':
        food_name = request.form['food_name']
        quantity = request.form['quantity']
        donor_id = session['user_id']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO food_items (donor_id, name, quantity_kg) VALUES (%s, %s, %s)", (donor_id, food_name, quantity))
        cur.execute("UPDATE users SET green_points = green_points + 10 WHERE id = %s", [donor_id])
        mysql.connection.commit()
        cur.close()
    return redirect(url_for('dashboard'))

@app.route('/claim_food/<int:food_id>')
def claim_food(food_id):
    if session['role'] == 'recipient':
        recipient_id = session['user_id']
        cur = mysql.connection.cursor()
        cur.execute("UPDATE food_items SET status = 'claimed' WHERE id = %s", [food_id])
        cur.execute("INSERT INTO claims (food_id, recipient_id) VALUES (%s, %s)", (food_id, recipient_id))
        mysql.connection.commit()
        cur.close()
    return redirect(url_for('dashboard'))

@app.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html')

if __name__ == '__main__':
    app.run(debug=True)