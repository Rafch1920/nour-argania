# -*- coding: utf-8 -*-
"""
Dermo-CRM - Application Factory
"""
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

# Extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
mail = Mail()


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))


def create_app(config_name=None):
    """
    Factory pattern pour créer l'application Flask
    """
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Déterminer la config
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'production')
    
    # Import ici pour éviter le conflit circulaire
    from config import config_dict
    app.config.from_object(config_dict[config_name])
    
    # Initialiser les extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Configuration LoginManager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'
    
    # Enregistrer les blueprints
    _register_blueprints(app)
    
    # CRUCIAL : Créer les tables au premier démarrage (avec gestion d'erreur PostgreSQL)
    with app.app_context():
        _init_database(app)
    
    return app


def _init_database(app):
    """
    Initialise la base de données avec gestion des erreurs PostgreSQL
    """
    try:
        # Teste si la connexion fonctionne et si les tables existent
        from app.models import User
        db.session.execute(db.select(User).limit(1))
        app.logger.info("✅ Base de données déjà initialisée")
        return
        
    except Exception as e:
        # Tables n'existent pas ou erreur de connexion
        app.logger.warning(f"🔧 Base de données non initialisée: {e}")
        
        try:
            # Ferme la session proprement pour éviter les transactions bloquées
            db.session.remove()
            
            # Crée toutes les tables
            app.logger.info("🔧 Création des tables...")
            db.create_all()
            app.logger.info("✅ Tables créées avec succès")
            
            # Crée les données initiales
            _create_initial_data(app)
            app.logger.info("✅ Données initiales créées avec succès")
            
        except Exception as create_error:
            # En cas d'erreur, rollback et log
            app.logger.error(f"❌ Erreur création base de données: {create_error}")
            db.session.rollback()
            # Ne bloque pas le démarrage de l'app


def _register_blueprints(app):
    """Enregistrer tous les blueprints"""
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.routes.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)
    
    from app.routes.pharmacies import bp as pharmacies_bp
    app.register_blueprint(pharmacies_bp, url_prefix='/pharmacies')
    
    from app.routes.visits import bp as visits_bp
    app.register_blueprint(visits_bp, url_prefix='/visits')
    
    from app.routes.products import bp as products_bp
    app.register_blueprint(products_bp, url_prefix='/products')
    
    from app.routes.campaigns import bp as campaigns_bp
    app.register_blueprint(campaigns_bp, url_prefix='/campaigns')
    
    from app.routes.referents import bp as referents_bp
    app.register_blueprint(referents_bp, url_prefix='/referents')
    
    from app.routes.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')


def _create_initial_data(app):
    """Créer les données initiales si elles n'existent pas"""
    from app.models import User, Referent, Product, Campaign
    from werkzeug.security import generate_password_hash
    from datetime import date
    
    try:
        # Créer l'admin s'il n'existe pas
        admin_exists = db.session.execute(
            db.select(User).filter_by(username='admin')
        ).scalar_one_or_none()
        
        if not admin_exists:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                email='admin@dermo-crm.local',
                full_name='Administrateur',
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            app.logger.info("✅ Utilisateur admin créé (admin / admin123)")
        
        # Créer des référents exemples
        referent_exists = db.session.execute(db.select(Referent).limit(1)).scalar_one_or_none()
        if not referent_exists:
            referents = [
                Referent(name='Marie Dupont', email='marie.dupont@email.com', 
                        phone='06 12 34 56 78', zone='Nord', color='#e74c3c'),
                Referent(name='Jean Martin', email='jean.martin@email.com', 
                        phone='06 23 45 67 89', zone='Sud', color='#3498db'),
                Referent(name='Sophie Bernard', email='sophie.bernard@email.com', 
                        phone='06 34 56 78 90', zone='Est', color='#2ecc71')
            ]
            db.session.add_all(referents)
            db.session.commit()
            app.logger.info("✅ Référents exemples créés")
        
        # Créer des produits exemples
        product_exists = db.session.execute(db.select(Product).limit(1)).scalar_one_or_none()
        if not product_exists:
            products = [
                Product(name='Crème Hydratante Ultra', brand='Dermophil', 
                       category='Hydratation', 
                       description='Crème hydratante pour peaux sensibles'),
                Product(name='Sérum Anti-Âge', brand='SkinScience', 
                       category='Anti-Âge', 
                       description='Sérum concentré au rétinol'),
                Product(name='Protection Solaire SPF50', brand='SunCare', 
                       category='Protection', 
                       description='Écran solaire haute protection')
            ]
            db.session.add_all(products)
            db.session.commit()
            app.logger.info("✅ Produits exemples créés")
        
        # Créer une campagne exemple
        campaign_exists = db.session.execute(db.select(Campaign).limit(1)).scalar_one_or_none()
        if not campaign_exists:
            campaign = Campaign(
                name='Campagne Été 2026',
                description='Promotion des produits solaires',
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 15),
                objectives='Former 100 pharmacies sur la gamme solaire',
                status='active'
            )
            db.session.add(campaign)
            db.session.commit()
            app.logger.info("✅ Campagne exemple créée")
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"❌ Erreur création données initiales: {e}")
        raise
