from flask import Flask, render_template, request, redirect, session, flash, url_for,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import logging
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import func
import os
from datetime import datetime, timedelta, timezone

# Configure the Flask app

app= Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://root:Shiv#8005@localhost/job"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root' 
app.config['MYSQL_PASSWORD'] = 'Shiv#8005'
app.config['MYSQL_DB'] = 'job'
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Directory to save uploaded files
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}  # Allowed file types
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG)
# Initialize the database
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
mysql = MySQL(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app) 
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = 'info'
# Route to login
import pyotp
from flask_mail import Mail , Message
from flask import current_app
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'pramodbardoti@gmail.com'
app.config['MAIL_PASSWORD'] = 'dewb ndwk cweo fizp'
mail = Mail(app)
# Assuming you've configured Flask-Mail in your app already
def send_otp_email(company, otp):
    msg = Message("Your OTP Code", sender="pramodbardoti@gmail.com", recipients=[company.email])
    msg.body = f"login RojiRoti my job portal Do not share OTP2 : {otp}"
    try:
        mail.send(msg)
        logging.info(f"OTP sent to {company.email}")
    except Exception as e:
        logging.error(f"Error sending OTP to {company.email}: {e}")



class person(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.String(500), nullable=True)
    profile_picture = db.Column(db.String(100), nullable=True)
    otp = db.Column(db.String(6), nullable=True)  # OTP stored here
    otp_expiry = db.Column(db.DateTime, nullable=True) 
    
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<person {self.username}>'
    @property
    def user_type(self):
        return 'person'
# Load user function for Flask-Login
from flask import session

@login_manager.user_loader
def load_user(user_id):
    user_type = session.get('user_type')  # Get user_type from session

    if user_type == 'person':
        return person.query.get(int(user_id))
    elif user_type == 'company':
        return company.query.get(int(user_id))
    
    return None  # Default fallback


# Create the database tables
with app.app_context():
    try:
        db.create_all()
        logging.info("Database tables created successfully.")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")

# Route to login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        logging.debug(f"Login attempt with username: {username}")

        user1 = person.query.filter_by(username=username).first()

        if user1 and user1.password == password:
            # Generate OTP for user
            otp = pyotp.random_base32()[:6]  # Generate a 6-digit OTP
            user1.otp = otp
           
            user1.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=5) # OTP expiry time is 5 minutes

            db.session.commit()

            # Send OTP to the user's email
            send_otp_email(user1, otp)
            session['user_type'] = 'person'
            flash('OTP sent to your email. Please check your inbox.', 'info')
            logging.info(f"OTP sent to {user1.email}")
            
            # Redirect to the OTP verification page
            return redirect(url_for('verify_otp1', username=username))

        flash('Invalid username or password!', 'danger')
        logging.warning(f"Invalid login for username: {username}")
        return redirect(url_for('login'))
    
    return render_template('login_register.html')
@app.route('/verify_otp1/<username>', methods=['GET', 'POST'])
def verify_otp1(username):
    user1 = person.query.filter_by(username=username).first_or_404()

    if request.method == 'POST':
        entered_otp = request.form.get('otp')

        # Check if OTP is expired
        if datetime.utcnow() > user1.otp_expiry:
            flash('OTP expired. Please request a new one.', 'danger')
            logging.warning(f"OTP expired for {user1.username}")
            return redirect(url_for('login'))

        # Check if OTP matches
        if entered_otp == user1.otp:
            session['user_type'] = 'person'
            login_user(user1)
            flash('Logged in successfully!', 'success')
            logging.info(f"User {username} logged in.")
            user1.otp = None  # Clear OTP after successful login
            user1.otp_expiry = None  # Clear OTP expiry time
            db.session.commit()
            return redirect(url_for('dashboard'))

        flash('Invalid OTP. Please try again.', 'danger')
        logging.warning(f"Invalid OTP entered for {user1.username}")
        return redirect(url_for('verify_otp1', username=username))
    
    return render_template('verify_otp1.html', username=username)


# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if person.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        try:
            # Create new user
            new_user = person(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()  # Commit to get the new user's ID

            flash('Account created successfully! Please log in.', 'success')
            logging.info(f"User registered: {username} ({email})")
            return redirect(url_for('login'))
        
        except Exception as e:
            logging.error(f"Error saving user to database: {e}")
            db.session.rollback()
            flash('An error occurred while creating your account. Please try again.', 'danger')
            return redirect(url_for('register'))

    return render_template('login_register.html')

# Route to display the profile page
@app.route('/profile/<username>')
@login_required
def profile(username):
    # Debugging output
    user1 = person.query.filter_by(username=username).first_or_404()
    return render_template('profile.html', user1=user1)


# Route to edit profile information
@app.route('/edit_profile/<username>', methods=['GET', 'POST'])
@login_required
def edit_profile(username):
    user1 = person.query.filter_by(username=username).first_or_404()

    if request.method == 'POST':
        # Update the user profile fields only if they are provided
        if request.form['email']:
            user1.email = request.form['email']
        
        if request.form['last_name']:
            user1.last_name = request.form['last_name']
        
        if request.form['phone']:
            user1.phone = request.form['phone']
        
        if request.form['bio']:
            user1.bio = request.form['bio']

        # Handle profile picture upload (only if a new one is uploaded)
        if 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture and profile_picture.filename:
                # Secure the file name
                profile_picture_filename = secure_filename(profile_picture.filename)

                # Ensure the upload folder exists
                upload_folder = app.config['UPLOAD_FOLDER']
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)

                # Save the uploaded file
                profile_picture.save(os.path.join(upload_folder, profile_picture_filename))

                # Save the filename in the user's profile
                user1.profile_picture = profile_picture_filename

        # Commit the changes to the database
        db.session.commit()

        # Redirect to the profile page with updated data
        return redirect(url_for('profile', username=user1.username))

    return render_template('edit_profile.html', user1=user1)
# Login route
@app.route('/')

@app.route('/index2')
def index():
    user = apply.query.all()
    
    return render_template('index2.html',user=user)  # Replace with your dashboard page
 

@app.route('/about2')
def about2():
    return render_template('about2.html')  # Show the About page
# @app.route('/update_post')
# def update_post():
#     return render_template('job-detail2.html')  
@app.route('/contact2')
def contact2():
   return render_template('contact2.html')

@app.route('/about3')
def about3():
    return render_template('about3.html')  # Show the About page
   
@app.route('/contact3')
def contact3():
   return render_template('contact3.html')
@app.route('/job-list2')
def job_list2():
    user = Job.query.all()
 
    return render_template('job-list2.html',user=user)  # Show the About page
   
@app.route('/job-detail2')
def job_detail2():
    user = Job.query.all()
  
    return render_template('job-detail2.html',user=user,)


# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')  # Replace with your actual dashboard template

@app.route('/dashboard1')
def dashboard1():
    return render_template('index3.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/test')
def test():
    return render_template('testimonial.html', )
@app.route('/test2')
def test2():
    return render_template('testimonial2.html', )


@app.route('/joblist')
def joblist():
    user = Job.query.all()
   
    return render_template('job-list.html',user=user)


@app.route('/jobdetail')
def jobdetail():
    user = Job.query.all()
                                
    
    return render_template('job-detail.html',user=user)


@app.route('/category')
def category():
    return render_template('category.html', )  # Ensure the 'login' route exists
@app.route('/category2')
def category2():
    return render_template('category2.html', ) 

@app.route('/contact')
def contact():
      return render_template('contact.html')


