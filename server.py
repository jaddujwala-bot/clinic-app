#!/usr/bin/env python3
"""Multi-speciality Clinic Management System (CMS)

Run: python3 server.py
Open: http://localhost:8000
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, sqlite3, os, mimetypes, datetime, uuid, hashlib, hmac, secrets, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, 'clinic.db')

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS departments (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  parent_id TEXT,
  module TEXT DEFAULT 'CMS',
  description TEXT,
  status TEXT DEFAULT 'Active',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patients (
  id TEXT PRIMARY KEY,
  registration_no TEXT UNIQUE,
  name TEXT NOT NULL,
  guardian_name TEXT,
  gender TEXT,
  dob TEXT,
  age INTEGER DEFAULT 0,
  phone TEXT,
  alt_phone TEXT,
  email TEXT,
  address TEXT,
  city TEXT,
  identity_type TEXT,
  identity_no TEXT,
  blood_group TEXT,
  allergies TEXT,
  category TEXT DEFAULT 'General',
  status TEXT DEFAULT 'Active',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS doctors (
  id TEXT PRIMARY KEY,
  doctor_code TEXT UNIQUE,
  name TEXT NOT NULL,
  department_id TEXT,
  department TEXT,
  specialization TEXT,
  designation TEXT,
  phone TEXT,
  email TEXT,
  address TEXT,
  fee REAL DEFAULT 0,
  room TEXT,
  available_days TEXT,
  status TEXT DEFAULT 'Active',
  created_at TEXT NOT NULL,
  FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS employees (
  id TEXT PRIMARY KEY,
  employee_code TEXT UNIQUE,
  name TEXT NOT NULL,
  department_id TEXT,
  department TEXT,
  designation TEXT,
  phone TEXT,
  email TEXT,
  address TEXT,
  status TEXT DEFAULT 'Active',
  created_at TEXT NOT NULL,
  FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS appointments (
  id TEXT PRIMARY KEY,
  appointment_no TEXT UNIQUE,
  patient_id TEXT NOT NULL,
  doctor_id TEXT NOT NULL,
  appt_date TEXT NOT NULL,
  appt_time TEXT NOT NULL,
  visit_type TEXT DEFAULT 'OPD',
  reason TEXT,
  status TEXT DEFAULT 'Scheduled',
  notes TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
  FOREIGN KEY(doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS opd_bills (
  id TEXT PRIMARY KEY,
  bill_no TEXT UNIQUE,
  patient_id TEXT NOT NULL,
  doctor_id TEXT NOT NULL,
  bill_date TEXT NOT NULL,
  doctor_fee REAL DEFAULT 0,
  discount REAL DEFAULT 0,
  tax REAL DEFAULT 0,
  total REAL DEFAULT 0,
  payment_mode TEXT,
  paid REAL DEFAULT 0,
  balance REAL DEFAULT 0,
  status TEXT DEFAULT 'Unpaid',
  symptoms TEXT,
  diagnosis TEXT,
  prescription TEXT,
  advice TEXT,
  follow_up TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT,
  FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
  FOREIGN KEY(doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL,
  linked_doctor_id TEXT,
  linked_employee_id TEXT,
  status TEXT DEFAULT 'Active',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS audit_logs (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  username TEXT,
  role TEXT,
  action TEXT NOT NULL,
  resource TEXT,
  resource_id TEXT,
  details TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pharmacy_settings (
  id TEXT PRIMARY KEY,
  pharmacy_name TEXT, owner_name TEXT, phone TEXT, gst_number TEXT, drug_license TEXT,
  registration_number TEXT, email TEXT, address TEXT, city TEXT, state TEXT, pin_code TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS pharma_units (id TEXT PRIMARY KEY, unit_name TEXT NOT NULL, status TEXT DEFAULT 'Active', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pharma_hsn (id TEXT PRIMARY KEY, hsn_no TEXT NOT NULL, description TEXT, gst REAL DEFAULT 5, status TEXT DEFAULT 'Active', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pharma_manufacturers (id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT DEFAULT 'Active', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pharma_locations (id TEXT PRIMARY KEY, block TEXT, col TEXT, row_no TEXT, status TEXT DEFAULT 'Active', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pharma_suppliers (
  id TEXT PRIMARY KEY, supplier_name TEXT NOT NULL, phone TEXT, contact_person TEXT, email TEXT, gst_number TEXT,
  drug_license TEXT, address TEXT, city TEXT, state TEXT, payment_terms TEXT, status TEXT DEFAULT 'Active', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pharmacy_stock_inwards (
  id TEXT PRIMARY KEY, po_no TEXT UNIQUE, supplier_id TEXT, supplier_name TEXT, invoice_ref TEXT,
  payment_status TEXT DEFAULT 'Pending', status TEXT DEFAULT 'Draft', items TEXT NOT NULL,
  base_amount REAL DEFAULT 0, gst_amount REAL DEFAULT 0, grand_total REAL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pharmacy_stock_items (
  id TEXT PRIMARY KEY, stock_inward_id TEXT, po_no TEXT, invoice_ref TEXT, medicine_name TEXT NOT NULL,
  category TEXT DEFAULT 'Tablet', batch_no TEXT, quantity REAL DEFAULT 0, original_qty REAL DEFAULT 0,
  cost_per_qty REAL DEFAULT 0, selling_price REAL DEFAULT 0, mrp REAL DEFAULT 0, hsn TEXT,
  cgst REAL DEFAULT 2.5, sgst REAL DEFAULT 2.5, expiry_date TEXT, supplier_id TEXT, supplier_name TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pharmacy_invoices (
  id TEXT PRIMARY KEY, invoice_no TEXT UNIQUE, patient_id TEXT, registration_no TEXT, customer_name TEXT NOT NULL,
  contact TEXT, order_date TEXT NOT NULL, payment_status TEXT DEFAULT 'Draft', payment_method TEXT,
  items TEXT NOT NULL, total_qty REAL DEFAULT 0, subtotal REAL DEFAULT 0, discount_percent REAL DEFAULT 0,
  gst_amount REAL DEFAULT 0, grand_total REAL DEFAULT 0, payment REAL DEFAULT 0, received REAL DEFAULT 0,
  remaining REAL DEFAULT 0, status TEXT DEFAULT 'Active', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pharmacy_returns (
  id TEXT PRIMARY KEY, return_no TEXT UNIQUE, invoice_id TEXT, invoice_no TEXT, invoice_date TEXT,
  status TEXT DEFAULT 'Draft', customer_name TEXT, contact TEXT, notes TEXT, items TEXT NOT NULL,
  subtotal REAL DEFAULT 0, discount_percent REAL DEFAULT 0, gst_amount REAL DEFAULT 0, refund_amount REAL DEFAULT 0,
  refund_status TEXT DEFAULT 'Pending', stock_restored TEXT DEFAULT 'No', return_date TEXT NOT NULL, created_at TEXT NOT NULL
);
"""

