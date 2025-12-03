"""
Utility functions for demo account management.
"""
import uuid
import secrets
from django.contrib.auth import get_user_model, authenticate, login
from django.utils.translation import gettext_lazy as _

User = get_user_model()


def generate_visitor_id():
    """Generate a unique visitor ID."""
    return str(uuid.uuid4())


def generate_demo_password():
    """Generate a secure random password for demo accounts."""
    return secrets.token_urlsafe(32)


def get_visitor_id_from_request(request):
    """Get or create visitor ID from session."""
    visitor_id = request.session.get('demo_visitor_id')
    if not visitor_id:
        visitor_id = generate_visitor_id()
        request.session['demo_visitor_id'] = visitor_id
        request.session.set_expiry(60 * 60 * 24 * 365)  # 1 year
    return visitor_id


def get_or_create_demo_accounts(visitor_id, request=None):
    """
    Get or create demo accounts for a visitor.
    Stores passwords in session for later authentication.
    Returns tuple: (citizen_account, official_account, passwords_dict)
    where passwords_dict = {'citizen': password, 'official': password}
    """
    # Email pattern for demo accounts
    citizen_email = f'demo_citizen_{visitor_id}@demo.local'
    official_email = f'demo_official_{visitor_id}@demo.local'
    
    passwords = {}
    
    # Try to get existing accounts
    citizen = User.objects.filter(email=citizen_email, is_demo_account=True).first()
    official = User.objects.filter(email=official_email, is_demo_account=True).first()
    
    # Get passwords from session if accounts exist
    if request:
        session_passwords = request.session.get('demo_account_passwords', {})
        passwords = session_passwords.get(visitor_id, {})
    
    # Create citizen account if it doesn't exist
    if not citizen:
        password = generate_demo_password()
        passwords['citizen'] = password
        citizen = User.objects.create_user(
            email=citizen_email,
            password=password,
            role='citizen',
            first_name=_('Демо'),
            last_name=_('Горожанин'),
            email_verified=True,
            is_active=True,
            is_demo_account=True,
        )
        if request:
            if 'demo_account_passwords' not in request.session:
                request.session['demo_account_passwords'] = {}
            if visitor_id not in request.session['demo_account_passwords']:
                request.session['demo_account_passwords'][visitor_id] = {}
            request.session['demo_account_passwords'][visitor_id]['citizen'] = password
    else:
        # Account exists, get password from session or generate new one
        if 'citizen' not in passwords:
            password = generate_demo_password()
            citizen.set_password(password)
            citizen.save()
            passwords['citizen'] = password
            if request:
                if 'demo_account_passwords' not in request.session:
                    request.session['demo_account_passwords'] = {}
                if visitor_id not in request.session['demo_account_passwords']:
                    request.session['demo_account_passwords'][visitor_id] = {}
                request.session['demo_account_passwords'][visitor_id]['citizen'] = password
    
    # Create official account if it doesn't exist
    if not official:
        password = generate_demo_password()
        passwords['official'] = password
        official = User.objects.create_user(
            email=official_email,
            password=password,
            role='official',
            first_name=_('Демо'),
            last_name=_('Должностное лицо'),
            email_verified=True,
            is_active=True,
            is_demo_account=True,
            department=_('Демонстрационный департамент'),
        )
        if request:
            if 'demo_account_passwords' not in request.session:
                request.session['demo_account_passwords'] = {}
            if visitor_id not in request.session['demo_account_passwords']:
                request.session['demo_account_passwords'][visitor_id] = {}
            request.session['demo_account_passwords'][visitor_id]['official'] = password
    else:
        # Account exists, get password from session or generate new one
        if 'official' not in passwords:
            password = generate_demo_password()
            official.set_password(password)
            official.save()
            passwords['official'] = password
            if request:
                if 'demo_account_passwords' not in request.session:
                    request.session['demo_account_passwords'] = {}
                if visitor_id not in request.session['demo_account_passwords']:
                    request.session['demo_account_passwords'][visitor_id] = {}
                request.session['demo_account_passwords'][visitor_id]['official'] = password
    
    return citizen, official, passwords


def login_demo_account(request, user, password):
    """Login a demo user account."""
    authenticated_user = authenticate(request, username=user.email, password=password)
    if authenticated_user:
        login(request, authenticated_user)
        request.session['demo_mode'] = True
        return True
    return False


def get_demo_account_password(request, visitor_id, role):
    """Get the password for a demo account from session."""
    passwords = request.session.get('demo_account_passwords', {})
    visitor_passwords = passwords.get(visitor_id, {})
    return visitor_passwords.get(role)

