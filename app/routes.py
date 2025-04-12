from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from app.services.firecrawl_service import search_website, get_best_results

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', title='The ONE - Find the Best of Everything')

@main_bp.route('/search', methods=['POST'])
def search():
    # This will be implemented in a later step
    pass

@main_bp.route('/results/<search_id>')
def results(search_id):
    # This will be implemented in a later step
    pass