TABLES = {
    'patients': {'prefix':'pat', 'fields':['registration_no','name','guardian_name','gender','dob','age','phone','alt_phone','email','address','city','identity_type','identity_no','blood_group','allergies','category','status']},
    'doctors': {'prefix':'doc', 'fields':['doctor_code','name','department_id','department','specialization','designation','phone','email','address','fee','room','available_days','status']},
    'employees': {'prefix':'emp', 'fields':['employee_code','name','department_id','department','designation','phone','email','address','status']},
    'departments': {'prefix':'dep', 'fields':['name','parent_id','module','description','status']},
    'appointments': {'prefix':'apt', 'fields':['appointment_no','patient_id','doctor_id','appt_date','appt_time','visit_type','reason','status','notes']},
    'opd_bills': {'prefix':'opd', 'fields':['bill_no','patient_id','doctor_id','bill_date','doctor_fee','discount','tax','total','payment_mode','paid','balance','status','symptoms','diagnosis','prescription','advice','follow_up']},
    'pharma_units': {'prefix':'unit', 'fields':['unit_name','status']},
    'pharma_hsn': {'prefix':'hsn', 'fields':['hsn_no','description','gst','status']},
    'pharma_manufacturers': {'prefix':'mfg', 'fields':['name','status']},
    'pharma_locations': {'prefix':'loc', 'fields':['block','col','row_no','status']},
    'pharma_suppliers': {'prefix':'sup', 'fields':['supplier_name','phone','contact_person','email','gst_number','drug_license','address','city','state','payment_terms','status']},
    'pharmacy_stock_inwards': {'prefix':'po', 'fields':['po_no','supplier_id','supplier_name','invoice_ref','payment_status','status','items','base_amount','gst_amount','grand_total']},
    'pharmacy_stock_items': {'prefix':'stk', 'fields':['stock_inward_id','po_no','invoice_ref','medicine_name','category','batch_no','quantity','original_qty','cost_per_qty','selling_price','mrp','hsn','cgst','sgst','expiry_date','supplier_id','supplier_name']},
    'pharmacy_invoices': {'prefix':'pinv', 'fields':['invoice_no','patient_id','registration_no','customer_name','contact','order_date','payment_status','payment_method','items','total_qty','subtotal','discount_percent','gst_amount','grand_total','payment','received','remaining','status']},
    'pharmacy_returns': {'prefix':'pret', 'fields':['return_no','invoice_id','invoice_no','invoice_date','status','customer_name','contact','notes','items','subtotal','discount_percent','gst_amount','refund_amount','refund_status','stock_restored','return_date']},
}

ROLE_LABELS = {'admin':'Admin','receptionist':'Receptionist','doctor':'Doctor','pharmacist':'Pharmacist'}
ROLE_TABS = {
    'admin':['dashboard','registration','billing','appointments','reports','admin','pharmacy_dashboard','pharmacy_invoice','pharmacy_returns','pharmacy_sales','pharmacy_po','pharmacy_stock_in','pharmacy_inventory','pharmacy_master','pharmacy_reports','pharmacy_settings'],
    'receptionist':['dashboard','registration','billing','appointments','reports'],
    'doctor':['dashboard','registration','billing','appointments','reports','pharmacy_inventory'],
    'pharmacist':['pharmacy_dashboard','pharmacy_invoice','pharmacy_returns','pharmacy_sales','pharmacy_po','pharmacy_stock_in','pharmacy_inventory','pharmacy_master','pharmacy_reports','pharmacy_settings'],
}
NUM_FIELDS = {'age','fee','doctor_fee','discount','tax','total','paid','balance','gst','base_amount','gst_amount','grand_total','quantity','original_qty','cost_per_qty','selling_price','mrp','cgst','sgst','total_qty','subtotal','discount_percent','payment','received','remaining','refund_amount'}

def now(): return datetime.datetime.now().isoformat(timespec='seconds')
def today(): return datetime.date.today().isoformat()
def new_id(prefix): return f"{prefix}_{uuid.uuid4().hex[:10]}"

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 120000).hex()
    return f'pbkdf2_sha256${salt}${digest}'

def verify_password(password, stored):
    try:
        _algo, salt, digest = stored.split('$', 2)
        test = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 120000).hex()
        return hmac.compare_digest(test, digest)
    except Exception:
        return False

def cookie_value(header, name):
    if not header: return ''
    for part in header.split(';'):
        if '=' in part:
            k, v = part.strip().split('=', 1)
            if k == name: return v
    return ''

def public_user(row):
    if not row: return None
    d = dict(row); d.pop('password_hash', None)
    d['role_label'] = ROLE_LABELS.get(d.get('role'), d.get('role'))
    d['tabs'] = ROLE_TABS.get(d.get('role'), [])
    return d

def audit(user, action, resource='', resource_id='', details=''):
    try:
        con = connect()
        con.execute('INSERT INTO audit_logs VALUES (?,?,?,?,?,?,?,?,?)', (
            new_id('log'), user.get('id') if user else '', user.get('username') if user else '', user.get('role') if user else '',
            action, resource, resource_id, (details or '')[:1000], now()
        ))
        con.commit(); con.close()
    except Exception as e:
        print('audit failed', e)

def can_access(user, method, resource):
    role = user.get('role') if user else ''
    if role == 'admin': return True
    pharmacy_resources = {'pharma_units','pharma_hsn','pharma_manufacturers','pharma_locations','pharma_suppliers','pharmacy_stock_inwards','pharmacy_stock_items','pharmacy_invoices','pharmacy_returns','pharmacy_settings','pharmacy_reports','pharmacy_dashboard'}
    if role == 'pharmacist' and resource in pharmacy_resources:
        return method in {'GET','POST','PUT'}
    if role == 'doctor' and resource in {'pharmacy_stock_items','pharmacy_dashboard'}:
        return method == 'GET'
    if resource == 'reports': return role in {'receptionist','doctor'} and method == 'GET'
    if resource in {'doctors','departments'}: return role in {'receptionist','doctor'} and method == 'GET'
    if role == 'receptionist' and resource in {'patients','appointments','opd_bills'}:
        return method in {'GET','POST','PUT'}
    if role == 'receptionist' and resource == 'pharmacy_stock_items':
        return method == 'GET'
    if role == 'doctor' and resource in {'patients','appointments','opd_bills'}:
        return method in {'GET','PUT'}
    if role == 'pharmacist':
        return resource in {'patients','opd_bills'} and method == 'GET'
    return False

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    return con

def table_cols(con, table):
    return {r['name'] for r in con.execute(f'PRAGMA table_info({table})')}

