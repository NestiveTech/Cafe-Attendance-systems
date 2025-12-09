from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.utils import timezone  # Import timezone
import google_auth_oauthlib.flow
import datetime
from .models import DriveToken, CompanySettings
from .drive_auth import get_gspread_client, init_db, send_gmail_report, REDIRECT_URI, SCOPES
from .utils import render_to_pdf

# --- HELPER: CACHE EMPLOYEES FOR SPEED ---
def get_cached_employees(request, gc):
    """Fetches employees from Session Cache or Drive if expired."""
    # Check if data exists and is less than 5 minutes old
    if 'emp_data' in request.session and 'emp_time' in request.session:
        last_fetch = datetime.datetime.fromtimestamp(request.session['emp_time'])
        if (datetime.datetime.now() - last_fetch).seconds < 300: # 5 mins cache
            return request.session['emp_data']
    
    # If not in cache, fetch from Google
    sh = gc.open("CafeTerrain_DB")
    employees = sh.worksheet("Employees").get_all_records()
    
    # Save to session
    request.session['emp_data'] = employees
    request.session['emp_time'] = datetime.datetime.now().timestamp()
    return employees

# ---------------------------------------------------------
# 1. AUTHENTICATION (Hybrid: Password + Google)
# ---------------------------------------------------------

def login_view(request):
    """Standard Username/Password Login."""
    if request.user.is_authenticated: return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def register(request):
    """Standard Registration."""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            login(request, form.save())
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

def google_login(request):
    """Start Google OAuth Flow."""
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file('credentials.json', SCOPES)
    flow.redirect_uri = REDIRECT_URI
    auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
    request.session['state'] = state
    return redirect(auth_url)

def oauth2callback(request):
    """Handle Google OAuth Return."""
    state = request.session.get('state')
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file('credentials.json', SCOPES, state=state)
    flow.redirect_uri = REDIRECT_URI
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    creds = flow.credentials
    
    if not request.user.is_authenticated:
        session = flow.authorized_session()
        email = session.get('https://www.googleapis.com/userinfo/v2/me').json().get('email')
        user, _ = User.objects.get_or_create(username=email, defaults={'email': email})
        login(request, user)
    else:
        user = request.user

    DriveToken.objects.update_or_create(user=user, defaults={'token': creds.to_json()})
    init_db(user)
    messages.success(request, "Google Services Connected!")
    return redirect('dashboard')


# ---------------------------------------------------------
# 2. MAIN APPLICATION LOGIC
# ---------------------------------------------------------

@login_required
def dashboard(request):
    gc = get_gspread_client(request.user)
    
    settings_obj, _ = CompanySettings.objects.get_or_create(user=request.user)
    if request.method == "POST" and 'update_threshold' in request.POST:
        try:
            h, m = map(int, request.POST.get('late_time').split(':'))
            settings_obj.late_threshold = datetime.time(h, m)
            settings_obj.save()
            messages.success(request, "Global Late Threshold Updated!")
        except: messages.error(request, "Invalid Time")
        return redirect('dashboard')

    if not gc: return render(request, 'attendance/dashboard.html', {'connected': False})

    try:
        # Optimization: Use Cached Employees
        employees = get_cached_employees(request, gc)
        
        # We still need to fetch Attendance live for accuracy
        sh = gc.open("CafeTerrain_DB")
        attendance = sh.worksheet("Attendance").get_all_records()
        
        # Fix: Use Timezone Aware Date
        today = timezone.localtime().date().isoformat()
        today_recs = [r for r in attendance if r['Date'] == today]
        
        present = len(set(r['Emp_ID'] for r in today_recs))
        half_days = len([r for r in today_recs if r.get('Status') == 'Half Day'])
        
        context = {
            'connected': True, 
            'total_emp': len(employees), 
            'present': present, 
            'absent': len(employees) - present,
            'half_days': half_days,
            'current_threshold': settings_obj.late_threshold.strftime('%H:%M')
        }
        return render(request, 'attendance/dashboard.html', context)
    except Exception as e:
        return render(request, 'attendance/dashboard.html', {'connected': False, 'error': str(e)})

@login_required
def employees_list(request):
    gc = get_gspread_client(request.user)
    if not gc: return redirect('dashboard')
    
    # Optimization: Use Cached Employees for GET request
    if request.method == "GET":
        return render(request, 'attendance/employees.html', {'employees': get_cached_employees(request, gc)})

    # For POST (Adding), we must open the sheet to write
    ws = gc.open("CafeTerrain_DB").worksheet("Employees")
    
    if request.method == "POST":
        emp_id = request.POST.get('emp_id')
        name = request.POST.get('name')
        role = request.POST.get('role')
        joined = request.POST.get('joined_date')
        threshold = request.POST.get('threshold_time')
        
        existing = [str(r['ID']) for r in ws.get_all_records()]
        if emp_id in existing:
            messages.error(request, f"ID {emp_id} already exists.")
        else:
            ws.append_row([emp_id, name, role, joined, threshold])
            messages.success(request, f"Added {name} (Late after {threshold})")
            # Clear cache so new employee shows up
            if 'emp_data' in request.session: del request.session['emp_data']
            
        return redirect('employees')