@app.route('/error')
def error_page():
      return render_template('404.html')


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(200), nullable=False)
    Job_cetegoray = db.Column(db.String(1000), nullable=False)
    country_name = db.Column(db.String(100), nullable=False)
    min_salary = db.Column(db.Float, nullable=False)
    max_salary = db.Column(db.Float, nullable=False)
    job_type = db.Column(db.String(100), nullable=False)
    Vacancy=  db.Column(db.String(1000), nullable=False)
    job_description=db.Column(db.String(1000), nullable=False)
    Responsibility = db.Column(db.String(1000), nullable=False)
    logo_path = db.Column(db.String(200), nullable=True)
    Qualifications=db.Column(db.String(1000), nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Job {self.job_name}>"

# Create the database and table
with app.app_context():
    db.create_all()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to handle job posting
@app.route('/post', methods=['GET', 'POST'])
def post():
   
        if request.method == 'POST':
            # Validate input
            job_name = request.form.get('job_name')
            country_name = request.form.get('country_name')
            min_salary = request.form.get('min_salary')
            max_salary = request.form.get('max_salary')
            job_type = request.form.get('job_type')
            job_description=request.form.get('job_description')
            Responsibility =request.form.get('Responsibility')
            company_logo = request.files.get('company_logo')
            Qualifications=request.form.get('Qualifications')
            Vacancy= request.form.get('Vacancy')
            Job_cetegoray= request.form.get('Job_cetegoray')

            # Check required fields
            if not all([job_name,Job_cetegoray, country_name, min_salary, max_salary, Vacancy,job_type,job_description,Responsibility,Qualifications]):
                flash('All fields are required except the logo.', 'error')
                return redirect('/post')

            # Validate salary
            try:
                min_salary = float(min_salary)
                max_salary = float(max_salary)
                if min_salary > max_salary:
                    flash('Minimum salary cannot be greater than maximum salary.', 'error')
                    return redirect('/post')
            except ValueError:
                flash('Salary must be a valid number.', 'error')
                return redirect('/post')

            # Handle file upload
            logo_path = None
            if company_logo and allowed_file(company_logo.filename):
                filename = secure_filename(company_logo.filename)
                logo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                company_logo.save(logo_path)

            # Save the job post
            new_job = Job(
                job_name=job_name,
                country_name=country_name,
                min_salary=min_salary,
                max_salary=max_salary,
                job_type=job_type,
                job_description=job_description,
                Responsibility=Responsibility,
                logo_path=logo_path,
                Qualifications=Qualifications,
                Vacancy=Vacancy,
                Job_cetegoray=Job_cetegoray
                
            )
            db.session.add(new_job)
            db.session.commit()

            flash('Job posted successfully!', 'success')
            return redirect('/dashboard1')

        return render_template('post_a_job.html')  # Make sure this template exists and contains necessary fields
   
# API endpoint to list all job postings
@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    jobs = Job.query.all()
    return jsonify([
        {
            "id": job.id,
            "job_name": job.job_name,
            "country_name": job.country_name,
            "min_salary": job.min_salary,
            "max_salary": job.max_salary,
            "job_type": job.job_type,
            "Responsibility":job.Responsibility,
            "logo_path": job.logo_path,
            "Qualifications": job.Qualifications,
            "Job_cetegoray": job.Job_cetegoray,
            "Vacancy":job.Vacancy,   
            "date_posted": job.date_posted.strftime("%Y-%m-%d %H:%M:%S"),
        } for job in jobs
     # Redirect to login if not logged in
    ])
@app.route('/logout')
@login_required
def logout():
    # Check if the user is a company user BEFORE clearing the session
    if 'company_type' in session:
        flash('You have been logged out from the company dashboard.', 'info')
        session.clear()
        return redirect(url_for('company1'))  # Redirect back to company login
    else:
        flash('You have been logged out.', 'info')
        session.clear()
        return redirect(url_for('login'))  # Redirect to user login
#  post a job update
@app.route('/u_post/<int:id>', methods=['GET', 'POST'])
def u_post(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        job_name = request.form['job_name']
        country_name = request.form['country_name']
        min_salary = request.form['min_salary']
        max_salary = request.form['max_salary']
        job_type = request.form['job_type']
        job_description = request.form['job_description']
        Responsibility = request.form['Responsibility']
        company_logo = request.files['company_logo']
        Qualifications = request.form['Qualifications']
        Vacancy= request.form['Vacancy']
        Job_cetegoray= request.form['Job_cetegoray']

        if company_logo:
            company_logo_filename = secure_filename(company_logo.filename)
            company_logo.save(os.path.join(app.config['UPLOAD_FOLDER'], company_logo_filename))
        else:
            company_logo_filename = user['company_logo']  # Use existing logo if no new logo uploaded

        cur.execute("""
            UPDATE job SET
                job_name = %s,
                country_name = %s,
                min_salary = %s,
                max_salary = %s,
                job_type = %s,
                job_description = %s,
                Responsibility = %s,
                logo_path = %s,
                Qualifications = %s
                Job_cetegoray=%s
                Vacancy=%s
            WHERE id = %s
        """, (job_name, country_name, min_salary, max_salary, job_type, job_description, Responsibility, 'static\\uploads\\'+company_logo_filename, Qualifications,Job_cetegoray,Vacancy, id))

        mysql.connection.commit()
        cur.close()
        return redirect(url_for('job_detail2'))

    cur.execute("SELECT * FROM job WHERE id = %s", (id,))
    user = cur.fetchone()
    cur.close()
    return render_template('update_post.html', user=user)
#---------------------------------------------------------------------------------------------------------------------------------
class company(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    companyname = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(500), nullable=False)
    email = db.Column(db.String(500), nullable=False, unique=True)
    company_type = db.Column(db.String(500), nullable=False)
    company_image = db.Column(db.String(500), nullable=True)
    city = db.Column(db.String(500), nullable=True)
    location = db.Column(db.String(500), nullable=True)
    bio = db.Column(db.String(500), nullable=True)
    otp = db.Column(db.String(6), nullable=True)  # OTP stored here
    otp_expiry = db.Column(db.DateTime, nullable=True) 
    
    def __repr__(self):
        return f'<company {self.companyname}>'
    @property
    def user_type(self):
        return 'company'
# Load user function for Flask-Login


# Create the database tables
with app.app_context():
    try:
        db.create_all()
        logging.info("Database tables created successfully.")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")


@app.route('/company', methods=['GET', 'POST'])
def company1():
    if request.method == 'POST':
        companyname = request.form.get('companyname')
        password = request.form.get('password')
        logging.debug(f"Login attempt with companyname: {companyname}")

        user = company.query.filter_by(companyname=companyname).first()

        if user and user.password == password:
            # Generate OTP for user
            otp = pyotp.random_base32()[:6]  # Generate a 6-digit OTP
            user.otp = otp
           
            user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=5) # OTP expiry time is 5 minutes

             
            db.session.commit()

            # Send OTP to the user's email
            send_otp_email(user, otp)
            session['user_type'] = 'company'
            flash('OTP sent to your email. Please check your inbox.', 'info')
            logging.info(f"OTP sent to {user.email}")
            
            # Redirect to the OTP verification page
            return redirect(url_for('verify_otp', companyname=companyname))

        flash('Invalid username or password!', 'danger')
        logging.warning(f"Invalid login for username: {companyname}")
        return redirect(url_for('company1'))
    
    return render_template('company.html')
@app.route('/verify_otp/<companyname>', methods=['GET', 'POST'])
def verify_otp(companyname):
    user = company.query.filter_by(companyname=companyname).first_or_404()

    if request.method == 'POST':
        entered_otp = request.form.get('otp')

        # Check if OTP is expired
        if datetime.utcnow() > user.otp_expiry:
            flash('OTP expired. Please request a new one.', 'danger')
            logging.warning(f"OTP expired for {user.companyname}")
            return redirect(url_for('company1'))

        # Check if OTP matches
        if entered_otp == user.otp:
            session['user_type'] = 'company'
            login_user(user)
            flash('Logged in successfully!', 'success')
            logging.info(f"User {companyname} logged in.")
            user.otp = None  # Clear OTP after successful login
            user.otp_expiry = None  # Clear OTP expiry time
            db.session.commit()
            return redirect(url_for('dashboard1'))

        flash('Invalid OTP. Please try again.', 'danger')
        logging.warning(f"Invalid OTP entered for {user.companyname}")
        return redirect(url_for('verify_otp', companyname=companyname))
    
    return render_template('verify_otp.html', companyname=companyname)

# Register route
@app.route('/register1', methods=['GET', 'POST'])
def register1():
    if request.method == 'POST':
        companyname = request.form.get('companyname')
        email = request.form.get('email')
        password = request.form.get('password')
        company_type = request.form.get('company_type')  # Get company type from form

        if not companyname or not email or not password or not  company_type:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register1'))


        if company.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register1'))

        try:
            new_company = company(companyname=companyname, email=email, password=password, company_type=company_type)
            db.session.add(new_company)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            logging.info(f"company registered: {companyname} ({email}) with type {company_type}")
            return redirect(url_for('company1'))
        except Exception as e:
            logging.error(f"Error saving company to database: {e}")
            db.session.rollback()
            flash('An error occurred while creating your account. Please try again.', 'danger')
            return redirect(url_for('register1'))

    return render_template('company.html')

# Route to display the profile page
@app.route('/companyprofile/<companyname>')
@login_required
def companyprofile(companyname):
    user = company.query.filter_by(companyname=companyname).first_or_404()
    return render_template('companyprofile.html', user=user)


# Route to edit profile information
@app.route('/edit_companyprofile/<companyname>', methods=['GET', 'POST'])
@login_required
def edit_companyprofile(companyname):
    user = company.query.filter_by(companyname=companyname).first_or_404()

    if request.method == 'POST':
        # Update the user profile fields only if they are provided
        if request.form['email']:
            user.email = request.form['email']
        
        if request.form['city']:
            user.city = request.form['city']
        
        if request.form['location']:
            user.location = request.form['location']
        
        if request.form['bio']:
            user.bio = request.form['bio']

        # Handle profile picture upload (only if a new one is uploaded)
        if 'company_image' in request.files:
            company_image = request.files['company_image']
            if company_image and company_image.filename:
                # Secure the file name
                company_image_filename = secure_filename(company_image.filename)

                # Ensure the upload folder exists
                upload_folder = app.config['UPLOAD_FOLDER']
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)

                # Save the uploaded file
                company_image.save(os.path.join(upload_folder, company_image_filename))

                # Save the filename in the user's profile
                user.company_image = company_image_filename

        # Commit the changes to the database
        db.session.commit()

        # Redirect to the profile page with updated data
        return redirect(url_for('companyprofile', companyname=user.companyname))  # Use `user.companyname`

    return render_template('edit_companyprofile.html', user=user)


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