def ensure_columns(con):
    # Lightweight migration for users who ran the previous starter version.
    additions = {
        'patients': {
            'registration_no':'TEXT','guardian_name':'TEXT','age':'INTEGER DEFAULT 0','alt_phone':'TEXT','city':'TEXT','identity_type':'TEXT','identity_no':'TEXT','category':"TEXT DEFAULT 'General'",'status':"TEXT DEFAULT 'Active'"
        },
        'doctors': {
            'doctor_code':'TEXT','department_id':'TEXT','department':'TEXT','designation':'TEXT','address':'TEXT','status':"TEXT DEFAULT 'Active'"
        },
        'appointments': {'appointment_no':'TEXT','visit_type':"TEXT DEFAULT 'OPD'"},
        'opd_bills': {'updated_at':'TEXT'},
        'users': {'linked_employee_id':'TEXT'},
    }
    for table, cols in additions.items():
        existing = table_cols(con, table)
        for col, decl in cols.items():
            if col not in existing:
                try: con.execute(f'ALTER TABLE {table} ADD COLUMN {col} {decl}')
                except sqlite3.OperationalError: pass

def serial_no(con, table, prefix, col):
    y = datetime.date.today().year
    like = f'{prefix}-{y}-%'
    r = con.execute(f"SELECT {col} FROM {table} WHERE {col} LIKE ? ORDER BY {col} DESC LIMIT 1", (like,)).fetchone()
    n = int(r[col].split('-')[-1]) + 1 if r and r[col] else 1
    return f'{prefix}-{y}-{n:05d}'

def init_db():
    con = connect(); con.executescript(SCHEMA); ensure_columns(con)
    if con.execute('SELECT COUNT(*) c FROM departments').fetchone()['c'] == 0: seed(con)
    seed_users(con)
    seed_pharmacy_data(con)
    # Backfill old starter records, if any.
    for row in con.execute('SELECT id FROM patients WHERE registration_no IS NULL OR registration_no=""').fetchall():
        con.execute('UPDATE patients SET registration_no=? WHERE id=?', (serial_no(con,'patients','CMS','registration_no'), row['id']))
    for row in con.execute('SELECT id FROM doctors WHERE doctor_code IS NULL OR doctor_code=""').fetchall():
        con.execute('UPDATE doctors SET doctor_code=? WHERE id=?', (serial_no(con,'doctors','DOC','doctor_code'), row['id']))
    if 'updated_at' in table_cols(con, 'opd_bills'):
        con.execute('UPDATE opd_bills SET updated_at=COALESCE(updated_at, created_at)')
    con.commit(); con.close()



def seed_pharmacy_data(con):
    ts = now()
    suppliers = [
        ('sup_mediworld','MediWorld Distributors','+91 93000 10001','Sanjay Verma','mediworld@example.com','22ABCDE1234F1Z5','DL-CG-001','Supela Market','Bhilai','Chhattisgarh','30 Days','Active',ts),
        ('sup_healthplus','HealthPlus Pharma','+91 93000 10002','Ritu Sahu','healthplus@example.com','22ABCDE1234F2Z6','DL-CG-002','Power House Road','Bhilai','Chhattisgarh','Cash','Active',ts),
        ('sup_lifecare','LifeCare Medical Supply','+91 93000 10003','Amit Jain','lifecare@example.com','22ABCDE1234F3Z7','DL-CG-003','G.E. Road','Bhilai','Chhattisgarh','15 Days','Active',ts),
    ]
    con.executemany('INSERT OR IGNORE INTO pharma_suppliers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', suppliers)
    stocks = [
        ('stk_para_500','','PO-SEED-001','MH-INV-001','Paracetamol 500mg','Tablet','PCM500-A1',250,250,1.20,2.50,3.00,'3004',2.5,2.5,'2027-12-31','sup_mediworld','MediWorld Distributors',ts),
        ('stk_amox_500','','PO-SEED-001','MH-INV-001','Amoxicillin 500mg','Capsule','AMX500-B1',120,120,4.50,8.00,10.00,'3004',2.5,2.5,'2027-08-31','sup_mediworld','MediWorld Distributors',ts),
        ('stk_cet_10','','PO-SEED-002','MH-INV-002','Cetirizine 10mg','Tablet','CTZ10-C1',180,180,0.80,2.00,2.50,'3004',2.5,2.5,'2027-10-31','sup_healthplus','HealthPlus Pharma',ts),
        ('stk_azith_500','','PO-SEED-002','MH-INV-002','Azithromycin 500mg','Tablet','AZI500-D1',90,90,9.00,16.00,20.00,'3004',2.5,2.5,'2027-09-30','sup_healthplus','HealthPlus Pharma',ts),
        ('stk_pantop_40','','PO-SEED-003','MH-INV-003','Pantoprazole 40mg','Tablet','PAN40-E1',160,160,2.00,5.00,6.00,'3004',2.5,2.5,'2028-01-31','sup_lifecare','LifeCare Medical Supply',ts),
        ('stk_cough_syp','','PO-SEED-003','MH-INV-003','Cough Syrup 100ml','Syrup','CS100-F1',45,45,35.00,65.00,75.00,'3004',2.5,2.5,'2027-06-30','sup_lifecare','LifeCare Medical Supply',ts),
        ('stk_ors','','PO-SEED-004','MH-INV-004','ORS Sachet','Other','ORS-G1',300,300,8.00,15.00,18.00,'3004',2.5,2.5,'2028-03-31','sup_mediworld','MediWorld Distributors',ts),
        ('stk_vitc','','PO-SEED-004','MH-INV-004','Vitamin C 500mg','Tablet','VITC-H1',140,140,1.50,4.00,5.00,'3004',2.5,2.5,'2027-11-30','sup_healthplus','HealthPlus Pharma',ts),
        ('stk_diclo_gel','','PO-SEED-005','MH-INV-005','Diclofenac Gel 30g','Ointment','DICG-I1',35,35,28.00,55.00,65.00,'3004',2.5,2.5,'2027-07-31','sup_lifecare','LifeCare Medical Supply',ts),
        ('stk_salbut_inh','','PO-SEED-005','MH-INV-005','Salbutamol Inhaler','Inhaler','SALB-J1',25,25,110.00,180.00,210.00,'3004',2.5,2.5,'2027-05-31','sup_lifecare','LifeCare Medical Supply',ts),
        ('stk_eye_drop','','PO-SEED-006','MH-INV-006','Lubricant Eye Drops','Drops','EYE-K1',40,40,45.00,85.00,99.00,'3004',2.5,2.5,'2027-04-30','sup_healthplus','HealthPlus Pharma',ts),
        ('stk_insulin','','PO-SEED-006','MH-INV-006','Insulin Injection','Injection','INS-L1',18,18,220.00,320.00,350.00,'3004',2.5,2.5,'2027-03-31','sup_mediworld','MediWorld Distributors',ts),
    ]
    con.executemany('INSERT OR IGNORE INTO pharmacy_stock_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', stocks)

