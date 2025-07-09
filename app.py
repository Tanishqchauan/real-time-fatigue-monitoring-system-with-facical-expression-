import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flashing messages

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # Replace with your MySQL username
app.config['MYSQL_PASSWORD'] = 'root'  # Replace with your MySQL password
app.config['MYSQL_DB'] = 'fatigue_monitoring_system'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # To fetch rows as dictionaries

mysql = MySQL(app)

@app.route('/')
def index():
    return redirect(url_for('start'))

# Start Page Route
@app.route('/start')
def start():
    return render_template('start.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            # Ensure the user object has the correct keys
            stored_password = user.get('password')
            if check_password_hash(stored_password, password):
                session['user_id'] = user.get('id')  # Use 'id' instead of 'user_id'
                session['username'] = user.get('name')  # Ensure 'name' exists
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Incorrect password. Please try again.', 'danger')
        else:
            flash('No account found with that email.', 'danger')

    return render_template('login.html')

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        family_mobile = request.form['family_mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password == confirm_password:
            hashed_password = generate_password_hash(password)
            try:
                cursor = mysql.connection.cursor()
                cursor.execute(
                    "INSERT INTO users (name, email, mobile, family_mobile, password) VALUES (%s, %s, %s, %s, %s)",
                    (name, email, mobile, family_mobile, hashed_password)
                )
                mysql.connection.commit()
                cursor.close()
                flash('Registration successful! You can log in now.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                print(f"Error: {e}")
                flash('There was an error in registration. Please try again.', 'danger')
        else:
            flash('Passwords do not match. Please try again.', 'danger')

    return render_template('register.html')

# Home Route
@app.route('/home')
def home():
    if 'user_id' in session:
        return render_template('home.html', username=session['username'])
    else:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()

        # Fetch filtered log data for the current user
        detected_details = [
            {'label': 'Drowsy Alerts', 'value': '3'},
            {'label': 'Total Session Time', 'value': '45 minutes'},
            {'label': 'Head Movements Detected', 'value': '5'},
        ]
        report_data = parse_log_file(user_id)  # Pass user_id to filter logs
        
        return render_template(
            'dashboard.html',
            username=session['username'],
            detected_details=detected_details,
            report_data=report_data
        )
    else:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))

# Start Monitoring Route
@app.route('/start_monitoring')
def start_monitoring():
    if 'user_id' in session:
        try:
            # Ensure monitoring is not started multiple times
            if 'monitoring_active' not in session:
                script_path = os.path.join(os.getcwd(), "model.py")
                
                # Check if the model script exists
                if os.path.exists(script_path):
                    subprocess.Popen(["python", script_path])
                    session['monitoring_active'] = True  # Track monitoring status
                    flash('Monitoring started successfully.', 'success')
                else:
                    flash('Monitoring model script not found. Please try again.', 'danger')
            else:
                flash('Monitoring is already active. Please wait.', 'warning')
        except Exception as e:
            print(f"Error: {e}")
            flash(f'There was an error starting the monitoring: {e}', 'danger')
        return redirect(url_for('home'))
    else:
        flash('Please log in to start monitoring.', 'warning')
        return redirect(url_for('login'))

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Parse Log File to Create Report
def parse_log_file(id):
    report_data = []
    log_file_path = os.path.join(os.getcwd(), 'log.txt')  # Path to your log file
    
    try:
        with open(log_file_path, 'r') as log_file:
            for line in log_file:
                # Assuming logs are structured with user_id and a timestamp and log message
                try:
                    # Example log format: "user_id - timestamp - message"
                    log_user_id, timestamp, message = line.split(" - ", 2)
                    if int(id) == id:  # Filter logs based on user_id
                        timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                        report_data.append({
                            'timestamp': timestamp,
                            'message': message.strip()
                        })
                except ValueError:
                    # Handle case where the log line is not in the expected format
                    continue
    except FileNotFoundError:
        flash('Log file not found.', 'danger')
    
    return report_data

# Route to Display Report
@app.route('/generate_report')
def generate_report():
    # Parse the log file
    report_data = parse_log_file(session['id'])

    # If no data in report, flash a message and return
    if not report_data:
        flash('No logs to generate the report from.', 'warning')
        return render_template('report.html', report_data=[])

    # Render report in HTML
    return render_template('report.html', report_data=report_data)

# Route to Download Report as CSV
@app.route('/download_report')
def download_report():
    # Parse the log file
    report_data = parse_log_file(session['id'])

    # If no data in report, return an error
    if not report_data:
        flash('No logs to generate the report from.', 'warning')
        return redirect(url_for('generate_report'))

    # Create a temporary CSV report
    csv_file_path = os.path.join(os.getcwd(), 'report.csv')
    with open(csv_file_path, 'w') as file:
        file.write("Timestamp,Message\n")
        for entry in report_data:
            file.write(f"{entry['timestamp']},{entry['message']}\n")

    # Send the CSV file for download
    return send_file(csv_file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
