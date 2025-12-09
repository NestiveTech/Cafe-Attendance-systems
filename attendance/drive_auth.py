import json
import base64
import gspread
import google.oauth2.credentials
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from .models import DriveToken
import os # <--- NEW IMPORT

# Load REDIRECT_URI from environment variable, falling back to localhost for dev
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://127.0.0.1:8000/oauth2callback/')

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/gmail.send',
    'openid'
]
DB_FILENAME = "CafeTerrain_DB"

def get_credentials(user):
    try:
        db_token = DriveToken.objects.get(user=user)
        creds_data = json.loads(db_token.token)
        creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
            creds_data, SCOPES)
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            db_token.token = creds.to_json()
            db_token.save()
        return creds
    except DriveToken.DoesNotExist:
        return None

def get_gspread_client(user):
    creds = get_credentials(user)
    return gspread.authorize(creds) if creds else None

def init_db(user):
    gc = get_gspread_client(user)
    if not gc: return None
    try:
        sh = gc.open(DB_FILENAME)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(DB_FILENAME)
        sh.add_worksheet(title="Employees", rows=100, cols=5)
        sh.add_worksheet(title="Attendance", rows=1000, cols=6)
        sh.worksheet("Employees").append_row(["ID", "Name", "Role", "Joined_Date", "Late_Threshold"])
        sh.worksheet("Attendance").append_row(["Emp_ID", "Name", "Date", "In_Time", "Out_Time", "Status"])
        try: sh.del_worksheet(sh.worksheet("Sheet1"))
        except: pass
    return sh

# --- UPDATED EMAIL FUNCTION ---
def send_gmail_report(user, to_email, subject, body_html, attachment_name=None, attachment_data=None):
    """Sends email with optional PDF attachment."""
    creds = get_credentials(user)
    if not creds: return False

    try:
        service = build('gmail', 'v1', credentials=creds)
        msg = MIMEMultipart()
        msg['to'] = to_email
        msg['subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))
        
        # Attach PDF if provided
        if attachment_name and attachment_data:
            part = MIMEApplication(attachment_data, Name=attachment_name)
            part['Content-Disposition'] = f'attachment; filename="{attachment_name}"'
            msg.attach(part)
        
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return True
    except Exception as e:
        print(f"Gmail Error: {e}")
        return False