from flask import *
from flask_sqlalchemy import SQLAlchemy
import os
import requests
from datetime import datetime
import os
from random import shuffle
from datetime import date, time, timedelta
from flask_login import login_required,login_user,logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from mail_service import *

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', default=os.urandom(16).hex())
db = SQLAlchemy(app)



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    vehicle = db.Column(db.String(20), nullable=True)  
    password_hash = db.Column(db.String(128))

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)




class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=True)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)

    def __init__(self, id, status, date=None, start_time=None, end_time=None):
        self.id = id
        self.status = status
        self.date = date
        self.start_time = start_time
        self.end_time = end_time


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slot.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    commercial = db.Column(db.Boolean, nullable=False)
    license_plate_number = db.Column(db.String(10), nullable=False)
    
    # Relationships
    slot = db.relationship('Slot', backref=db.backref('reservations', lazy=True))



from flask_login import LoginManager
from flask_login import current_user



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # specify what page to load for NON-authenticated users

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


def initialize_db():
    if os.path.exists('test.db'):
        os.remove('test.db')

    db.create_all()

    # Check if slots are already initialized
    if Slot.query.first() is None:
        # Initialize slots for each hour of the day
        statuses = ['occupied', 'reserved', 'empty']
        for i in range(24):
            start_time = time(hour=i)
            end_time = time(hour=i+1) if i < 23 else time(hour=0)

            # Assign statuses randomly
            shuffle(statuses)
            status = statuses[0]

            slot = Slot(id=i+1, status=status, date=date.today(), start_time=start_time, end_time=end_time)
            db.session.add(slot)

    admin = User.query.filter_by(username='admin').first()
    if admin is None:
        admin = User(username='admin',email ='admin@sau.com', is_admin=True)
        admin.set_password('1234')
        db.session.add(admin)
        
    db.session.commit()


@app.route('/')
@app.route('/index')
def home():
    slots = Slot.query.all()
    return render_template('home.html', slots=slots)


@app.route('/parking_status')
def parking_status():
    slots = Slot.query.all()
    return render_template('parking_status.html', slots=slots) 


@app.route('/reserve', methods=['GET', 'POST'])
@login_required
def reserve():
    price = 1.99
    if request.method == 'POST':
        slot_id = request.form.get('slot')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
        end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()

        slot = Slot.query.get(slot_id)
        slot.status = 'reserved'
        slot.date = date
        slot.start_time = start_time
        slot.end_time = end_time
        db.session.commit()

        # Prepare the email content
        subject = "Reservation Confirmation"
        content = f"Hello {current_user.username},\n\nYour reservation for Slot {slot.id} on {date} from {start_time} to {end_time} has been confirmed.\n\nThanks,\nParking Management Team"

        # Send the confirmation email
        send_reservation_confirmation(current_user.email, subject, content)

        return redirect('/parking_status')

    slots = Slot.query.filter_by(status='empty').all()
    return render_template('reserve.html', slots=slots, price=price)


@app.route('/careers')
def careers():
    return render_template('careers.html')


@app.route('/contact_us')
def contact():
    return render_template('contact_us.html')


@app.route('/about_us')
def about_us():
    return render_template('about_us.html')


@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        abort(403)
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Username or password is incorrect. Please try again.')
            return redirect('/login')
        login_user(user)
        return redirect('/')
    return render_template('login.html')


@app.route("/forgot_password", methods=['GET', 'POST'])
def forgot_password():
    # Implement functionality for user to reset password
    return render_template('forgot_password.html')

@app.route("/account_creation", methods=['GET', 'POST'])
def account_creation():
    # Implement functionality for user to create an account
    return render_template('account_creation.html')


