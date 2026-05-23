from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import json
import os
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = 'ingorala_village_secret_key_2024'

# ========== SESSION CONFIGURATION - 30 DAYS ==========
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

# ========== DATABASE CONFIGURATION ==========
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_sOe3yinBHG5k@ep-polished-truth-apa48k4z-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 5,
    'pool_recycle': 300,
    'pool_pre_ping': True
}

db = SQLAlchemy(app)

# ========== HELPER FUNCTION ==========
def calculate_age(born):
    if born:
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return None

# ========== DATABASE MODELS ==========

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Family(db.Model):
    __tablename__ = 'families'
    id = db.Column(db.Integer, primary_key=True)
    surname = db.Column(db.String(50), nullable=False)
    head_name = db.Column(db.String(100), nullable=False)
    members_count = db.Column(db.Integer, default=1)
    contact = db.Column(db.String(15))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    photo = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='SET NULL'))
    
    members = db.relationship('Member', backref='family', lazy=True, cascade='all, delete-orphan')
    admin = db.relationship('Admin', backref='families')

class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id', ondelete='CASCADE'))
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date)
    relation = db.Column(db.String(50))
    work = db.Column(db.String(100))
    contact = db.Column(db.String(15))
    gender = db.Column(db.String(10))

    @property
    def age(self):
        if self.dob:
            today = date.today()
            return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
        return None

class Business(db.Model):
    __tablename__ = 'businesses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    contact = db.Column(db.String(15))
    address = db.Column(db.String(200))
    timings = db.Column(db.String(100))
    photo = db.Column(db.String(300))

class Gallery(db.Model):
    __tablename__ = 'gallery'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    image_url = db.Column(db.String(300), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notice(db.Model):
    __tablename__ = 'notices'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='SET NULL'))
    admin_name = db.Column(db.String(100))
    
    admin = db.relationship('Admin', backref='notices')

class Work(db.Model):
    __tablename__ = 'works'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ========== ROUTES - PUBLIC ==========

@app.route('/')
def index():
    notices = Notice.query.order_by(Notice.date.desc()).limit(5).all()
    total_families = Family.query.count()
    total_businesses = Business.query.count()
    total_members = Member.query.count()
    
    return render_template('index.html', 
                         notices=notices,
                         total_families=total_families,
                         total_businesses=total_businesses,
                         total_members=total_members)

@app.route('/families')
def families():
    search = request.args.get('search', '')
    surname_filter = request.args.get('surname', '')
    
    query = Family.query
    
    if surname_filter:
        surname_filter = surname_filter.strip()
        query = query.filter(Family.surname == surname_filter)
    
    if search and search.strip():
        query = query.filter(Family.head_name.contains(search.strip()))
    
    all_families = query.order_by(Family.surname, Family.head_name).all()
    
    surnames_with_count = db.session.query(
        Family.surname, 
        db.func.count(Family.id).label('count')
    ).group_by(Family.surname).order_by(db.desc('count')).all()
    
    surnames = [{'name': s[0], 'count': s[1]} for s in surnames_with_count]
    
    return render_template('families.html', 
                         families=all_families, 
                         surnames=surnames,
                         current_surname=surname_filter,
                         search=search)

@app.route('/family/<int:id>')
def family_detail(id):
    family = Family.query.get_or_404(id)
    members = Member.query.filter_by(family_id=id).all()
    return render_template('family_detail.html', family=family, members=members)

@app.route('/businesses')
def businesses():
    cat = request.args.get('category', '')
    if cat:
        all_businesses = Business.query.filter_by(type=cat).all()
    else:
        all_businesses = Business.query.all()
    
    categories = db.session.query(Business.type).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('businesses.html', businesses=all_businesses, categories=categories)

@app.route('/gallery')
def gallery():
    cat = request.args.get('category', '')
    if cat:
        images = Gallery.query.filter_by(category=cat).all()
    else:
        images = Gallery.query.all()
    
    categories = ['મંદિર', 'તળાવ', 'શાળા', 'ખેતી', 'સમારોહ', 'અન્ય']
    return render_template('gallery.html', images=images, categories=categories)

@app.route('/works')
def works():
    works_with_count = db.session.query(
        Member.work,
        db.func.count(Member.id).label('count')
    ).filter(Member.work != '', Member.work.isnot(None)).group_by(Member.work).order_by(db.desc('count')).all()
    
    works = [{'name': w[0], 'count': w[1]} for w in works_with_count]
    total_people = Member.query.count()
    
    return render_template('works.html', works=works, total_people=total_people)