def seed_users(con):
    ts = now()
    defaults = [
        ('usr_admin','admin','admin123','System Administrator','admin','',''),
        ('usr_reception','reception','reception123','Reception User','receptionist','','emp_reena'),
        ('usr_doctor','doctor','doctor123','Doctor User','doctor','doc_anjali',''),
        ('usr_pharmacy','pharmacy','pharmacy123','Pharmacy User','pharmacist','',''),
    ]
    for uid, username, password, full_name, role, linked_doctor_id, linked_employee_id in defaults:
        if con.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone() is None:
            cols = table_cols(con, 'users')
            if 'linked_employee_id' in cols:
                con.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (uid, username, hash_password(password), full_name, role, linked_doctor_id, linked_employee_id, 'Active', ts))
            else:
                con.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?)', (uid, username, hash_password(password), full_name, role, linked_doctor_id, 'Active', ts))

def seed(con):
    ts = now()
    deps = [
        ('dep_gen','General Medicine','', 'CMS','General OPD and physician services','Active',ts),
        ('dep_ped','Pediatrics','', 'CMS','Child care and vaccination','Active',ts),
        ('dep_derm','Dermatology','', 'CMS','Skin and hair clinic','Active',ts),
        ('dep_admin','Administration','', 'CMS','Clinic administration','Active',ts),
        ('dep_recp','Reception','dep_admin', 'CMS','Registration and OPD billing','Active',ts),
    ]
    con.executemany('INSERT OR IGNORE INTO departments VALUES (?,?,?,?,?,?,?)', deps)
    doctors = [
        ('doc_anjali','DOC-2026-00001','Dr. Anjali Mehta','dep_gen','General Medicine','General Physician','Consultant','+91 98765 43210','anjali@clinic.local','Raipur, Chhattisgarh',600,'101','Mon,Tue,Wed,Thu,Fri','Active',ts),
        ('doc_rahul','DOC-2026-00002','Dr. Rahul Shah','dep_ped','Pediatrics','Pediatrician','Consultant','+91 98765 11122','rahul@clinic.local','Raipur, Chhattisgarh',800,'102','Mon,Wed,Fri,Sat','Active',ts),
        ('doc_neha','DOC-2026-00003','Dr. Neha Iyer','dep_derm','Dermatology','Dermatologist','Consultant','+91 98765 22233','neha@clinic.local','Raipur, Chhattisgarh',1000,'103','Tue,Thu,Sat','Active',ts),
    ]
    con.executemany('INSERT OR IGNORE INTO doctors VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', doctors)
    emps = [
        ('emp_reena','EMP-2026-00001','Reena Sahu','dep_recp','Reception','Receptionist','+91 90000 10001','reena@clinic.local','Raipur','Active',ts),
        ('emp_arvind','EMP-2026-00002','Arvind Verma','dep_admin','Administration','Admin Manager','+91 90000 10002','arvind@clinic.local','Raipur','Active',ts),
    ]
    con.executemany('INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?,?,?,?,?,?,?)', emps)
    patients = [
        ('pat_aisha','CMS-2026-00001','Aisha Khan','Imran Khan','Female','1992-05-14',34,'+91 90000 12345','','aisha@example.com','Raipur','Raipur','Aadhaar','XXXX-1234','B+','Penicillin','General','Active',ts),
        ('pat_rohan','CMS-2026-00002','Rohan Desai','Mahesh Desai','Male','1987-11-02',38,'+91 90000 23456','','rohan@example.com','Raipur','Raipur','PAN','ABCDE1234F','O+','None','General','Active',ts),
        ('pat_maya','CMS-2026-00003','Maya Nair','Kavita Nair','Female','2018-08-19',7,'+91 90000 34567','','maya@example.com','Raipur','Raipur','Birth Certificate','BC-9981','A+','Dust allergy','General','Active',ts),
    ]
    con.executemany('INSERT OR IGNORE INTO patients VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', patients)
    appts = [
        ('apt_001','APT-2026-00001','pat_aisha','doc_anjali',today(),'10:00','OPD','Fever and body ache','Scheduled','',ts),
        ('apt_002','APT-2026-00002','pat_maya','doc_rahul',today(),'11:30','OPD','Vaccination follow-up','Checked In','',ts),
    ]
    con.executemany('INSERT OR IGNORE INTO appointments VALUES (?,?,?,?,?,?,?,?,?,?,?)', appts)
    prev_date = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    opd_bills = [
        ('opd_demo_001','OPD-2026-00001','pat_rohan','doc_anjali',prev_date,600,0,0,600,'Cash',600,0,'Paid','Headache and weakness','Migraine suspected','Pain relief medicine as advised','Avoid stress and follow up if pain continues','',ts,ts),
        ('opd_demo_002','OPD-2026-00002','pat_aisha','doc_neha',prev_date,1000,100,0,900,'UPI',500,400,'Partial Paid','Skin rash','Allergic dermatitis','Antihistamine and topical cream','Avoid known allergens','',ts,ts),
    ]
    con.executemany('INSERT OR IGNORE INTO opd_bills VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', opd_bills)

def rows(sql, params=()):
    con = connect(); data = [dict(r) for r in con.execute(sql, params).fetchall()]; con.close(); return data

def one(sql, params=()):
    con = connect(); r = con.execute(sql, params).fetchone(); con.close(); return dict(r) if r else None

def list_table(table):
    if table == 'appointments':
        return rows('''SELECT a.*, p.registration_no, p.name patient_name, p.gender patient_gender, d.name doctor_name, d.specialization, d.department, d.fee
                       FROM appointments a JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id
                       ORDER BY a.appt_date DESC, a.appt_time DESC''')
    if table == 'opd_bills':
        return rows('''SELECT b.*, p.registration_no, p.name patient_name, p.age patient_age, p.gender patient_gender, p.phone patient_phone,
                              d.name doctor_name, d.specialization, d.department, d.designation
                       FROM opd_bills b JOIN patients p ON p.id=b.patient_id JOIN doctors d ON d.id=b.doctor_id
                       ORDER BY b.bill_date DESC, b.created_at DESC''')
    if table == 'doctors':
        return rows('SELECT * FROM doctors ORDER BY status ASC, name ASC')
    if table == 'employees':
        return rows('SELECT * FROM employees ORDER BY status ASC, name ASC')
    if table == 'departments':
        return rows('''SELECT d.*, p.name parent_name FROM departments d LEFT JOIN departments p ON p.id=d.parent_id ORDER BY d.name ASC''')
    if table == 'patients':
        return rows('SELECT * FROM patients ORDER BY created_at DESC')
    return rows(f'SELECT * FROM {table}')

