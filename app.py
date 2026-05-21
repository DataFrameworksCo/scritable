import os
from flask import Flask, render_template, request, jsonify

from checkers.parser import parse_file
from checkers.spellcheck import check_spelling, check_repeated_words
from checkers.characters import analyze_characters

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

ALLOWED = {'txt', 'docx', 'pdf'}


def _allowed(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded.'}), 400

    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'No file selected.'}), 400
    if not _allowed(f.filename):
        return jsonify({'error': 'Unsupported format. Please upload .txt, .docx, or .pdf.'}), 400

    try:
        paragraphs = parse_file(f, f.filename)
    except Exception as e:
        return jsonify({'error': f'Could not read file: {e}'}), 400

    if not paragraphs:
        return jsonify({'error': 'No text could be extracted from the file.'}), 400

    word_count = sum(len(p.split()) for p in paragraphs)

    # Run all three checks
    char_results = analyze_characters(paragraphs)
    known_names = set(char_results.get('character_names', []))

    spell_results = check_spelling(paragraphs, known_names)
    repeat_results = check_repeated_words(paragraphs)

    return jsonify({
        'success': True,
        'word_count': word_count,
        'paragraph_count': len(paragraphs),
        'spelling': spell_results,
        'repeated_words': repeat_results,
        'characters': {
            'profiles': char_results['profiles'],
            'inconsistency_count': char_results['inconsistency_count'],
            'spacy_available': char_results['spacy_available'],
        },
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Manuscript Checker running at http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
