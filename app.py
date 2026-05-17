from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'ingorala_village_secret_key_2024'

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

# ========== DATABASE MODELS ==========

class Family(db.Model):
    __tablename__ = 'families'
    id = db.Column(db.Integer, primary_key=True)
    surname = db.Column(db.String(50), nullable=False)
    head_name = db.Column(db.String(100), nullable=False)
    members_count = db.Column(db.Integer, default=1)
    contact = db.Column(db.String(15))
    address = db.Column(db.String(200))
    photo = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    members = db.relationship('Member', backref='family', lazy=True, cascade='all, delete-orphan')

class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id', ondelete='CASCADE'))
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    relation = db.Column(db.String(50))
    work = db.Column(db.String(100))
    contact = db.Column(db.String(15))
    gender = db.Column(db.String(10))

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

# ========== ROUTES - PUBLIC ==========

@app.route('/')
def index():
    notices = Notice.query.order_by(Notice.date.desc()).limit(3).all()
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

# ========== ADMIN ROUTES ==========

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == 'ingorala@2024':
            session['admin'] = True
            return redirect('/admin/dashboard')
        else:
            return render_template('admin_login.html', error='પાસવર્ડ ખોટો છે!')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin/login')
    
    families = Family.query.order_by(Family.surname, Family.created_at.desc()).limit(10).all()
    businesses = Business.query.order_by(Business.id.desc()).limit(5).all()
    
    total_families = Family.query.count()
    total_members = Member.query.count()
    total_businesses = Business.query.count()
    
    surname_stats = db.session.query(
        Family.surname, 
        db.func.count(Family.id).label('count')
    ).group_by(Family.surname).order_by(db.func.count(Family.id).desc()).all()
    
    return render_template('admin_dashboard.html', 
                         families=families,
                         businesses=businesses,
                         total_families=total_families,
                         total_members=total_members,
                         total_businesses=total_businesses,
                         surname_stats=surname_stats)

@app.route('/admin/add_family', methods=['POST'])
def add_family():
    if not session.get('admin'):
        return "Unauthorized", 401
    
    try:
        surname_raw = request.form.get('surname', '')
        surname_clean = surname_raw.strip()
        surname_clean = ' '.join(surname_clean.split())
        
        family = Family(
            surname=surname_clean,
            head_name=request.form.get('head_name'),
            members_count=int(request.form.get('members_count', 1)),
            contact=request.form.get('contact'),
            address=request.form.get('address')
        )
        db.session.add(family)
        db.session.flush()
        
        members_data = request.form.get('members_data', '[]')
        members = json.loads(members_data)
        
        for member in members:
            # Safe age conversion
            age_value = member.get('age')
            if age_value and str(age_value).strip():
                try:
                    age_int = int(str(age_value).strip())
                except ValueError:
                    age_int = None
            else:
                age_int = None
            
            new_member = Member(
                family_id=family.id,
                name=member.get('name'),
                age=age_int,
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

@app.route('/admin/delete_family/<int:id>')
def delete_family(id):
    if not session.get('admin'):
        return redirect('/admin/login')
    
    family = Family.query.get_or_404(id)
    db.session.delete(family)
    db.session.commit()
    return redirect('/admin/dashboard')

@app.route('/admin/add_business', methods=['POST'])
def add_business():
    if not session.get('admin'):
        return "Unauthorized", 401
    
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
        return redirect('/admin/dashboard')
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

@app.route('/admin/delete_business/<int:id>')
def delete_business(id):
    if not session.get('admin'):
        return redirect('/admin/login')
    
    business = Business.query.get_or_404(id)
    db.session.delete(business)
    db.session.commit()
    return redirect('/admin/dashboard')

@app.route('/admin/add_notice', methods=['POST'])
def add_notice():
    if not session.get('admin'):
        return "Unauthorized", 401
    
    try:
        notice = Notice(
            title=request.form.get('title'),
            content=request.form.get('content')
        )
        db.session.add(notice)
        db.session.commit()
        return redirect('/admin/dashboard')
    except Exception as e:
        db.session.commit()
        return f"Error: {str(e)}", 500

# ========== WORK (વ્યવસાય) BASED FILTER ==========

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
            'age': member.age,
            'contact': member.contact,
            'family_id': member.family_id,
            'family_head': family.head_name if family else '',
            'family_surname': family.surname if family else ''
        })
    
    return render_template('work_detail.html', work=work_name, people=people_data, total=len(people_data))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)