@app.route('/work/<work_name>')
def work_detail(work_name):
    members = Member.query.filter(Member.work == work_name).all()
    
    people_data = []
    for member in members:
        family = Family.query.get(member.family_id)
        people_data.append({
            'id': member.id,
            'name': member.name,
            'dob': member.dob,
            'age': member.age,
            'contact': member.contact,
            'family_id': member.family_id,
            'family_head': family.head_name if family else '',
            'family_surname': family.surname if family else ''
        })
    
    return render_template('work_detail.html', work=work_name, people=people_data, total=len(people_data))

# ========== ADMIN AUTH ROUTES ==========

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_id'):
        return redirect('/admin/dashboard')
    
    if request.method == 'GET':
        session.clear()
    
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(mobile=mobile).first()
        if admin and admin.password == password:
            session.clear()
            session.permanent = True
            session['admin_id'] = admin.id
            session['admin_name'] = admin.name
            session['admin_mobile'] = admin.mobile
            return redirect('/admin/dashboard')
        else:
            return render_template('admin_login.html', error='મોબાઇલ નંબર અથવા પાસવર્ડ ખોટો છે!')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/')

# ========== SESSION CHECK MIDDLEWARE ==========
@app.before_request
def check_session():
    public_routes = ['admin_login', 'static', 'index', 'families', 'family_detail', 
                     'businesses', 'gallery', 'works', 'work_detail']
    
    if request.endpoint in public_routes:
        return None
    
    if request.endpoint and request.endpoint.startswith('admin') and request.endpoint != 'admin_login':
        if not session.get('admin_id'):
            return redirect('/admin/login')
        session.permanent = True
    
    if request.endpoint and request.endpoint.startswith('superadmin'):
        if not session.get('admin_id'):
            return redirect('/admin/login')
        
        admin = Admin.query.get(session.get('admin_id'))
        if not admin or admin.mobile != 'admin':
            return "Unauthorized: Only Super Admin can access this page", 401
    
    return None

# ========== SUPER ADMIN ROUTES ==========

@app.route('/superadmin/admins')
def superadmin_admins():
    admins = Admin.query.all()
    return render_template('superadmin_admins.html', admins=admins)

@app.route('/superadmin/add_admin', methods=['POST'])
def superadmin_add_admin():
    try:
        new_admin = Admin(
            name=request.form.get('name'),
            mobile=request.form.get('mobile'),
            password=request.form.get('password')
        )
        db.session.add(new_admin)
        db.session.commit()
        return redirect('/superadmin/admins')
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

@app.route('/superadmin/delete_admin/<int:id>')
def superadmin_delete_admin(id):
    admin_to_delete = Admin.query.get(id)
    if admin_to_delete.mobile == 'admin':
        return "Cannot delete Super Admin", 400
    
    db.session.delete(admin_to_delete)
    db.session.commit()
    return redirect('/superadmin/admins')

# ========== SUPER ADMIN BUSINESS ROUTES ==========

@app.route('/superadmin/businesses')
def superadmin_businesses():
    businesses = Business.query.order_by(Business.id.desc()).all()
    return render_template('superadmin_businesses.html', businesses=businesses)

@app.route('/superadmin/add_business', methods=['POST'])
def superadmin_add_business():
    try:
        business = Business(
            name=request.form.get('name'),
            owner=request.form.get('owner'),
            type=request.form.get('type'),
            contact=request.form.get('contact'),
            address=request.form.get('address'),
            timings=request.form.get('timings')
        )
        db.session.add(business)
        db.session.commit()
        return redirect('/superadmin/businesses')
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

@app.route('/superadmin/edit_business/<int:id>', methods=['GET', 'POST'])
def superadmin_edit_business(id):
    business = Business.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            business.name = request.form.get('name')
            business.owner = request.form.get('owner')
            business.type = request.form.get('type')
            business.contact = request.form.get('contact')
            business.address = request.form.get('address')
            business.timings = request.form.get('timings')
            db.session.commit()
            return redirect('/superadmin/businesses')
        except Exception as e:
            db.session.rollback()
            return f"Error: {str(e)}", 500
    
    return render_template('superadmin_edit_business.html', business=business)

@app.route('/superadmin/delete_business/<int:id>')
def superadmin_delete_business(id):
    business = Business.query.get_or_404(id)
    db.session.delete(business)
    db.session.commit()
    return redirect('/superadmin/businesses')

# ========== SUPER ADMIN WORK ROUTES ==========

@app.route('/superadmin/works')
def superadmin_works():
    works = Work.query.order_by(Work.name).all()
    return render_template('superadmin_works.html', works=works)

@app.route('/superadmin/add_work', methods=['POST'])
def superadmin_add_work():
    try:
        work_name = request.form.get('name').strip()
        if work_name:
            existing = Work.query.filter_by(name=work_name).first()
            if not existing:
                new_work = Work(name=work_name)
                db.session.add(new_work)
                db.session.commit()
        return redirect('/superadmin/works')
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

