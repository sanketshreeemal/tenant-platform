from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os

app = Flask(__name__)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///tenants.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define the Tenant model
class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    lease_start = db.Column(db.Date, nullable=False)
    lease_end = db.Column(db.Date, nullable=False)
    rent = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Tenant {self.unit}>'

# Define the Landlord model
class Landlord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Landlord {self.first_name} {self.last_name}>'

# Email configuration (use your Gmail credentials)
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'ecityhsrre@gmail.com'  # the sender's email address
SMTP_PASSWORD = 'Oro@1105'             # Replace with the app password generated for Gmail

def send_email(subject, body, recipient):
    """Send an email using SMTP."""
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = recipient

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SMTP_USERNAME, SMTP_PASSWORD)  # Log in to the SMTP server
            server.sendmail(SMTP_USERNAME, recipient, msg.as_string())  # Send the email
    except Exception as e:
        logging.error(f"Error sending email to {recipient}: {e}")

# Function to check lease expirations and send email alerts
def check_lease_expirations():
    with app.app_context():  # This ensures we are inside the Flask application context
        tenants = Tenant.query.all()  # Get all tenants from the database
        landlords = Landlord.query.all()  # Get all landlords from the database
        today = datetime.today().date()  # Get the current date

        for tenant in tenants:
            days_until_expiry = (tenant.lease_end - today).days
            if days_until_expiry in [30, 15, 7]:
                # Compose the email subject and body
                email_subject = f"Lease Expiry Alert for Unit {tenant.unit}"
                email_body = (
                    f"Dear Landlord,\n\n"
                    f"The lease for Unit {tenant.unit} is expiring in {days_until_expiry} days. "
                    f"Please renew the lease agreement.\n\n"
                    f"Best regards,\nYour Property Management System"
                )
                # Send the email to each landlord
                for landlord in landlords:
                    send_email(email_subject, email_body, landlord.email)

# Initialize the scheduler
scheduler = BackgroundScheduler()
# Schedule the job to run daily (for testing, you might want to set it to minutes or seconds)
scheduler.add_job(func=check_lease_expirations, trigger='interval', days=1, id='lease_expiry_check')

# Start the scheduler before the app starts
scheduler.start()

@app.teardown_appcontext
def shutdown_scheduler(exception=None):
    """Shut down the scheduler only if it's running."""
    if scheduler.running:  # Check if the scheduler is running
        scheduler.shutdown(wait=False)


# Route for home page
@app.route('/')
def index():
    return render_template('index.html')

# Route to view all tenants
@app.route('/tenants')
def view_tenants():
    tenants = Tenant.query.all()  # Query all tenants from the database
    landlords = Landlord.query.all()  # Get all landlords from the database
    today = datetime.today().date()

    # List to store tenants with upcoming expirations
    expiring_tenants = []

    for tenant in tenants:
        # Calculate the number of days until the lease expires
        days_until_expiry = (tenant.lease_end - today).days

        # Check if the lease is expiring soon (30, 15, or 7 days)
        if days_until_expiry in [30, 15, 7]:
            expiring_tenants.append((tenant, days_until_expiry))

    return render_template('tenants.html', tenants=tenants, expiring_tenants=expiring_tenants)

# Route to add a new tenant
@app.route('/add_tenant', methods=['GET', 'POST'])
def add_tenant():
    if request.method == 'POST':
        # Get the form data
        unit = request.form['unit']
        name = request.form['name']
        email = request.form['email']
        lease_start = request.form['lease_start']
        lease_end = request.form['lease_end']
        rent = request.form['rent']

        # Convert the form input dates to datetime objects
        lease_start_date = datetime.strptime(lease_start, '%Y-%m-%d').date()
        lease_end_date = datetime.strptime(lease_end, '%Y-%m-%d').date()

        # Create a new tenant object
        new_tenant = Tenant(
            unit=unit,
            name=name,
            email=email,
            lease_start=lease_start_date,
            lease_end=lease_end_date,
            rent=rent
        )

        # Add the new tenant to the database
        db.session.add(new_tenant)
        db.session.commit()

        # Redirect to the tenant list page
        return redirect(url_for('view_tenants'))

    return render_template('add_tenant.html')

# Route to add a new landlord
@app.route('/add_landlord', methods=['GET', 'POST'])
def add_landlord():
    if request.method == 'POST':
        # Get form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone_number = request.form['phone_number']

        # Create a new landlord object
        new_landlord = Landlord(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number
        )

        # Add to the database
        db.session.add(new_landlord)
        db.session.commit()

        return redirect(url_for('view_landlords'))

    return render_template('add_landlord.html')

# Route to view all landlords
@app.route('/landlords')
def view_landlords():
    landlords = Landlord.query.all()  # Query all landlords from the database
    return render_template('landlords.html', landlords=landlords)

# Route to delete a tenant
@app.route('/delete_tenant', methods=['GET', 'POST'])
def delete_tenant():
    if request.method == 'POST':
        # Get the unit number from the form
        unit = request.form['unit']

        # Query the tenant based on the unit number
        tenant = Tenant.query.filter_by(unit=unit).first()

        if tenant:
            # If tenant exists, redirect to a confirmation page
            return redirect(url_for('confirm_delete', unit=tenant.unit))
        else:
            # If no tenant is found, return an error message
            return render_template('delete_tenant.html', error="No tenant found with that unit number.")

    return render_template('delete_tenant.html')

# Route to confirm tenant deletion
@app.route('/confirm_delete/<unit>', methods=['GET', 'POST'])
def confirm_delete(unit):
    # Query the tenant by unit number
    tenant = Tenant.query.filter_by(unit=unit).first()

    if not tenant:
        return redirect(url_for('view_tenants'))

    if request.method == 'POST':
        if request.form['confirm'] == 'Yes':
            # Delete the tenant from the database
            db.session.delete(tenant)
            db.session.commit()
            return redirect(url_for('view_tenants'))
        else:
            # If "No" is selected, redirect back to the main page
            return redirect(url_for('index'))

    return render_template('confirm_delete.html', tenant=tenant)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)

# Create the database and the tenants & landlords tables (run this once)
#with app.app_context():
#    db.create_all()