def make_defaults(table, data):
    con = connect()
    try:
        if table == 'patients' and not data.get('registration_no'):
            data['registration_no'] = serial_no(con,'patients','CMS','registration_no')
        if table == 'doctors' and not data.get('doctor_code'):
            data['doctor_code'] = serial_no(con,'doctors','DOC','doctor_code')
        if table == 'employees' and not data.get('employee_code'):
            data['employee_code'] = serial_no(con,'employees','EMP','employee_code')
        if table == 'appointments' and not data.get('appointment_no'):
            data['appointment_no'] = serial_no(con,'appointments','APT','appointment_no')
        if table == 'opd_bills':
            if not data.get('bill_no'): data['bill_no'] = serial_no(con,'opd_bills','OPD','bill_no')
            fee = float(data.get('doctor_fee') or 0); disc = float(data.get('discount') or 0); tax = float(data.get('tax') or 0); paid = float(data.get('paid') or 0)
            total = float(data.get('total') or max(0, fee - disc + tax))
            bal = max(0, total - paid)
            data['total'], data['balance'] = total, bal
            data['status'] = 'Paid' if paid >= total and total > 0 else ('Partial Paid' if paid > 0 else 'Unpaid')
        if table == 'pharmacy_stock_inwards':
            if not data.get('po_no'): data['po_no'] = serial_no(con,'pharmacy_stock_inwards','PO','po_no')
            data = calc_stock_inward(data)
        if table == 'pharmacy_invoices':
            if not data.get('invoice_no'): data['invoice_no'] = serial_no(con,'pharmacy_invoices','PHINV','invoice_no')
            if not data.get('order_date'): data['order_date'] = today()
            data = calc_pharmacy_invoice(data)
        if table == 'pharmacy_returns':
            if not data.get('return_no'): data['return_no'] = serial_no(con,'pharmacy_returns','RET','return_no')
            if not data.get('return_date'): data['return_date'] = today()
            items = data.get('items')
            if not isinstance(items, str): data['items'] = json.dumps(items or [])
        return data
    finally: con.close()

def reports(params):
    date = params.get('date', [today()])[0] or today()
    con = connect()
    result = {
        'date': date,
        'total_patients': con.execute('SELECT COUNT(*) c FROM patients').fetchone()['c'],
        'active_doctors': con.execute("SELECT COUNT(*) c FROM doctors WHERE status='Active'").fetchone()['c'],
        'opd_today': con.execute('SELECT COUNT(*) c FROM opd_bills WHERE bill_date=?', (date,)).fetchone()['c'],
        'appointments_today': con.execute('SELECT COUNT(*) c FROM appointments WHERE appt_date=?', (date,)).fetchone()['c'],
        'gender_opd': [dict(r) for r in con.execute('''SELECT p.gender, COUNT(*) count FROM opd_bills b JOIN patients p ON p.id=b.patient_id WHERE b.bill_date=? GROUP BY p.gender''', (date,)).fetchall()],
        'upcoming_appointments': [dict(r) for r in con.execute('''SELECT a.*, p.registration_no, p.name patient_name, d.name doctor_name, d.specialization FROM appointments a JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id WHERE a.appt_date >= ? AND a.status != 'Cancelled' ORDER BY a.appt_date ASC, a.appt_time ASC LIMIT 10''', (date,)).fetchall()],
        'daily_opd': [dict(r) for r in con.execute('''SELECT b.*, p.registration_no, p.name patient_name, p.gender, d.name doctor_name, d.specialization FROM opd_bills b JOIN patients p ON p.id=b.patient_id JOIN doctors d ON d.id=b.doctor_id WHERE b.bill_date=? ORDER BY b.created_at DESC''', (date,)).fetchall()],
        'doctor_wise_opd': [dict(r) for r in con.execute('''SELECT d.name doctor_name, d.specialization, COUNT(b.id) opd_count, COALESCE(SUM(b.total),0) total_amount, COALESCE(SUM(b.paid),0) paid_amount FROM doctors d LEFT JOIN opd_bills b ON b.doctor_id=d.id AND b.bill_date=? GROUP BY d.id ORDER BY opd_count DESC''', (date,)).fetchall()],
        'daily_registrations': [dict(r) for r in con.execute('SELECT * FROM patients WHERE date(created_at)=? ORDER BY created_at DESC', (date,)).fetchall()],
        'daily_appointments': [dict(r) for r in con.execute('''SELECT a.*, p.registration_no, p.name patient_name, d.name doctor_name FROM appointments a JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id WHERE a.appt_date=? ORDER BY a.appt_time ASC''', (date,)).fetchall()],
        'daily_collection': con.execute('SELECT COALESCE(SUM(total),0) billed, COALESCE(SUM(paid),0) collected, COALESCE(SUM(balance),0) balance FROM opd_bills WHERE bill_date=?', (date,)).fetchone(),
    }
    result['daily_collection'] = dict(result['daily_collection'])
    con.close(); return result


def jloads(value, default=None):
    try: return json.loads(value or '[]')
    except Exception: return default if default is not None else []

def pharmacy_dashboard(params=None):
    params = params or {}
    date = params.get('date', [today()])[0] if isinstance(params, dict) else today()
    con = connect()
    soon = (datetime.date.today()+datetime.timedelta(days=60)).isoformat()
    week_start = (datetime.date.today()-datetime.timedelta(days=6)).isoformat()
    result = {
        'date': date,
        'today_revenue': con.execute("SELECT COALESCE(SUM(received),0) v FROM pharmacy_invoices WHERE order_date=? AND payment_status!='Draft'", (date,)).fetchone()['v'],
        'today_refund': con.execute("SELECT COALESCE(SUM(refund_amount),0) v FROM pharmacy_returns").fetchone()['v'],
        'active_invoices': con.execute("SELECT COUNT(*) c FROM pharmacy_invoices WHERE order_date=? AND status='Active'", (date,)).fetchone()['c'],
        'low_stock_items': con.execute('SELECT COUNT(*) c FROM pharmacy_stock_items WHERE quantity>0 AND quantity<=10').fetchone()['c'],
        'soon_to_expire': con.execute('SELECT COUNT(*) c FROM pharmacy_stock_items WHERE quantity>0 AND expiry_date<=?', (soon,)).fetchone()['c'],
        'weekly_sales': [dict(r) for r in con.execute("SELECT order_date date, COALESCE(SUM(grand_total),0) total FROM pharmacy_invoices WHERE order_date>=? GROUP BY order_date ORDER BY order_date", (week_start,)).fetchall()],
        'low_stock_by_category': [dict(r) for r in con.execute('SELECT category, COUNT(*) count FROM pharmacy_stock_items WHERE quantity>0 AND quantity<=10 GROUP BY category').fetchall()],
        'recent_invoices': [dict(r) for r in con.execute('SELECT * FROM pharmacy_invoices ORDER BY created_at DESC LIMIT 10').fetchall()],
        'alerts': [dict(r) for r in con.execute('SELECT medicine_name, batch_no, quantity, expiry_date, category FROM pharmacy_stock_items WHERE quantity<=10 OR expiry_date<=? ORDER BY expiry_date ASC LIMIT 20', (soon,)).fetchall()],
    }
    con.close(); return result