@app.route('/superadmin/delete_work/<int:id>')
def superadmin_delete_work(id):
    work = Work.query.get_or_404(id)
    db.session.delete(work)
    db.session.commit()
    return redirect('/superadmin/works')

# ========== SUPER ADMIN CITY ROUTES ==========

@app.route('/superadmin/cities')
def superadmin_cities():
    cities = City.query.order_by(City.name).all()
    return render_template('superadmin_cities.html', cities=cities)

@app.route('/superadmin/add_city', methods=['POST'])
def superadmin_add_city():
    try:
        city_name = request.form.get('name').strip()
        if city_name:
            existing = City.query.filter_by(name=city_name).first()
            if not existing:
                new_city = City(name=city_name)
                db.session.add(new_city)
                db.session.commit()
        return redirect('/superadmin/cities')
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

@app.route('/superadmin/delete_city/<int:id>')
def superadmin_delete_city(id):
    city = City.query.get_or_404(id)
    db.session.delete(city)
    db.session.commit()
    return redirect('/superadmin/cities')

# ========== REGULAR ADMIN DASHBOARD ==========

@app.route('/admin/dashboard')
def admin_dashboard():
    admin_id = session.get('admin_id')
    admin_name = session.get('admin_name')
    admin_mobile = session.get('admin_mobile')
    
    families = Family.query.filter_by(admin_id=admin_id).order_by(Family.created_at.desc()).all()
    notices = Notice.query.order_by(Notice.date.desc()).limit(20).all()
    works = Work.query.order_by(Work.name).all()
    cities = City.query.order_by(City.name).all()  # 👈 Get cities
    
    total_families = len(families)
    total_members = Member.query.join(Family).filter(Family.admin_id == admin_id).count()
    total_businesses = Business.query.count()
    
    return render_template('admin_dashboard.html', 
                         families=families,
                         notices=notices,
                         works=works,
                         cities=cities,  # 👈 Pass cities to template
                         total_families=total_families,
                         total_members=total_members,
                         total_businesses=total_businesses,
                         admin_name=admin_name,
                         admin_mobile=admin_mobile)

@app.route('/admin/add_family', methods=['POST'])
def add_family():
    if not session.get('admin_id'):
        return "Unauthorized", 401
    
    try:
        surname_raw = request.form.get('surname', '')
        surname_clean = surname_raw.strip()
        surname_clean = ' '.join(surname_clean.split())
        
        # Handle city - if "અન્ય" selected, use city_other value
        city_value = request.form.get('city')
        if city_value == 'અન્ય':
            city_value = request.form.get('city_other', '').strip()
            # Optional: Save new city to cities table
            if city_value:
                existing_city = City.query.filter_by(name=city_value).first()
                if not existing_city:
                    new_city = City(name=city_value)
                    db.session.add(new_city)
                    db.session.commit()
        
        family = Family(
            surname=surname_clean,
            head_name=request.form.get('head_name'),
            members_count=int(request.form.get('members_count', 1)),
            contact=request.form.get('contact'),
            address=request.form.get('address'),
            city=city_value,
            admin_id=session['admin_id']
        )
        db.session.add(family)
        db.session.flush()
        
        # Rest of member saving code...
        members_data = request.form.get('members_data', '[]')
        members = json.loads(members_data)
        
        for member in members:
            dob_value = member.get('dob')
            dob_date = None
            if dob_value and dob_value.strip():
                try:
                    dob_date = datetime.strptime(dob_value.strip(), '%Y-%m-%d').date()
                except ValueError:
                    dob_date = None
            
            new_member = Member(
                family_id=family.id,
                name=member.get('name'),
                dob=dob_date,
                contact=member.get('contact'),
                gender=member.get('gender'),
                relation=member.get('relation'),
                work=member.get('work')
            )
            db.session.add(new_member)
        
        family.members_count = len(members)
        db.session.commit()
        return redirect('/admin/dashboard')
    
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

