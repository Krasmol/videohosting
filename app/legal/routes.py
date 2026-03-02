from flask import render_template
from app.legal import legal_bp

@legal_bp.route('/faq')
def faq():
    return render_template('legal/faq.html')

@legal_bp.route('/privacy')
def privacy():
    return render_template('legal/privacy.html')

@legal_bp.route('/terms')
def terms():
    return render_template('legal/terms.html')

@legal_bp.route('/community-guidelines')
def community_guidelines():
    return render_template('legal/community_guidelines.html')

@legal_bp.route('/about')
def about():
    return render_template('legal/about.html')