def pharmacy_reports(params):
    start = params.get('start', [today()])[0] or today(); end = params.get('end', [today()])[0] or today()
    con = connect(); month_start = datetime.date.today().replace(day=1).isoformat()
    result = {
        'start': start, 'end': end,
        'today_sales': con.execute("SELECT COALESCE(SUM(grand_total),0) v FROM pharmacy_invoices WHERE order_date=? AND payment_status!='Draft'", (today(),)).fetchone()['v'],
        'monthly_revenue': con.execute("SELECT COALESCE(SUM(grand_total),0) v FROM pharmacy_invoices WHERE order_date>=? AND payment_status!='Draft'", (month_start,)).fetchone()['v'],
        'items_sold_monthly': con.execute("SELECT COALESCE(SUM(total_qty),0) v FROM pharmacy_invoices WHERE order_date>=? AND payment_status!='Draft'", (month_start,)).fetchone()['v'],
        'avg_transaction': con.execute("SELECT COALESCE(AVG(grand_total),0) v FROM pharmacy_invoices WHERE order_date BETWEEN ? AND ? AND payment_status!='Draft'", (start,end)).fetchone()['v'],
        'daily_sales': [dict(r) for r in con.execute("SELECT order_date date, COALESCE(SUM(grand_total),0) total FROM pharmacy_invoices WHERE order_date BETWEEN ? AND ? GROUP BY order_date", (start,end)).fetchall()],
        'stock_by_category': [dict(r) for r in con.execute('SELECT category, COALESCE(SUM(quantity),0) qty FROM pharmacy_stock_items GROUP BY category').fetchall()],
        'recent_transactions': [dict(r) for r in con.execute("SELECT invoice_no, customer_name customer, order_date date, grand_total amount, 'Sale' type FROM pharmacy_invoices WHERE order_date BETWEEN ? AND ? ORDER BY created_at DESC LIMIT 20", (start,end)).fetchall()],
        'stock_report': [dict(r) for r in con.execute('SELECT * FROM pharmacy_stock_items ORDER BY medicine_name').fetchall()],
        'expiry_report': [dict(r) for r in con.execute('SELECT * FROM pharmacy_stock_items WHERE quantity>0 ORDER BY expiry_date ASC').fetchall()],
        'gst_report': [dict(r) for r in con.execute('SELECT invoice_no, order_date, customer_name, subtotal, gst_amount, grand_total FROM pharmacy_invoices WHERE order_date BETWEEN ? AND ?', (start,end)).fetchall()],
    }
    con.close(); return result

def pharmacy_settings_get():
    con=connect(); row=con.execute('SELECT * FROM pharmacy_settings LIMIT 1').fetchone();
    if not row:
        con.execute('INSERT INTO pharmacy_settings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', ('phset_1','Clinic Pharmacy','','','','','','','','','','',now()))
        con.commit(); row=con.execute('SELECT * FROM pharmacy_settings LIMIT 1').fetchone()
    con.close(); return dict(row)

def pharmacy_settings_save(data):
    pharmacy_settings_get()
    fields=['pharmacy_name','owner_name','phone','gst_number','drug_license','registration_number','email','address','city','state','pin_code']
    vals=[data.get(f,'') for f in fields]+[now(),'phset_1']
    con=connect(); con.execute(f"UPDATE pharmacy_settings SET {','.join(f+'=?' for f in fields)}, updated_at=? WHERE id=?", vals); con.commit(); con.close()
    return pharmacy_settings_get()

def calc_pharmacy_invoice(data):
    items = data.get('items')
    if isinstance(items, str): items = jloads(items)
    subtotal=gst=qty=0
    for it in items or []:
        q=float(it.get('qty') or it.get('quantity') or 0); rate=float(it.get('rate') or it.get('selling_price') or 0)
        cg=float(it.get('cgst') or 2.5); sg=float(it.get('sgst') or 2.5)
        base=q*rate; tax=base*(cg+sg)/100; total=base+tax
        it['qty']=q; it['rate']=rate; it['cgst']=cg; it['sgst']=sg; it['total']=round(total,2)
        subtotal+=base; gst+=tax; qty+=q
    discp=float(data.get('discount_percent') or 0); discount=subtotal*discp/100
    grand=max(0, subtotal-discount+gst); pay=float(data.get('payment') or data.get('received') or 0)
    remaining = round(max(0, grand-pay), 2)
    data.update({'items':json.dumps(items or []),'total_qty':qty,'subtotal':round(subtotal,2),'gst_amount':round(gst,2),'grand_total':round(grand,2),'received':pay,'remaining':remaining})
    # Always recalculate payment status after editing, except when deliberately saved as Draft.
    if data.get('payment_status') == 'Draft':
        data['payment_status'] = 'Draft'
    else:
        data['payment_status']='Paid' if pay>=grand and grand>0 else ('Partial' if pay>0 else 'Pending')
    return data

def calc_stock_inward(data):
    items=data.get('items')
    if isinstance(items,str): items=jloads(items)
    base=gst=0
    for it in items or []:
        q=float(it.get('quantity') or 0); cost=float(it.get('cost_per_qty') or 0); cg=float(it.get('cgst') or 2.5); sg=float(it.get('sgst') or 2.5)
        line=q*cost; tax=line*(cg+sg)/100; it['quantity']=q; it['cgst']=cg; it['sgst']=sg; it['line_total']=round(line+tax,2); base+=line; gst+=tax
    data.update({'items':json.dumps(items or []),'base_amount':round(base,2),'gst_amount':round(gst,2),'grand_total':round(base+gst,2)})
    return data

def apply_stock_inward(stock_id, data):
    items=jloads(data.get('items'))
    if data.get('status') not in {'Confirmed','Added to Stock'}: return
    con=connect()
    if con.execute('SELECT 1 FROM pharmacy_stock_items WHERE stock_inward_id=?',(stock_id,)).fetchone(): con.close(); return
    for it in items:
        qty=float(it.get('quantity') or 0)
        con.execute('INSERT INTO pharmacy_stock_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            new_id('stk'), stock_id, data.get('po_no',''), data.get('invoice_ref',''), it.get('medicine_name',''), it.get('category','Tablet'), it.get('batch_no',''), qty, qty,
            float(it.get('cost_per_qty') or 0), float(it.get('selling_price') or 0), float(it.get('mrp') or 0), it.get('hsn',''), float(it.get('cgst') or 2.5), float(it.get('sgst') or 2.5), it.get('expiry_date',''), data.get('supplier_id',''), data.get('supplier_name',''), now()
        ))
    con.commit(); con.close()

def deduct_invoice_stock(invoice_id, data):
    if data.get('payment_status') == 'Draft': return
    items=jloads(data.get('items'))
    con=connect()
    for it in items:
        med=it.get('medicine_name') or it.get('medicine') or ''; need=float(it.get('qty') or 0)
        lots=con.execute('SELECT * FROM pharmacy_stock_items WHERE medicine_name=? AND quantity>0 ORDER BY expiry_date ASC, created_at ASC',(med,)).fetchall()
        for lot in lots:
            if need<=0: break
            take=min(need, float(lot['quantity'])); need-=take
            con.execute('UPDATE pharmacy_stock_items SET quantity=? WHERE id=?',(float(lot['quantity'])-take,lot['id']))
    con.commit(); con.close()