@app.route('/admin/edit_family/<int:id>', methods=['GET', 'POST'])
def edit_family(id):
    family = Family.query.get_or_404(id)
    
    if family.admin_id != session.get('admin_id'):
        return "તમે આ પરિવારમાં ફેરફાર કરી શકતા નથી.", 403
    
    if request.method == 'POST':
        try:
            # Handle city - if "અન્ય" selected, use city_other value
            city_value = request.form.get('city')
            if city_value == 'અન્ય':
                city_value = request.form.get('city_other', '').strip()
                # Optional: Save new city to cities table
                if city_value:
                    existing_city = City.query.filter_by(name=city_value).first()
                    if not existing_city:
                        new_city = City(name=city_value)
                        db.session.add(new_city)
                        db.session.commit()
            
            family.surname = request.form.get('surname')
            family.head_name = request.form.get('head_name')
            family.contact = request.form.get('contact')
            family.address = request.form.get('address')
            family.city = city_value
            db.session.commit()
            return redirect('/admin/dashboard')
        except Exception as e:
            db.session.rollback()
            return f"Error: {str(e)}", 500
    
    members = Member.query.filter_by(family_id=id).all()
    works = Work.query.order_by(Work.name).all()
    cities = City.query.order_by(City.name).all()
    return render_template('edit_family.html', family=family, members=members, works=works, cities=cities)

@app.route('/admin/delete_family/<int:id>')
def delete_family(id):
    family = Family.query.get_or_404(id)
    
    if family.admin_id != session.get('admin_id'):
        return "તમે આ પરિવારને ડિલીટ કરી શકતા નથી.", 403
    
    db.session.delete(family)
    db.session.commit()
    return redirect('/admin/dashboard')

# ========== MEMBER MANAGEMENT ROUTES ==========

@app.route('/admin/add_member/<int:family_id>', methods=['POST'])
def add_member(family_id):
    family = Family.query.get_or_404(family_id)
    if family.admin_id != session.get('admin_id'):
        return "Unauthorized", 403
    
    try:
        dob_value = request.form.get('dob')
        dob_date = None
        if dob_value and dob_value.strip():
            try:
                dob_date = datetime.strptime(dob_value.strip(), '%Y-%m-%d').date()
            except ValueError:
                dob_date = None
        
        work = request.form.get('work')
        if work == 'અન્ય':
            work = request.form.get('work_other')
        
        new_member = Member(
            family_id=family_id,
            name=request.form.get('name'),
            dob=dob_date,
            contact=request.form.get('contact'),
            gender=request.form.get('gender'),
            relation=request.form.get('relation'),
            work=work
        )
        db.session.add(new_member)
        
        family.members_count = Member.query.filter_by(family_id=family_id).count()
        db.session.commit()
        return redirect(f'/admin/edit_family/{family_id}')
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

@app.route('/admin/edit_member/<int:member_id>', methods=['POST'])
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)
    family = Family.query.get(member.family_id)
    
    if family.admin_id != session.get('admin_id'):
        return "Unauthorized", 403
    
    try:
        member.name = request.form.get('name')
        member.relation = request.form.get('relation')
        member.contact = request.form.get('contact')
        member.gender = request.form.get('gender')
        
        work = request.form.get('work')
        if work == 'અન્ય':
            work = request.form.get('work_other')
        member.work = work
        
        dob_value = request.form.get('dob')
        if dob_value and dob_value.strip():
            try:
                member.dob = datetime.strptime(dob_value.strip(), '%Y-%m-%d').date()
            except ValueError:
                member.dob = None
        else:
            member.dob = None
        
        db.session.commit()
        return redirect(f'/admin/edit_family/{family.id}')
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

@app.route('/admin/delete_member/<int:member_id>')
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)
    family = Family.query.get(member.family_id)
    
    if family.admin_id != session.get('admin_id'):
        return "Unauthorized", 403
    
    family_id = family.id
    db.session.delete(member)
    
    family.members_count = Member.query.filter_by(family_id=family_id).count()
    db.session.commit()
    
    return redirect(f'/admin/edit_family/{family_id}')

@app.route('/admin/add_notice', methods=['POST'])
def add_notice():
    if not session.get('admin_id'):
        return "Unauthorized", 401
    
    try:
        notice = Notice(
            title=request.form.get('title'),
            content=request.form.get('content'),
            admin_id=session['admin_id'],
            admin_name=session.get('admin_name', 'Unknown Admin')
        )
        db.session.add(notice)
        db.session.commit()
        return redirect('/admin/dashboard')
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

@app.route('/family-form')
def family_form():
    """Printable family data collection form"""
    return render_template('family_form.html')



# ========== WEATHER API CONFIGURATION ==========
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', 'ea6e04b13cf844a04310cf4ef1dd8925')
INGORALA_LAT = 21.448665
INGORALA_LON = 71.505525

@app.route('/api/weather')
def get_weather():
    """Get current weather for Ingorala village"""
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={INGORALA_LAT}&lon={INGORALA_LON}&appid={WEATHER_API_KEY}&units=metric&lang=gu"
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            weather_data = {
                'temp': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'],
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'city': data.get('name', 'ઈંગોરાળા')
            }
            return jsonify(weather_data)
        else:
            return jsonify({'error': 'Unable to fetch weather'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