class apply(db.Model):
    __tablename__ = 'apply' 
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(12),nullable=False)
    email = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(30), nullable=False)
    state= db.Column(db.String(30), nullable=False)
    apply_position = db.Column(db.String(100), nullable=False)
    work_time = db.Column(db.String(100), nullable=False)
    desired_pay = db.Column(db.Float, nullable=True)
    avalible_date=db.Column(db.Date,nullable=False)
    college=db.Column(db.String(150), nullable=True)
    department=db.Column(db.String(150), nullable=True)
    E_start_date=db.Column(db.Date, nullable=True)
    E_end_date=db.Column(db.Date, nullable=True)
    company_name=db.Column(db.String(150), nullable=True)
    position = db.Column(db.String(100), nullable=False)
    ex_start_date=db.Column(db.Date, nullable=False)
    ex_end_date=db.Column(db.Date, nullable=False)
    cv=db.Column(db.String(100),nullable=False)
    cv_cover=db.Column(db.String(100),nullable=False)
    date_posted = db.Column(db.Date,nullable=True )

    def __repr__(self):
        return f"<apply {self.name}>"

# Create the database and table
with app.app_context():
    db.create_all()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif','pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to handle job posting
@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    # if 'loggedin' in session:
        if request.method == 'POST':
            # Validate input fields
            name = request.form['name']
            last_name = request.form['Last_name']
            phone = request.form['phone']
            email = request.form['email']
            city = request.form['city']
            state = request.form['state']
            apply_position = request.form['apply_position']
            work_time = request.form['worktime']
            desired_pay = request.form['desired_pay']
            avalible_date = request.form['avalible_date']
            college = request.form['college']
            department = request.form['department']
            E_start_date = request.form['E_start_date']
            E_end_date = request.form['E_end_date']
            company_name = request.form['company_name']
            position = request.form['position']
            ex_start_date = request.form['ex_start_date']
            ex_end_date = request.form['ex_end_date']

            cv = request.files['cv']
            cv_cover = request.files['cv_cover']

            date_posted = request.form['date_posted']
            # Check required fields
            if not all([name, last_name, phone, email, city, state, apply_position, work_time, desired_pay,
                        avalible_date, college, department, E_start_date, E_end_date, company_name, position,
                        ex_start_date, ex_end_date, cv, cv_cover, date_posted]):
                flash('All fields are required except the logo.', 'error')
                return redirect('/create_post')

            # Handle file uploads and save them
            if cv and allowed_file(cv.filename):
                filename = secure_filename(cv.filename)
                cv_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                cv.save(cv_path)
            if cv_cover and allowed_file(cv_cover.filename):
                filename = secure_filename(cv_cover.filename)
                cv_cover_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                cv_cover.save(cv_cover_path)

            # Save the application in the database
            new_apply = apply(
              
                name=name,
                last_name=last_name,
                phone=phone,
                email=email,
                city=city,
                state=state,
                apply_position=apply_position,
                work_time=work_time,
                desired_pay=desired_pay,
                avalible_date=datetime.strptime(avalible_date, "%Y-%m-%d"),
                college=college,
                department=department,
                E_start_date=datetime.strptime(E_start_date, "%Y-%m-%d") if E_start_date else None,
                E_end_date=datetime.strptime(E_end_date, "%Y-%m-%d") if E_end_date else None,
                company_name=company_name,
                position=position,
                ex_start_date=datetime.strptime(ex_start_date, "%Y-%m-%d"),
                ex_end_date=datetime.strptime(ex_end_date, "%Y-%m-%d"),
                cv=cv_path,
                cv_cover=cv_cover_path,
                date_posted=datetime.strptime(date_posted, "%Y-%m-%d")
            )

            db.session.add(new_apply)
            db.session.commit()  # This saves the record to the database
            flash('Job posted successfully!','success')
            return redirect('/dashboard')

        return render_template('apply.html')  # Make sure this template exists






if __name__ == "__main__":
    app.run(debug=True)