def restore_return_stock(return_id, user):
    con=connect(); r=con.execute('SELECT * FROM pharmacy_returns WHERE id=?',(return_id,)).fetchone()
    if not r: con.close(); return {'error':'Return not found'}
    if r['stock_restored']=='Yes': con.close(); return {'ok':True,'message':'Already restored'}
    items=jloads(r['items'])
    for it in items:
        med=it.get('medicine_name') or it.get('medicine') or ''; qty=float(it.get('return_qty') or 0)
        lot=con.execute('SELECT * FROM pharmacy_stock_items WHERE medicine_name=? ORDER BY created_at DESC LIMIT 1',(med,)).fetchone()
        if lot: con.execute('UPDATE pharmacy_stock_items SET quantity=? WHERE id=?',(float(lot['quantity'])+qty,lot['id']))
    con.execute("UPDATE pharmacy_returns SET status='Refunded', refund_status='Paid', stock_restored='Yes' WHERE id=?",(return_id,))
    con.commit(); con.close(); audit(user,'MARK_PAID_RESTORE','pharmacy_returns',return_id); return {'ok':True}


def list_users():
    con = connect()
    sql = """SELECT u.id, u.username, u.full_name, u.role, u.linked_doctor_id,
        COALESCE(u.linked_employee_id,'') linked_employee_id, u.status, u.created_at,
        d.name linked_doctor_name, e.name linked_employee_name
        FROM users u
        LEFT JOIN doctors d ON d.id=u.linked_doctor_id
        LEFT JOIN employees e ON e.id=u.linked_employee_id
        ORDER BY u.created_at DESC"""
    data = [dict(r) for r in con.execute(sql).fetchall()]
    con.close()
    for u in data:
        u['role_label'] = ROLE_LABELS.get(u.get('role'), u.get('role'))
        u['tabs'] = ROLE_TABS.get(u.get('role'), [])
    return data

def create_user(data):
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or 'changeme123'
    if not username: raise ValueError('Username is required')
    role = data.get('role') or 'receptionist'
    if role not in ROLE_LABELS: raise ValueError('Invalid role')
    item_id = new_id('usr')
    con = connect()
    con.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)', (
        item_id, username, hash_password(password), data.get('full_name') or username, role,
        data.get('linked_doctor_id',''), data.get('linked_employee_id',''), data.get('status','Active'), now()
    ))
    con.commit(); con.close()
    return {'id': item_id, 'username': username}

def update_user(user_id, data):
    allowed = ['full_name','role','linked_doctor_id','linked_employee_id','status']
    if 'role' in data and data['role'] not in ROLE_LABELS: raise ValueError('Invalid role')
    fields = [f for f in allowed if f in data]
    if not fields: return {'updated': 0}
    con = connect()
    cur = con.execute(f"UPDATE users SET {','.join(f+'=?' for f in fields)} WHERE id=?", [data[f] for f in fields]+[user_id])
    con.commit(); con.close()
    return {'updated': cur.rowcount}

