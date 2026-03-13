# -*- coding: utf-8 -*-
"""
Dermo-CRM - Application Factory
"""
import os
from flask import Flask, current_app
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
    
    # CRUCIAL : Créer les tables au premier démarrage
    with app.app_context():
        _init_database()
    
    return app


def _init_database():
    """
    Initialise la base de données avec gestion des erreurs
    """
    try:
        # Teste si les tables existent
        from app.models import User
        db.session.execute(db.select(User).limit(1))
        current_app.logger.info("✅ Base de données déjà initialisée")
        return
        
    except Exception as e:
        current_app.logger.warning(f"🔧 Initialisation nécessaire: {e}")
        
        try:
            # Ferme la session proprement
            db.session.remove()
            
            # Crée les tables
            current_app.logger.info("🔧 Création des tables...")
            db.create_all()
            current_app.logger.info("✅ Tables créées")
            
            # Crée les données
            _create_initial_data()
            current_app.logger.info("✅ Données créées")
            
        except Exception as create_error:
            current_app.logger.error(f"❌ Erreur: {create_error}")
            db.session.rollback()


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


def _create_initial_data():
    """Créer les données initiales"""
    from app.models import User, Referent, Product, Campaign
    from werkzeug.security import generate_password_hash
    from datetime import date
    
    try:
        # Créer l'admin
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
        current_app.logger.info("✅ Admin créé")
        
        # Créer référents
        referents = [
            Referent(name='Marie Dupont', email='marie@email.com', 
                    phone='0612345678', zone='Nord', color='#e74c3c'),
            Referent(name='Jean Martin', email='jean@email.com', 
                    phone='0623456789', zone='Sud', color='#3498db'),
        ]
        db.session.add_all(referents)
        db.session.commit()
        current_app.logger.info("✅ Référents créés")
        
        # Créer produits
        products = [
            Product(name='Crème Hydratante', brand='Dermophil', 
                   category='Hydratation', description='Peaux sensibles'),
            Product(name='Sérum Anti-Âge', brand='SkinScience', 
                   category='Anti-Âge', description='Au rétinol'),
        ]
        db.session.add_all(products)
        db.session.commit()
        current_app.logger.info("✅ Produits créés")
        
        # Créer campagne
        campaign = Campaign(
            name='Campagne 2024',
            description='Promotion',
            start_date=date(2024, 6, 1),
            end_date=date(2024, 8, 31),
            objectives='Former 100 pharmacies',
            status='active'
        )
        db.session.add(campaign)
        db.session.commit()
        current_app.logger.info("✅ Campagne créée")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Erreur création données: {e}")


# Route temporaire pour forcer la création des données
def add_reset_route(app):
    @app.route('/reset-db')
    def reset_db():
        """Force la réinitialisation de la base"""
        try:
            db.drop_all()
            db.create_all()
            _create_initial_data()
            return "✅ Base réinitialisée avec succès!"
        except Exception as e:
            return f"❌ Erreur: {str(e)}"

# Appeler après create_app
# add_reset_route(app)  # Décommente si besoin