@login_required
def mark_attendance(request):
    gc = get_gspread_client(request.user)
    if not gc: return redirect('dashboard')
    
    # Optimization: Use Cached Employees
    employees = get_cached_employees(request, gc)
    
    sh = gc.open("CafeTerrain_DB")
    ws_att = sh.worksheet("Attendance")
    
    # Fix: Use Timezone Aware Date
    today_str = timezone.localtime().date().isoformat()
    
    # Only fetch today's records (Manual filter still needed unless using advanced API)
    all_recs = ws_att.get_all_records()
    today_records = [r for r in all_recs if r['Date'] == today_str]
    
    status_map = {str(r['Emp_ID']): r for r in today_records}

    for emp in employees:
        e_id = str(emp['ID'])
        if e_id in status_map:
            record = status_map[e_id]
            if record.get('Out_Time'):
                emp['status'] = 'COMPLETED'
            else:
                emp['status'] = 'CHECKED_IN'
        else:
            emp['status'] = 'NONE'

    if request.method == "POST":
        emp_id = request.POST.get('emp_id')
        action = request.POST.get('action')
        
        # Fix: Use Timezone Aware Time
        now = timezone.localtime()
        date_str, time_str = now.date().isoformat(), now.strftime('%H:%M')
        
        emp_data = next((e for e in employees if str(e['ID']) == emp_id), None)
        
        if not emp_data:
            messages.error(request, "Employee not found.")
            return redirect('mark_attendance')
        
        name = emp_data['Name']
        
        if action == "IN":
            existing_record = any(str(r['Emp_ID']) == str(emp_id) for r in today_records)
            
            if existing_record:
                messages.warning(request, f"⚠️ Attendance already exists for {name} today.")
            else:
                t_str = emp_data.get('Late_Threshold', '10:00')
                try:
                    th_hour, th_min = map(int, t_str.split(':'))
                    cutoff = now.replace(hour=th_hour, minute=th_min, second=0)
                except:
                    cutoff = now.replace(hour=10, minute=0, second=0)

                if now > cutoff:
                    status = "Half Day"
                    messages.warning(request, f"Checked IN: {name} (Late after {t_str} - Marked Half Day)")
                else:
                    status = "Present"
                    messages.success(request, f"Checked IN: {name} (On Time)")
                
                ws_att.append_row([emp_id, name, date_str, time_str, "", status])
                
        elif action == "OUT":
            found_open_record = False
            for i, r in enumerate(all_recs):
                # Only check matches for today with no Out Time
                if str(r['Emp_ID']) == str(emp_id) and r['Date'] == date_str and r['Out_Time'] == "":
                    ws_att.update_cell(i + 2, 5, time_str) 
                    messages.success(request, f"Checked OUT: {name}")
                    found_open_record = True
                    break
            
            if not found_open_record:
                messages.error(request, f"Cannot Check OUT. {name} has not checked IN or already done.")

        return redirect('mark_attendance')
        
    return render(request, 'attendance/mark_attendance.html', {'employees': employees})


# ---------------------------------------------------------
# 3. PDF REPORTING
# ---------------------------------------------------------

@login_required
def trigger_daily_report(request):
    gc = get_gspread_client(request.user)
    if not gc: return redirect('dashboard')
    
    ws_att = gc.open("CafeTerrain_DB").worksheet("Attendance")
    # Fix: Timezone Aware Date
    today = timezone.localtime().date().isoformat()
    recs = [r for r in ws_att.get_all_records() if r['Date'] == today]
    
    context = {
        'title': f"Daily Attendance Report",
        'date': today,
        'records': recs,
        'total_present': len(set(r['Emp_ID'] for r in recs))
    }
    
    pdf_file = render_to_pdf('attendance/report_pdf.html', context)
    
    if pdf_file:
        target = request.user.email
        body = f"Attached is the Daily Attendance Report for {today}."
        if send_gmail_report(request.user, target, f"Daily Report {today}", body, f"Daily_{today}.pdf", pdf_file):
            messages.success(request, f"PDF Report sent to {target}")
        else:
            messages.error(request, "Failed to send email. Check API permissions.")
    else:
        messages.error(request, "Error generating PDF.")
        
    return redirect('dashboard')

@login_required
def trigger_monthly_report(request):
    gc = get_gspread_client(request.user)
    if not gc: return redirect('dashboard')
    
    ws_att = gc.open("CafeTerrain_DB").worksheet("Attendance")
    # Fix: Timezone Aware Date
    month_str = timezone.localtime().date().strftime('%Y-%m')
    recs = [r for r in ws_att.get_all_records() if r['Date'].startswith(month_str)]
    
    context = {
        'title': f"Monthly Summary Report",
        'date': timezone.localtime().strftime('%B %Y'),
        'records': recs,
        'total_present': len(set(r['Emp_ID'] for r in recs)),
        'total_shifts': len(recs)
    }
    
    pdf_file = render_to_pdf('attendance/report_pdf.html', context)
    
    if pdf_file:
        target = request.user.email
        body = f"Attached is the Monthly Summary for {month_str}."
        if send_gmail_report(request.user, target, f"Monthly Report {month_str}", body, f"Monthly_{month_str}.pdf", pdf_file):
            messages.success(request, f"PDF Report sent to {target}")
        else:
            messages.error(request, "Failed to send email.")
            
    return redirect('dashboard')