def reset_user_password(user_id, password):
    if not password or len(password) < 6: raise ValueError('Password must be at least 6 characters')
    con = connect(); cur = con.execute('UPDATE users SET password_hash=? WHERE id=?', (hash_password(password), user_id)); con.commit(); con.close()
    return {'updated': cur.rowcount}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): print('[%s] %s' % (self.log_date_time_string(), fmt % args))
    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def read_json(self):
        length = int(self.headers.get('Content-Length',0)); return json.loads(self.rfile.read(length).decode() or '{}')
    def current_user(self):
        token = cookie_value(self.headers.get('Cookie',''), 'cms_session')
        if not token: return None
        con = connect()
        row = con.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at > ? AND u.status='Active'", (token, now())).fetchone()
        con.close()
        return public_user(row) if row else None
    def require_user(self):
        user = self.current_user()
        if not user:
            self.send_json({'error':'Authentication required'}, 401)
            return None
        return user
    def require_permission(self, user, method, resource):
        if can_access(user, method, resource): return True
        self.send_json({'error':'Permission denied for your role'}, 403)
        return False
    def send_login_json(self, obj, token=None, clear=False, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        if clear:
            self.send_header('Set-Cookie','cms_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0')
        elif token:
            self.send_header('Set-Cookie',f'cms_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800')
        self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        parsed = urlparse(self.path); path = parsed.path
        if path == '/api/me':
            user = self.current_user()
            return self.send_json({'authenticated': bool(user), 'user': user})
        if path == '/api/logout':
            token = cookie_value(self.headers.get('Cookie',''), 'cms_session')
            if token:
                con = connect(); con.execute('DELETE FROM sessions WHERE token=?', (token,)); con.commit(); con.close()
            return self.send_login_json({'ok': True}, clear=True)
        if path in ('/api/users','/api/user_roles'):
            user = self.require_user()
            if not user: return
            if user.get('role') != 'admin': return self.send_json({'error':'Admin access required'}, 403)
            return self.send_json(list_users())
        if path == '/api/pharmacy_dashboard':
            user = self.require_user()
            if not user or not self.require_permission(user, 'GET', 'pharmacy_dashboard'): return
            return self.send_json(pharmacy_dashboard(parse_qs(parsed.query)))
        if path == '/api/pharmacy_reports':
            user = self.require_user()
            if not user or not self.require_permission(user, 'GET', 'pharmacy_reports'): return
            return self.send_json(pharmacy_reports(parse_qs(parsed.query)))
        if path == '/api/pharmacy_settings':
            user = self.require_user()
            if not user or not self.require_permission(user, 'GET', 'pharmacy_settings'): return
            return self.send_json(pharmacy_settings_get())
        if path == '/api/backup':
            user = self.require_user()
            if not user: return
            if user.get('role') != 'admin': return self.send_json({'error':'Admin access required'}, 403)
            os.makedirs(os.path.join(ROOT, 'backups'), exist_ok=True)
            backup_name = 'clinic_backup_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '.db'
            backup_path = os.path.join(ROOT, 'backups', backup_name)
            shutil.copy2(DB_PATH, backup_path)
            audit(user, 'BACKUP', 'database', backup_name)
            return self.send_json({'ok': True, 'file': 'backups/' + backup_name})
        if path == '/api/audit_logs':
            user = self.require_user()
            if not user: return
            if user.get('role') != 'admin': return self.send_json({'error':'Admin access required'}, 403)
            return self.send_json(rows('SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 300'))
        if path == '/api/reports':
            user = self.require_user()
            if not user or not self.require_permission(user, 'GET', 'reports'): return
            return self.send_json(reports(parse_qs(parsed.query)))
        if path.startswith('/api/'):
            user = self.require_user()
            if not user: return
            parts = path.strip('/').split('/'); table = parts[1] if len(parts)>1 else ''
            if table in TABLES:
                if not self.require_permission(user, 'GET', table): return
                if len(parts)==2: return self.send_json(list_table(table))
                if len(parts)==3:
                    item = one(f'SELECT * FROM {table} WHERE id=?', (parts[2],)); return self.send_json(item or {'error':'Not found'}, 200 if item else 404)
            return self.send_json({'error':'Unknown endpoint'},404)
        if path == '/': path = '/index.html'
        fp = os.path.normpath(os.path.join(ROOT,path.lstrip('/')))
        if not fp.startswith(ROOT) or not os.path.exists(fp) or os.path.isdir(fp): return self.send_json({'error':'Not found'},404)
        data = open(fp,'rb').read(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(fp)[0] or 'application/octet-stream'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/login':
            data = self.read_json(); username = (data.get('username') or '').strip().lower(); password = data.get('password') or ''
            con = connect(); row = con.execute("SELECT * FROM users WHERE lower(username)=? AND status='Active'", (username,)).fetchone()
            if not row or not verify_password(password, row['password_hash']):
                con.close(); return self.send_json({'error':'Invalid username or password'}, 401)
            token = secrets.token_urlsafe(32); expires = (datetime.datetime.now()+datetime.timedelta(hours=8)).isoformat(timespec='seconds')
            con.execute('INSERT INTO sessions VALUES (?,?,?,?)', (token, row['id'], now(), expires)); con.commit(); con.close()
            user = public_user(row); audit(user, 'LOGIN', 'session')
            return self.send_login_json({'ok': True, 'user': user}, token=token)
        if path in ('/api/users','/api/user_roles'):
            user = self.require_user()
            if not user: return
            if user.get('role') != 'admin': return self.send_json({'error':'Admin access required'}, 403)
            try:
                out = create_user(self.read_json())
                audit(user, 'CREATE', 'users', out.get('id',''))
                return self.send_json(out, 201)
            except sqlite3.IntegrityError as e:
                return self.send_json({'error':'Username already exists'}, 400)
            except ValueError as e:
                return self.send_json({'error':str(e)}, 400)
        if path == '/api/pharmacy_settings':
            user = self.require_user()
            if not user or not self.require_permission(user, 'POST', 'pharmacy_settings'): return
            out = pharmacy_settings_save(self.read_json()); audit(user,'UPDATE','pharmacy_settings','phset_1')
            return self.send_json(out)
        parts = path.strip('/').split('/')
        if len(parts)!=2 or parts[0]!='api' or parts[1] not in TABLES: return self.send_json({'error':'Unknown endpoint'},404)
        user = self.require_user()
        if not user: return
        table = parts[1]
        if not self.require_permission(user, 'POST', table): return
        meta = TABLES[table]; data = make_defaults(table, self.read_json()); item_id = new_id(meta['prefix'])
        fields = ['id'] + meta['fields'] + ['created_at']; vals = [item_id] + [data.get(f,0 if f in NUM_FIELDS else '') for f in meta['fields']] + [now()]
        con = connect()
        try:
            con.execute(f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(['?']*len(fields))})", vals); con.commit()
        except sqlite3.IntegrityError as e:
            con.close(); return self.send_json({'error':str(e)},400)
        if table == 'opd_bills' and 'updated_at' in table_cols(con, table):
            con.execute('UPDATE opd_bills SET updated_at=? WHERE id=?', (now(), item_id)); con.commit()
        con.close(); audit(user, 'CREATE', table, item_id)
        created = {'id':item_id, **{f:v for f,v in zip(fields[1:],vals[1:])}}
        if table == 'pharmacy_stock_inwards': apply_stock_inward(item_id, created)
        if table == 'pharmacy_invoices': deduct_invoice_stock(item_id, created)
        return self.send_json(created,201)
    def do_PUT(self):
        parts = urlparse(self.path).path.strip('/').split('/')
        if len(parts)==3 and parts[0]=='api' and parts[1] in ('users','user_roles'):
            user = self.require_user()
            if not user: return
            if user.get('role') != 'admin': return self.send_json({'error':'Admin access required'}, 403)
            try:
                out = update_user(parts[2], self.read_json())
                audit(user, 'UPDATE', 'users', parts[2])
                return self.send_json(out)
            except ValueError as e:
                return self.send_json({'error':str(e)}, 400)
        if len(parts)==4 and parts[0]=='api' and parts[1] in ('users','user_roles') and parts[3]=='reset_password':
            user = self.require_user()
            if not user: return
            if user.get('role') != 'admin': return self.send_json({'error':'Admin access required'}, 403)
            try:
                out = reset_user_password(parts[2], self.read_json().get('password',''))
                audit(user, 'RESET_PASSWORD', 'users', parts[2])
                return self.send_json(out)
            except ValueError as e:
                return self.send_json({'error':str(e)}, 400)
        if len(parts)==4 and parts[0]=='api' and parts[1]=='pharmacy_returns' and parts[3]=='mark_paid':
            user = self.require_user()
            if not user or not self.require_permission(user, 'PUT', 'pharmacy_returns'): return
            return self.send_json(restore_return_stock(parts[2], user))
        if len(parts)!=3 or parts[0]!='api' or parts[1] not in TABLES: return self.send_json({'error':'Unknown endpoint'},404)
        user = self.require_user()
        if not user: return
        table=parts[1]
        if not self.require_permission(user, 'PUT', table): return
        data=make_defaults(table,self.read_json()); fields=[f for f in TABLES[table]['fields'] if f in data]
        vals=[data[f] for f in fields]+[parts[2]]; con=connect(); cur=con.execute(f"UPDATE {table} SET {','.join(f+'=?' for f in fields)} WHERE id=?", vals)
        if 'updated_at' in table_cols(con, table): con.execute(f'UPDATE {table} SET updated_at=? WHERE id=?', (now(), parts[2]))
        con.commit(); con.close(); audit(user, 'UPDATE', table, parts[2])
        if table == 'pharmacy_stock_inwards':
            updated = one('SELECT * FROM pharmacy_stock_inwards WHERE id=?',(parts[2],)); apply_stock_inward(parts[2], updated or data)
        return self.send_json({'updated':cur.rowcount})
    def do_DELETE(self):
        parts = urlparse(self.path).path.strip('/').split('/')
        if len(parts)!=3 or parts[0]!='api' or parts[1] not in TABLES: return self.send_json({'error':'Unknown endpoint'},404)
        user = self.require_user()
        if not user: return
        if user.get('role') != 'admin': return self.send_json({'error':'Only admin can delete records'},403)
        con=connect(); cur=con.execute(f'DELETE FROM {parts[1]} WHERE id=?',(parts[2],)); con.commit(); con.close(); audit(user, 'DELETE', parts[1], parts[2]); return self.send_json({'deleted':cur.rowcount})

if __name__ == '__main__':
    init_db(); port = int(os.environ.get('PORT','8000'))
    print(f'Multi-speciality CMS running at http://localhost:{port}')
    ThreadingHTTPServer(('0.0.0.0',port), Handler).serve_forever()