@app.route("/create_account", methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        username = request.form.get('name')
        email = request.form.get('email')
        vehicle = request.form.get('vehicle')
        password = request.form.get('password')

        # Check if username or email already exists
        user = User.query.filter((User.username == username) | (User.email == email)).first()
        if user:
            print('Username or email already exists.')
            flash('Username or email already exists.')
            return redirect(url_for('create_account'))

        # Create a new user and add to the database
        new_user = User(username=username, 
                        email=email, 
                        vehicle=vehicle)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully. You can now log in.')
        return redirect(url_for('login'))

    return render_template('account_creation.html')




    




@app.route('/reserve_slot', methods=['POST'])
@login_required
def reserve_slot():
    # Get form data
    slot_id = request.form.get('slot')

    date_str = request.form.get('date')
    date = datetime.strptime(date_str, "%Y-%m-%d").date()  # Convert string to date

    start_time_str = request.form.get('start_time')
    start_time = datetime.strptime(start_time_str, "%H:%M").time()  # Convert string to time

    end_time_str = request.form.get('end_time')
    end_time = datetime.strptime(end_time_str, "%H:%M").time()  # Convert string to time

    license_plate_number = request.form.get('license_plate_number')
    commercial = request.form.get('commercial') == 'true'

    session['reservation_details'] = {
        'slot_id': slot_id,
        'date': date_str,
        'start_time': start_time_str,
        'end_time': end_time_str,
        'license_plate_number': license_plate_number,
        'commercial': commercial
    }

    # Redirect to payment gateway page
    return redirect(url_for('to_payment_gateway'))

def get_reservations(user_id):
    return Reservation.query.filter_by(user_id=user_id).all()

@app.route('/my_reservations', methods=['GET'])
@login_required
def my_reservations():
    reservations = get_reservations(current_user.id)
    return render_template('my_reservations.html', reservations=reservations)

@app.route('/confirm_slot', methods=['POST'])
@login_required
def confirm_slot():

    reservation_details = session.get('reservation_details')

    if reservation_details:
        # Retrieve individual details from the session
        slot_id = reservation_details.get('slot_id')
        date_str = reservation_details.get('date')
        start_time_str = reservation_details.get('start_time')
        end_time_str = reservation_details.get('end_time')
        license_plate_number = reservation_details.get('license_plate_number')
        commercial = reservation_details.get('commercial')

        # Convert date and time strings to date and time objects
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        end_time = datetime.strptime(end_time_str, "%H:%M").time()

    # Create new reservation
    reservation = Reservation(
        user_id=current_user.id,
        slot_id=slot_id,
        date=date,
        start_time=start_time,
        end_time=end_time,
        license_plate_number=license_plate_number,
        commercial=commercial
    )

    # Save to database
    db.session.add(reservation)
    db.session.commit()

    # Prepare the email content
    subject = "Reservation Confirmation"
    content = f"""
                    Dear {current_user.username},

                    Thank you for your reservation. Here are the details of your reservation:

                    Parking Slot: {slot_id}
                    Date: {date}
                    Start Time: {start_time.strftime('%H:%M')}
                    End Time: {end_time.strftime('%H:%M')}
                    License Plate Number: {license_plate_number}

                    We look forward to serving you.

                    Best,
                    Your Parking Service Team
                    """
    # Send the confirmation email
    send_reservation_confirmation(current_user.email, subject, content)

    reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    return render_template('my_reservations.html', reservations=reservations)


@app.route('/to_payment_gateway', methods=['POST'])
@login_required
def to_payment_gateway():

    print('here')
    # Get form data
    slot_id = request.form.get('slot')

    date_str = request.form.get('date')
    date = datetime.strptime(date_str, "%Y-%m-%d").date()  # Convert string to date

    start_time_str = request.form.get('start_time')
    start_time = datetime.strptime(start_time_str, "%H:%M").time()  # Convert string to time

    end_time_str = request.form.get('end_time')
    end_time = datetime.strptime(end_time_str, "%H:%M").time()  # Convert string to time

    license_plate_number = request.form.get('license_plate_number')
    commercial = request.form.get('commercial') == 'true'

    registration_fee = 1.99
    commercial_rate = 8.99
    non_commercial_rate = 4.99

    # Calculate hours
    hours = (datetime.combine(date, end_time) - datetime.combine(date, start_time)).seconds / 3600

    # Determine rate
    rate = commercial_rate if commercial else non_commercial_rate

    # Calculate total cost
    amount_to_pay = hours * rate + registration_fee

    # Store reservation details in session
    session['reservation_details'] = {
        'slot_id': slot_id,
        'date': date_str,
        'start_time': start_time_str,
        'end_time': end_time_str,
        'license_plate_number': license_plate_number,
        'commercial': commercial,
        'amount_to_pay': amount_to_pay
    }

    # Redirect to payment gateway page
    return redirect(url_for('payment_gateway'))

@app.route('/payment_gateway', methods=['GET'])
@login_required
def payment_gateway():
    reservation_details = session.get('reservation_details')
    if reservation_details is None:
        return redirect(url_for('error_page')) 

    return render_template('payment_gateway.html', amount_to_pay=reservation_details['amount_to_pay'])





if __name__ == '__main__':
    with app.app_context():
        # This ensures that the code inside the context will have access to the app
        initialize_db()
        app.run()
