"""
Dermo-CRM - Routes d'authentification
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from app import db
from app.models import User, ActivityLog

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        # Validation
        if not username or not password:
            flash('Veuillez remplir tous les champs.', 'danger')
            return render_template('auth/login.html')
        
        # Recherche utilisateur
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Ce compte est désactivé.', 'danger')
                return render_template('auth/login.html')
            
            # Connexion réussie
            login_user(user, remember=remember)
            user.last_login = db.func.now()
            db.session.commit()
            
            # Log
            _log_activity('login', None, None, {'ip': request.remote_addr})
            
            flash(f'Bienvenue, {user.full_name or user.username} !', 'success')
            
            # Redirection
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Identifiants incorrects.', 'danger')
            _log_activity('login_failed', None, None, {'username': username, 'ip': request.remote_addr})
    
    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    _log_activity('logout', None, None, {})
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Profil utilisateur"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_info':
            # Mise à jour infos
            current_user.full_name = request.form.get('full_name', '').strip()
            current_user.email = request.form.get('email', '').strip()
            current_user.phone = request.form.get('phone', '').strip()
            db.session.commit()
            flash('Profil mis à jour.', 'success')
            _log_activity('update_profile', 'user', current_user.id)
            
        elif action == 'change_password':
            # Changement mot de passe
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not current_user.check_password(current_password):
                flash('Mot de passe actuel incorrect.', 'danger')
            elif new_password != confirm_password:
                flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
            elif len(new_password) < 6:
                flash('Le nouveau mot de passe doit faire au moins 6 caractères.', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Mot de passe modifié.', 'success')
                _log_activity('change_password', 'user', current_user.id)
    
    return render_template('auth/profile.html')


def _log_activity(action, entity_type=None, entity_id=None, details=None):
    """Helper pour logger une activité"""
    import json
    log = ActivityLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details) if details else None,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
